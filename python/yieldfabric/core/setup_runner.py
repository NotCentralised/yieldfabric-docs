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

Usage (CLI):

    python -m yieldfabric.cli setup ../scripts/setup.yaml            # full setup
    python -m yieldfabric.cli setup ../scripts/setup.yaml tokens assets
    python -m yieldfabric.cli setup ../scripts/setup.yaml validate   # offline check

Granular phases mirror `setup_system.sh`'s commands one-for-one
(setup/all, users, groups, owners, tokens, assets, fiat, status,
validate). Multiple phases run in the order given, so `tokens assets`
seeds tokens then assets in a single invocation.
"""

import os
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

    Each step is also runnable on its own via :meth:`run_phases`, which
    is how the CLI exposes `setup_system.sh`'s granular commands.
    """

    # Canonical phase names — one per `setup_system.sh` command.
    ALL_PHASE = "all"
    PHASES = (
        "all", "users", "groups", "owners",
        "tokens", "assets", "fiat", "status", "validate",
    )
    # Accept a few friendly synonyms (CLI ergonomics + bash parity).
    _PHASE_ALIASES = {
        "setup": "all",
        "fiat_accounts": "fiat",
        "relationships": "owners",
        "user": "users",
        "group": "groups",
        "token": "tokens",
        "asset": "assets",
    }

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

        # Lazy, cached prerequisites so running several phases in one
        # invocation (e.g. `tokens assets`) doesn't re-validate services,
        # re-create users, or re-acquire the admin token for each phase.
        self._services_ok: Optional[bool] = None
        self._users_ensured: bool = False
        self._admin_token: Optional[str] = None

    # ------------------------------------------------------------------

    @classmethod
    def normalize_phase(cls, name: str) -> str:
        """Lower-case a phase name and resolve any alias (setup→all, …)."""
        n = (name or "").strip().lower()
        return cls._PHASE_ALIASES.get(n, n)

    @classmethod
    def is_known_phase(cls, name: str) -> bool:
        """True if `name` (after alias resolution) is a runnable phase."""
        return cls.normalize_phase(name) in cls.PHASES

    def run(self, setup_file: str) -> bool:
        """
        Full setup from `setup_file` (the `all` phase). Back-compat thin
        wrapper over :meth:`run_phases`. Returns True iff every step
        succeeded (or was idempotently skipped because it already
        existed).
        """
        return self.run_phases(setup_file, [self.ALL_PHASE])

    def run_phases(self, setup_file: str, phases: List[str]) -> bool:
        """
        Run one or more named phases against `setup_file`, in order.

        `phases` is a list of `setup_system.sh`-equivalent command names
        (see :attr:`PHASES`). An empty list defaults to the full setup.
        Phases share cached prerequisites (service validation, admin
        token, user creation) so `["tokens", "assets"]` validates once
        and reuses the same admin token for both.

        Returns True iff every requested phase succeeded.
        """
        if yaml is None:
            self.logger.error("❌ PyYAML is not installed (see requirements.txt)")
            return False

        # Normalise + validate the requested phases up front so a typo
        # fails fast instead of half-running a multi-phase sequence.
        normalized: List[str] = []
        for raw in (phases or [self.ALL_PHASE]):
            name = self.normalize_phase(raw)
            if name not in self.PHASES:
                self.logger.error(
                    f"❌ unknown phase: {raw!r} "
                    f"(valid: {', '.join(self.PHASES)})"
                )
                return False
            normalized.append(name)
        if not normalized:
            normalized = [self.ALL_PHASE]

        setup = self._parse_setup_file(setup_file)
        if setup is None:
            return False

        self.logger.cyan(f"📄 Config file: {setup_file}")
        self.logger.cyan(f"▶  Phases: {', '.join(normalized)}")
        self.logger.separator()

        all_ok = True
        for phase in normalized:
            all_ok &= self._run_one_phase(phase, setup, setup_file)
        return all_ok

    def _run_one_phase(self, phase: str, setup: Dict[str, Any], setup_file: str) -> bool:
        """Dispatch a single normalized phase. Acquires only the
        prerequisites that phase needs (validate/status/owners differ)."""
        # Offline / read-only phases — no services or admin token needed.
        if phase == "validate":
            return self._validate(setup, setup_file)
        if phase == "status":
            return self._status(setup, setup_file)
        if phase == self.ALL_PHASE:
            return self._run_full(setup)

        # Every mutating phase needs the services up.
        if not self._ensure_services():
            return False

        if phase == "users":
            ok = self._setup_users(setup.get("users") or [])
            self._users_ensured = True
            return ok

        # groups/owners need user_ids to resolve members; tokens/assets/fiat
        # only need users when there's no API key (so first-user admin login
        # works). This mirrors `setup_system.sh` calling create_initial_users
        # before each of those commands.
        needs_user_ids = phase in ("groups", "owners")
        if needs_user_ids or not self.config.api_key:
            self._ensure_users(setup)

        admin_token = self._ensure_admin(setup)
        if not admin_token:
            self.logger.error("❌ Could not acquire an admin token; aborting phase")
            return False

        if phase == "groups":
            return self._setup_groups(setup.get("groups") or [], admin_token)
        if phase == "owners":
            return self._setup_owners(setup.get("groups") or [], admin_token)
        if phase == "tokens":
            return self._setup_tokens(setup.get("tokens") or [], admin_token)
        if phase == "assets":
            return self._setup_assets(setup.get("assets") or [], admin_token)
        if phase == "fiat":
            return self._setup_fiat_accounts(setup.get("fiat_accounts") or [], admin_token)
        # Unreachable — phase was validated above.
        return False

    def _run_full(self, setup: Dict[str, Any]) -> bool:
        """The complete bootstrap (the `all` phase): users → groups →
        owners → tokens → assets → fiat, in the order the shell expects."""
        self.logger.cyan("🚀 Running system setup")
        if not self._ensure_services():
            return False

        all_ok = True

        # 1. Users.
        self.logger.subsection("👥 Users")
        all_ok &= self._setup_users(setup.get("users") or [])
        self._users_ensured = True

        # Everything else needs an admin token. Use the API key if set,
        # else the FIRST user in the YAML (conventionally a SuperAdmin).
        admin_token = self._ensure_admin(setup)
        if not admin_token:
            self.logger.error("❌ Could not acquire an admin token; aborting")
            return False

        # 2. Groups (create + per-creator login + deploy + members).
        self.logger.subsection("🏢 Groups")
        all_ok &= self._setup_groups(setup.get("groups") or [], admin_token)

        # 2b. On-chain account owners / relationships. No-op when no group
        # declares members (the common case for the current setup.yaml),
        # so existing token/asset-only files are unaffected.
        groups = setup.get("groups") or []
        if any((g.get("members") for g in groups)):
            self.logger.subsection("🔗 Group owners")
            all_ok &= self._setup_owners(groups, admin_token)

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
    # Cached prerequisites (shared across phases in one invocation).
    # ------------------------------------------------------------------

    def _ensure_services(self) -> bool:
        """Validate auth + payments are reachable (once per runner)."""
        if self._services_ok is None:
            self._services_ok = self.service_validator.validate_services()
        return self._services_ok

    def _ensure_users(self, setup: Dict[str, Any]) -> None:
        """Idempotently create the declared users (once per runner),
        populating `_user_ids` for downstream member resolution."""
        if not self._users_ensured:
            self._setup_users(setup.get("users") or [])
            self._users_ensured = True

    def _ensure_admin(self, setup: Dict[str, Any]) -> Optional[str]:
        """Acquire and cache the admin JWT (API key, else first user)."""
        if self._admin_token is None:
            self._admin_token = self._acquire_admin_token(setup.get("users") or [])
        return self._admin_token

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
            user_id = None
            if status == "created":
                user_id = result.get("user_id")
                self.logger.success(f"  ✅ {email} ({role}) created")
            elif status == "exists":
                # Already there — log in to learn the user_id so we can
                # still add them to groups downstream.
                self.logger.info(f"  ⚠️  {email} already exists; logging in to recover user_id")
                user_id = self._login_and_extract_user_id(email, password)
            else:
                self.logger.error(f"  ❌ {email}: {result.get('message')}")
                ok = False
                continue

            if user_id:
                self._user_ids[email] = user_id
                # Log in (triggers the account deploy) and print the
                # deployed default account address — shell parity.
                self._print_user_account_address(user_id, email, password)
            else:
                self.logger.warning(
                    f"  ⚠️  {email}: no user_id resolved; cannot show account address"
                )
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
        Acquire the admin JWT used for tokens/assets/fiat and group-member
        operations. Preference order:

          1. `config.api_key` (API_KEY env) — the canonical backend-service
             auth path. Exchanged for a short-lived JWT via POST /auth/api-key.
             The key owner must have enough permissions (SuperAdmin/Admin)
             for the create-* mutations downstream.
          2. The first user in setup.yaml (conventionally a SuperAdmin),
             logged in with email/password.
        """
        if self.config.api_key:
            self.logger.info("  🔑 Using API key for admin token")
            token = self.auth_service.authenticate_api_key(self.config.api_key)
            if token:
                return token
            self.logger.warning(
                "  ⚠️  API-key auth failed; falling back to first-user login"
            )

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

            if not name:
                self.logger.error(f"  ❌ group missing name: {group}")
                ok = False
                continue

            # A group needs a creator identity. If `user` is declared, log
            # in as that user (the group's initial owner). Otherwise fall
            # back to the admin token — works when setup runs under an
            # API key and the key owner is the intended group owner.
            if creator_email and creator_password:
                creator_token = self.auth_service.login(creator_email, creator_password)
                if not creator_token:
                    self.logger.error(
                        f"  ❌ could not log in creator {creator_email} for group {name}"
                    )
                    ok = False
                    continue
            else:
                self.logger.info(
                    f"  ℹ️  group {name} has no user.id/user.password; "
                    f"creating as admin principal"
                )
                creator_token = admin_token

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

            # Print the deployed group account address — shell parity.
            self._print_group_account_address(creator_token, group_id, name)

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

    # ------------------------------------------------------------------
    # Deployed account-address reporting — parity with setup_system.sh's
    # print_user_account_address / print_group_account_address.
    #
    # Account deployment is async (MQ): a user's default account deploys
    # on first login (auth `ensure_account_deployment_for_auth`); a
    # group's account deploys on creation. We poll the read endpoints
    # until the deterministic CREATE2 address appears, then print it.
    # ------------------------------------------------------------------

    _ACCT_POLL_ATTEMPTS = 12       # ~24s ceiling, matching the shell's loop
    _ACCT_POLL_INTERVAL = 2.0
    _ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    def _print_user_account_address(
        self, user_id: str, email: str, password: str
    ) -> None:
        """
        Log in as the user (which ALSO triggers the deploy) and print
        their default on-chain account address, polling until it shows up.

        The chain-accounts endpoint forbids reading another user's
        accounts, so this reads with the user's OWN token — exactly as
        the shell does.
        """
        token = self.auth_service.login(email, password)
        if not token:
            self.logger.warning("      🏦 account: (login failed; cannot read address)")
            return
        for attempt in range(self._ACCT_POLL_ATTEMPTS):
            accounts = self.auth_service.get_user_chain_accounts(token, user_id)
            addr, chain = self._pick_chain_account(accounts)
            if addr:
                self.logger.purple(f"      🏦 account: {addr} (chain {chain})")
                return
            if attempt < self._ACCT_POLL_ATTEMPTS - 1:
                time.sleep(self._ACCT_POLL_INTERVAL)
        self.logger.warning("      🏦 account: (not on chain yet)")

    def _print_group_account_address(
        self, token: str, group_id: str, name: str
    ) -> None:
        """Print a group's deployed account address, polling the
        account-status endpoint until the (non-zero) address appears."""
        for attempt in range(self._ACCT_POLL_ATTEMPTS):
            info = self.auth_service.group_account_info(token, group_id)
            addr = info.get("account_address")
            status = info.get("status")
            if addr and addr != self._ZERO_ADDRESS:
                suffix = f" ({status})" if status else ""
                self.logger.purple(f"      🏦 account: {addr}{suffix}")
                return
            if attempt < self._ACCT_POLL_ATTEMPTS - 1:
                time.sleep(self._ACCT_POLL_INTERVAL)
        self.logger.warning("      🏦 account: (not on chain yet)")

    @staticmethod
    def _pick_chain_account(accounts: Any):
        """
        Mirror the shell's jq selection: prefer the default wallet, else
        the first account that actually carries an address. Returns
        (account_address, chain_id) or (None, None).
        """
        if not isinstance(accounts, list):
            return None, None
        ordered = [a for a in accounts if isinstance(a, dict) and a.get("is_default")]
        ordered += [a for a in accounts if isinstance(a, dict) and not a.get("is_default")]
        for a in ordered:
            addr = a.get("account_address")
            if addr not in (None, ""):
                return addr, a.get("chain_id")
        return None, None

    @staticmethod
    def _normalize_eth_address(value: Any) -> str:
        """
        Coerce a YAML-parsed address back to canonical 0x + 40-hex.

        PyYAML's safe_load parses an unquoted `0x03420F…` as a Python int
        (it's a valid hex literal), so by the time we see it the `0x`
        prefix and any leading zeros are gone and the value is an int.
        Rebuild the 20-byte (40 hex char) representation. Strings are
        passed through (lower-cased, 0x-prefixed) so a quoted YAML value
        still works.
        """
        if value is None:
            return ""
        if isinstance(value, int):
            # 20-byte address → 40 hex chars, zero-padded.
            return "0x" + format(value, "040x")
        s = str(value).strip()
        if not s:
            return ""
        if s.lower().startswith("0x"):
            return "0x" + s[2:]
        return "0x" + s

    def _setup_tokens(self, tokens: List[Dict[str, Any]], admin_token: str) -> bool:
        ok = True
        for t in tokens:
            token_id = t.get("id")
            name = t.get("name")
            description = t.get("description") or ""
            address = self._normalize_eth_address(t.get("address"))
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

    def _setup_owners(
        self,
        groups: List[Dict[str, Any]],
        admin_token: str,
    ) -> bool:
        """
        The `owners` phase — port of `setup_system.sh`'s
        `setup_group_relationships`.

        For each declared group: resolve its real UUID by name (YAML ids
        are human labels, not UUIDs), ensure the on-chain account is
        deployed, then for every declared member add them BOTH as a group
        member (role-scoped) AND as an on-chain account owner. The
        add-owner call uses a group-scoped delegation JWT, matching the
        shell's `add_member_as_owner`.

        Idempotent: re-adding an existing member/owner is a no-op on the
        backend. Safe to run standalone (assumes groups already exist;
        creates a missing group on the fly to mirror the shell).
        """
        if not groups:
            self.logger.info("  (no groups declared)")
            return True

        ok = True
        for group in groups:
            name = group.get("name")
            if not name:
                self.logger.error(f"  ❌ group missing name: {group}")
                ok = False
                continue

            members = group.get("members") or []

            # Resolve the real group UUID by name.
            group_id = self.auth_service.get_group_id_by_name(admin_token, name)
            if not group_id:
                # Mirror the shell: try to create it, then re-resolve.
                creator = group.get("user") or {}
                creator_token = admin_token
                if creator.get("id") and creator.get("password"):
                    ct = self.auth_service.login(creator["id"], creator["password"])
                    if ct:
                        creator_token = ct
                self.auth_service.create_group(
                    creator_token,
                    name=name,
                    description=group.get("description") or "",
                    group_type=group.get("group_type", "project"),
                )
                group_id = self.auth_service.get_group_id_by_name(admin_token, name)
            if not group_id:
                self.logger.error(f"  ❌ could not resolve group id for {name}; skipping")
                ok = False
                continue

            # The account must be deployed before owners can be added.
            ok &= self._deploy_group_if_needed(admin_token, name, group_id)

            if not members:
                self.logger.info(f"  ℹ️  group {name} has no members; nothing to own")
                continue

            # Prefer the group creator's token for member/owner ops (the
            # shell does this); fall back to the admin token.
            creator = group.get("user") or {}
            member_token = admin_token
            if creator.get("id") and creator.get("password"):
                ct = self.auth_service.login(creator["id"], creator["password"])
                if ct:
                    member_token = ct

            # add-owner expects a group-scoped delegation JWT.
            delegation = self.auth_service.create_delegation_token(
                member_token, group_id, name
            )
            owner_token = delegation or member_token

            for m in members:
                m_email = m.get("id")
                m_role = m.get("role", "member")
                if not m_email:
                    continue
                m_user_id = self._user_ids.get(m_email)
                if not m_user_id and m.get("password"):
                    m_user_id = self._login_and_extract_user_id(m_email, m["password"])
                if not m_user_id:
                    self.logger.error(
                        f"    ❌ member {m_email}: unknown user_id (was the user created?)"
                    )
                    ok = False
                    continue

                # 1. Group membership (role-scoped, idempotent).
                self.auth_service.add_group_member(
                    member_token, group_id, m_user_id, m_role
                )
                # 2. On-chain account owner.
                res = self.auth_service.add_group_owner(owner_token, group_id, m_user_id)
                if res.get("status") == "error":
                    self.logger.warning(
                        f"    ⚠️  owner {m_email}: {res.get('message')}"
                    )
                    ok = False
                else:
                    self.logger.success(f"    ✅ owner {m_email} ({m_role})")
        return ok

    # ------------------------------------------------------------------
    # Read-only / offline phases (validate, status).
    # ------------------------------------------------------------------

    def validate(self, setup_file: str) -> bool:
        """Public entry: parse + structurally validate a setup file
        (offline). Returns True iff the structure is valid."""
        setup = self._parse_setup_file(setup_file)
        if setup is None:
            return False
        return self._validate(setup, setup_file)

    def show_status(self, setup_file: str) -> bool:
        """Public entry: parse + print a status summary."""
        setup = self._parse_setup_file(setup_file)
        if setup is None:
            return False
        return self._status(setup, setup_file)

    def _validate(self, setup: Dict[str, Any], setup_file: str) -> bool:
        """
        Offline structural validation — port of `validate_setup_file`.
        Checks required fields per item across every section. No network
        calls. Returns True iff there are no errors.
        """
        self.logger.cyan(f"🔍 Validating {os.path.basename(setup_file)}...")

        users = setup.get("users") or []
        groups = setup.get("groups") or []
        tokens = setup.get("tokens") or []
        assets = setup.get("assets") or []
        fiat = setup.get("fiat_accounts") or []

        errors: List[str] = []
        valid_member_roles = {"owner", "admin", "member", "viewer", "policymember"}
        valid_fiat_currencies = {"USD", "GBP", "AUD"}

        if not (users or groups or tokens or assets or fiat):
            errors.append(
                "file declares none of: users, groups, tokens, assets, fiat_accounts"
            )

        for i, u in enumerate(users):
            if not u.get("id"):
                errors.append(f"users[{i}]: missing id (email)")
            if not u.get("password"):
                errors.append(f"users[{i}]: missing password")

        for i, g in enumerate(groups):
            if not g.get("name"):
                errors.append(f"groups[{i}]: missing name")
            for j, m in enumerate(g.get("members") or []):
                if not m.get("id"):
                    errors.append(f"groups[{i}].members[{j}]: missing id")
                role = (m.get("role") or "").lower()
                if role and role not in valid_member_roles:
                    errors.append(
                        f"groups[{i}].members[{j}]: invalid role {m.get('role')!r} "
                        f"(valid: {', '.join(sorted(valid_member_roles))})"
                    )

        for i, t in enumerate(tokens):
            for field in ("id", "name", "chain_id", "address"):
                if t.get(field) in (None, ""):
                    errors.append(f"tokens[{i}]: missing {field}")

        for i, a in enumerate(assets):
            if not (a.get("type") or a.get("asset_type")):
                errors.append(f"assets[{i}]: missing type")
            for field in ("name", "currency", "token_id"):
                if a.get(field) in (None, ""):
                    errors.append(f"assets[{i}]: missing {field}")

        for i, fa in enumerate(fiat):
            if not fa.get("id"):
                errors.append(f"fiat_accounts[{i}]: missing id")
            currency = (fa.get("currency") or "").upper()
            if currency not in valid_fiat_currencies:
                errors.append(
                    f"fiat_accounts[{i}]: unsupported currency {fa.get('currency')!r} "
                    f"(supported: USD, GBP, AUD)"
                )

        self.logger.info(
            f"  users={len(users)} groups={len(groups)} tokens={len(tokens)} "
            f"assets={len(assets)} fiat={len(fiat)}"
        )
        if errors:
            self.logger.error(f"  ❌ {len(errors)} validation error(s):")
            for err in errors:
                self.logger.error(f"    - {err}")
            return False
        self.logger.success("  ✅ setup file is structurally valid")
        return True

    def _status(self, setup: Dict[str, Any], setup_file: str) -> bool:
        """
        Read-only status summary — port of `show_setup_status`. Reports
        service reachability (best-effort, non-fatal) plus a count of
        each section. Always returns True (informational).
        """
        self.logger.cyan("📊 Setup status")

        # Service reachability — informational, never fails the phase, and
        # uses the validator directly so it doesn't poison the cached flag.
        self.service_validator.validate_services()

        users = setup.get("users") or []
        groups = setup.get("groups") or []
        tokens = setup.get("tokens") or []
        assets = setup.get("assets") or []
        fiat = setup.get("fiat_accounts") or []

        self.logger.info(f"  📄 file: {setup_file}")
        self.logger.info(f"  👥 users:  {len(users)}")
        self.logger.info(f"  🏢 groups: {len(groups)}")
        for g in groups:
            members = g.get("members") or []
            self.logger.info(f"     - {g.get('name')} ({len(members)} member(s))")
        self.logger.info(f"  🪙 tokens: {len(tokens)}")
        self.logger.info(f"  💎 assets: {len(assets)}")
        self.logger.info(f"  🏦 fiat:   {len(fiat)}")
        self.logger.info(f"  🔑 API key configured: {bool(self.config.api_key)}")
        return True

    def close(self):
        self.auth_service.close()
        self.payments_service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


