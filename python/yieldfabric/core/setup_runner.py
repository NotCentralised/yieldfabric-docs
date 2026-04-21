"""
Setup runner — system bootstrap from a setup.yaml.

Ports `yieldfabric-docs/scripts/setup_system.sh` to Python: creates
users, groups, tokens, and assets (and optionally fiat accounts) in the
order the shell expects. Every operation is idempotent — 409 Conflict
or "already exists" error messages are treated as success, so this can
be re-run against a partially-seeded environment without damage.

Usage (programmatic):

    config = YieldFabricConfig.from_env()
    with YieldFabricSetupRunner(config) as runner:
        ok = runner.run("../scripts/setup.yaml")

Usage (CLI, once wired):

    python -m yieldfabric.cli setup ../scripts/setup.yaml
"""

import time
from typing import Any, Dict, List, Optional

from ..config import YieldFabricConfig
from ..services import AuthService, PaymentsService
from ..validation import ServiceValidator
from ..utils.jwt import get_sub
from ..utils.logger import get_logger

try:
    import yaml  # type: ignore
except ImportError as _e:  # pragma: no cover — PyYAML is in requirements.txt
    yaml = None  # type: ignore


class YieldFabricSetupRunner:
    """Orchestrator for the system-bootstrap phase.

    The shell performs these steps in order and we mirror them exactly.
    Steps are idempotent: re-running against a seeded env will skip
    items that already exist and only create what's missing.

    1. Validate services (auth + payments reachable).
    2. Parse setup.yaml.
    3. Create users (in order they appear).
    4. For each group:
         a. Login as the group's `user` (creator).
         b. Create the group (409 = exists, skip).
         c. Deploy on-chain group account if status is not_deployed.
         d. Add any declared members via an admin token.
    5. Create tokens under an admin JWT.
    6. Create assets under an admin JWT.
    7. Create fiat accounts (US/UK/AU) if the section exists.
    """

    def __init__(self, config: Optional[YieldFabricConfig] = None):
        self.config = config or YieldFabricConfig.from_env()
        self.logger = get_logger(debug=self.config.debug)
        self.auth_service = AuthService(self.config)
        self.payments_service = PaymentsService(self.config)
        self.service_validator = ServiceValidator(
            self.auth_service, self.payments_service,
            debug=self.config.debug,
        )

        # user_email → user_id, populated as we create users. Needed for
        # adding members to groups (the auth service requires user IDs,
        # not emails).
        self._user_ids: Dict[str, str] = {}

    # ------------------------------------------------------------------

    def run(self, setup_file: str) -> bool:
        """
        Full setup from `setup_file`. Returns True iff every step
        succeeded (or was idempotently skipped because it already
        existed).
        """
        self.logger.cyan("🚀 Running system setup")
        self.logger.separator()

        if yaml is None:
            self.logger.error("❌ PyYAML is not installed (see requirements.txt)")
            return False

        if not self.service_validator.validate_services():
            return False

        setup = self._parse_setup_file(setup_file)
        if setup is None:
            return False

        all_ok = True

        # 1. Users.
        self.logger.subsection("👥 Users")
        all_ok &= self._setup_users(setup.get("users") or [])

        # Everything else needs an admin token. Use the FIRST user in
        # the YAML (by convention all setup-yaml users are SuperAdmin).
        admin_token = self._acquire_admin_token(setup.get("users") or [])
        if not admin_token:
            self.logger.error("❌ Could not acquire an admin token; aborting")
            return False

        # 2. Groups (with per-creator login, deploy, and members).
        self.logger.subsection("🏢 Groups")
        all_ok &= self._setup_groups(setup.get("groups") or [], admin_token)

        # 3. Tokens.
        self.logger.subsection("🪙 Tokens")
        all_ok &= self._setup_tokens(setup.get("tokens") or [], admin_token)

        # 4. Assets.
        self.logger.subsection("💎 Assets")
        all_ok &= self._setup_assets(setup.get("assets") or [], admin_token)

        # 5. Fiat accounts (optional — section may be commented out).
        fiat_accounts = setup.get("fiat_accounts") or []
        if fiat_accounts:
            self.logger.subsection("🏦 Fiat accounts")
            all_ok &= self._setup_fiat_accounts(fiat_accounts, admin_token)

        self.logger.separator()
        if all_ok:
            self.logger.success("✅ Setup completed")
        else:
            self.logger.warning("⚠️  Setup completed with some failures")
        return all_ok

    # ------------------------------------------------------------------
    # Internals.
    # ------------------------------------------------------------------

    def _parse_setup_file(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r") as fh:
                return yaml.safe_load(fh) or {}
        except FileNotFoundError:
            self.logger.error(f"❌ setup file not found: {path}")
            return None
        except yaml.YAMLError as e:
            self.logger.error(f"❌ YAML parse error: {e}")
            return None

    def _setup_users(self, users: List[Dict[str, Any]]) -> bool:
        if not users:
            self.logger.info("  (no users declared)")
            return True

        ok = True
        for user in users:
            email = user.get("id")
            password = user.get("password")
            role = user.get("role", "Operator")
            if not email or not password:
                self.logger.error(f"  ❌ user entry missing id or password: {user}")
                ok = False
                continue

            result = self.auth_service.create_user(email, password, role)
            status = result.get("status")
            if status == "created":
                user_id = result.get("user_id")
                if user_id:
                    self._user_ids[email] = user_id
                self.logger.success(f"  ✅ {email} ({role}) created")
            elif status == "exists":
                # Already there — log in to learn the user_id so we can
                # still add them to groups downstream.
                self.logger.info(f"  ⚠️  {email} already exists; logging in to recover user_id")
                user_id = self._login_and_extract_user_id(email, password)
                if user_id:
                    self._user_ids[email] = user_id
            else:
                self.logger.error(f"  ❌ {email}: {result.get('message')}")
                ok = False
        return ok

    def _login_and_extract_user_id(self, email: str, password: str) -> Optional[str]:
        """
        When a user already exists we can't re-create them to learn their
        ID. Instead log in and decode the JWT `sub` claim.
        """
        jwt = self.auth_service.login(email, password)
        if not jwt:
            return None
        return get_sub(jwt)

    def _acquire_admin_token(self, users: List[Dict[str, Any]]) -> Optional[str]:
        """
        The first user in setup.yaml is conventionally a SuperAdmin and
        owns enough permissions to create tokens/assets and add group
        members. Log them in as our admin principal for later steps.
        """
        if not users:
            return None
        first = users[0]
        return self.auth_service.login(first.get("id"), first.get("password"))

    def _setup_groups(
        self,
        groups: List[Dict[str, Any]],
        admin_token: str,
    ) -> bool:
        if not groups:
            self.logger.info("  (no groups declared)")
            return True

        ok = True
        for group in groups:
            name = group.get("name")
            description = group.get("description") or ""
            group_type = group.get("group_type", "project")
            creator = group.get("user") or {}
            creator_email = creator.get("id")
            creator_password = creator.get("password")

            if not (name and creator_email and creator_password):
                self.logger.error(f"  ❌ group missing name/user.id/user.password: {group}")
                ok = False
                continue

            creator_token = self.auth_service.login(creator_email, creator_password)
            if not creator_token:
                self.logger.error(f"  ❌ could not log in creator {creator_email} for group {name}")
                ok = False
                continue

            result = self.auth_service.create_group(
                creator_token, name=name, description=description, group_type=group_type
            )
            status = result.get("status")
            group_id = result.get("group_id")

            if status == "created":
                self.logger.success(f"  ✅ group {name} created (id: {group_id[:8] if group_id else 'N/A'}...)")
            elif status == "exists":
                # Recover the group id by listing.
                group_id = self.auth_service.get_group_id_by_name(creator_token, name)
                self.logger.info(f"  ⚠️  group {name} already exists")
            else:
                self.logger.error(f"  ❌ group {name}: {result.get('message')}")
                ok = False
                continue

            if not group_id:
                self.logger.error(f"  ❌ cannot resolve group_id for {name}; skipping deploy/members")
                ok = False
                continue

            # Deploy the group's on-chain account if not already deployed.
            ok &= self._deploy_group_if_needed(admin_token, name, group_id)

            # Add any declared members (optional — commented out in current setup.yaml).
            members = group.get("members") or []
            for m in members:
                m_email = m.get("id")
                m_role = m.get("role", "member")
                if not m_email:
                    continue
                m_user_id = self._user_ids.get(m_email)
                if not m_user_id:
                    # Best-effort login to recover.
                    m_pw = m.get("password")
                    if m_pw:
                        m_user_id = self._login_and_extract_user_id(m_email, m_pw)
                if not m_user_id:
                    self.logger.error(
                        f"  ❌ member {m_email}: unknown user_id (was the user created?)"
                    )
                    ok = False
                    continue
                res = self.auth_service.add_group_member(admin_token, group_id, m_user_id, m_role)
                if res.get("status") in ("added", "exists"):
                    self.logger.success(f"    ✅ member {m_email} ({m_role})")
                else:
                    self.logger.error(f"    ❌ member {m_email}: {res.get('message')}")
                    ok = False
        return ok

    def _deploy_group_if_needed(self, admin_token: str, name: str, group_id: str) -> bool:
        status = self.auth_service.group_account_status(admin_token, group_id)
        if status == "deployed":
            self.logger.info(f"  ℹ️  group {name} account already deployed")
            return True
        if status == "not_deployed":
            res = self.auth_service.deploy_group_account(admin_token, group_id)
            if res.get("status") != "success":
                self.logger.error(
                    f"  ❌ deploy group {name} failed: {res.get('message')}"
                )
                return False
            self.logger.info(f"  🚀 group {name} deploy initiated; polling status")

            # Poll `/auth/groups/{id}/account-status` until status is
            # `deployed` rather than sleeping a fixed 3s. Timeout at 60s
            # — deployment normally completes in a few seconds; anything
            # past a minute is a genuine backend problem.
            from ..utils.polling import poll_until
            try:
                poll_until(
                    lambda: self.auth_service.group_account_status(admin_token, group_id),
                    lambda s: s == "deployed",
                    interval=1.0,
                    timeout=60.0,
                    description=f"group {name} account to be deployed",
                )
            except TimeoutError as e:
                self.logger.error(f"  ❌ deploy group {name}: {e}")
                return False
            self.logger.success(f"  ✅ group {name} account deployed")
            return True
        # Unknown status — log and continue (non-fatal).
        self.logger.warning(f"  ⚠️  group {name} account status: {status!r}")
        return True

    def _setup_tokens(self, tokens: List[Dict[str, Any]], admin_token: str) -> bool:
        ok = True
        for t in tokens:
            token_id = t.get("id")
            name = t.get("name")
            description = t.get("description") or ""
            address = t.get("address")
            chain_id = str(t.get("chain_id") or "")
            if not (token_id and name and address and chain_id):
                self.logger.error(f"  ❌ token entry missing required fields: {t}")
                ok = False
                continue
            res = self.payments_service.create_token(
                admin_token,
                token_id=token_id,
                name=name,
                description=description,
                chain_id=chain_id,
                address=address,
            )
            status = res.get("status")
            if status in ("created", "exists"):
                icon = "✅" if status == "created" else "⚠️ "
                self.logger.success(f"  {icon} token {name} ({token_id}) {status}")
            else:
                self.logger.error(f"  ❌ token {token_id}: {res.get('message')}")
                ok = False
        return ok

    def _setup_assets(self, assets: List[Dict[str, Any]], admin_token: str) -> bool:
        ok = True
        for a in assets:
            name = a.get("name")
            description = a.get("description") or ""
            asset_type = a.get("type") or a.get("asset_type")
            currency = a.get("currency")
            token_id = a.get("token_id")
            if not (name and asset_type and currency and token_id):
                self.logger.error(f"  ❌ asset entry missing required fields: {a}")
                ok = False
                continue
            res = self.payments_service.create_asset(
                admin_token,
                name=name,
                description=description,
                asset_type=asset_type,
                currency=currency,
                token_id=token_id,
            )
            status = res.get("status")
            if status in ("created", "exists"):
                icon = "✅" if status == "created" else "⚠️ "
                self.logger.success(f"  {icon} asset {name} {status}")
            else:
                self.logger.error(f"  ❌ asset {name}: {res.get('message')}")
                ok = False
        return ok

    def _setup_fiat_accounts(
        self,
        accounts: List[Dict[str, Any]],
        admin_token: str,
    ) -> bool:
        """
        Accounts are keyed by currency/country to pick the right mutation:
          currency=USD                       → create_us_bank_account (routing_number + account_number)
          currency=GBP                       → create_uk_bank_account (sort_code + account_number)
          currency=AUD (or country starts AU)→ create_au_bank_account (bsb + account_number)

        This is a minimum-viable port; the shell has more permutations.
        """
        ok = True
        for acct in accounts:
            currency = (acct.get("currency") or "").upper()
            inputs = {
                "account_id": acct.get("id"),
                "asset_id": acct.get("asset"),
                "country": acct.get("country"),
                "currency": currency,
                "account_holder_name": acct.get("holder"),
                "iban": acct.get("iban"),
                "account_number": acct.get("account_number"),
            }
            if currency == "USD":
                inputs["routing_number"] = acct.get("routing_number")
                inputs["country"] = inputs["country"] or "US"
                res = self.payments_service.create_us_bank_account(admin_token, **inputs)
            elif currency == "GBP":
                inputs["sort_code"] = acct.get("sort_code")
                inputs["country"] = inputs["country"] or "GB"
                res = self.payments_service.create_uk_bank_account(admin_token, **inputs)
            elif currency == "AUD":
                inputs["bsb"] = acct.get("bsb")
                inputs["country"] = inputs["country"] or "AU"
                res = self.payments_service.create_au_bank_account(admin_token, **inputs)
            else:
                self.logger.error(f"  ❌ fiat_account currency {currency!r} not supported")
                ok = False
                continue

            status = res.get("status")
            if status in ("created", "exists"):
                icon = "✅" if status == "created" else "⚠️ "
                self.logger.success(f"  {icon} fiat account {inputs['account_id']} {status}")
            else:
                self.logger.error(f"  ❌ fiat account {inputs['account_id']}: {res.get('message')}")
                ok = False
        return ok

    def close(self):
        self.auth_service.close()
        self.payments_service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


