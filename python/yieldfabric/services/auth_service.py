"""
Auth service client
"""

from typing import List, Optional

from .base import BaseServiceClient
from ..config import YieldFabricConfig


class AuthService(BaseServiceClient):
    """Client for Auth Service."""
    
    def __init__(self, config: YieldFabricConfig):
        """
        Initialize Auth Service client.
        
        Args:
            config: YieldFabric configuration
        """
        super().__init__(config.auth_service_url, config)
    
    def login(self, email: str, password: str) -> Optional[str]:
        """
        Login user and get JWT token.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            JWT token or None if login fails
        """
        self.logger.info(f"  🔐 Logging in user: {email}")
        
        payload = {
            "email": email,
            "password": password,
            "services": ["vault", "payments"]
        }
        
        try:
            response = self._post("/auth/login/with-services", payload)
            data = response.json()
            
            self.logger.debug(f"    📡 Login response: {data}")
            
            token = data.get('token') or data.get('access_token') or data.get('jwt')
            
            if token:
                self.logger.success("    ✅ Login successful")
                return token
            else:
                self.logger.error("    ❌ No token in response")
                return None
        
        except Exception as e:
            self.logger.error(f"    ❌ Login failed: {e}")
            return None
    
    def get_groups(self, token: str) -> List[dict]:
        """
        Get list of groups for user.
        
        Args:
            token: JWT token
            
        Returns:
            List of group dictionaries
        """
        self.logger.debug("  🏢 Fetching user groups")
        
        try:
            response = self._get("/auth/groups", token=token)
            groups = response.json()
            
            if isinstance(groups, list):
                self.logger.debug(f"    ✅ Found {len(groups)} groups")
                return groups
            else:
                self.logger.warning("    ⚠️  Unexpected response format")
                return []
        
        except Exception as e:
            self.logger.error(f"    ❌ Failed to fetch groups: {e}")
            return []
    
    def get_user_groups(self, token: str) -> List[dict]:
        """
        Get list of groups the user is a member of.
        
        Args:
            token: JWT token
            
        Returns:
            List of group dictionaries
        """
        self.logger.debug("  🏢 Fetching user groups (member of)")
        
        try:
            response = self._get("/auth/groups/user", token=token)
            groups = response.json()
            
            if isinstance(groups, list):
                self.logger.debug(f"    ✅ Found {len(groups)} groups")
                return groups
            else:
                self.logger.warning("    ⚠️  Unexpected response format")
                return []
        
        except Exception as e:
            self.logger.error(f"    ❌ Failed to fetch user groups: {e}")
            return []
    
    def get_group_id_by_name(self, token: str, group_name: str) -> Optional[str]:
        """
        Get group ID by name.
        
        Args:
            token: JWT token
            group_name: Name of the group
            
        Returns:
            Group ID or None if not found
        """
        self.logger.info(f"  🔍 Looking up group ID for: {group_name}")
        
        groups = self.get_groups(token)
        
        for group in groups:
            if group.get("name") == group_name:
                group_id = group.get("id")
                self.logger.success(f"    ✅ Found group ID: {group_id[:8] if group_id else 'N/A'}...")
                return group_id
        
        self.logger.error(f"    ❌ Group not found: {group_name}")
        return None
    
    def create_delegation_token(self, user_token: str, group_id: str, group_name: str) -> Optional[str]:
        """
        Create delegation JWT token for a specific group.
        
        Args:
            user_token: User JWT token
            group_id: ID of the group
            group_name: Name of the group (for logging)
            
        Returns:
            Delegation JWT token or None if creation fails
        """
        self.logger.info(f"  🎫 Creating delegation JWT for group: {group_name}")
        self.logger.debug(f"    Group ID: {group_id[:8] if group_id else 'N/A'}...")
        
        payload = {
            "group_id": group_id,
            "delegation_scope": self.config.delegation_scopes,
            "expiry_seconds": self.config.jwt_expiry_seconds
        }
        
        try:
            response = self._post("/auth/delegation/jwt", payload, token=user_token)
            data = response.json()
            
            self.logger.debug(f"    Delegation response: {data}")
            
            delegation_token = (
                data.get('delegation_jwt') or
                data.get('token') or
                data.get('delegation_token') or
                data.get('jwt')
            )
            
            if delegation_token:
                self.logger.success("    ✅ Delegation JWT created successfully")
                return delegation_token
            else:
                self.logger.error("    ❌ Failed to create delegation JWT")
                self.logger.warning(f"    Response: {data}")
                return None
        
        except Exception as e:
            self.logger.error(f"    ❌ Failed to create delegation JWT: {e}")
            return None
    
    def login_with_group(self, email: str, password: str, group_name: str) -> Optional[str]:
        """
        Login user and create delegation token for a specific group.

        Args:
            email: User email
            password: User password
            group_name: Name of the group for delegation

        Returns:
            Delegation JWT token or regular token if delegation fails
        """
        # First, login to get user token
        token = self.login(email, password)
        if not token:
            return None

        # Get group ID
        self.logger.cyan(f"  🏢 Group delegation requested for: {group_name}")
        group_id = self.get_group_id_by_name(token, group_name)

        if not group_id:
            self.logger.warning("    ⚠️  Group not found, using regular token")
            return token

        # Create delegation token
        delegation_token = self.create_delegation_token(token, group_id, group_name)

        if delegation_token:
            self.logger.success("    ✅ Group delegation successful")
            return delegation_token
        else:
            self.logger.warning("    ⚠️  Delegation failed, using regular token")
            return token

    # ------------------------------------------------------------------
    # Group-admin operations (auth-service REST endpoints).
    # These mirror the shell functions in executors_additional.sh:
    #   execute_add_owner / execute_remove_owner
    #   execute_add_account_member / execute_remove_account_member
    #   execute_get_account_owners / execute_get_account_members
    # All expect a group_id resolved via get_group_id_by_name first.
    # ------------------------------------------------------------------

    def get_user_group_id_by_name(self, token: str, group_name: str) -> Optional[str]:
        """
        Resolve group name → group id, searching groups the user is a
        MEMBER of (GET /auth/groups/user). Some admin operations require
        this narrower view rather than the full groups list.
        """
        groups = self.get_user_groups(token)
        for group in groups:
            if group.get("name") == group_name:
                return group.get("id")
        self.logger.error(f"    ❌ Group not found in user's groups: {group_name}")
        return None

    def add_group_owner(self, token: str, group_id: str, new_owner: str) -> dict:
        """POST /auth/groups/{id}/add-owner — add an on-chain owner."""
        self.logger.info(
            f"  📤 add_group_owner group_id={group_id[:8]}... new_owner={new_owner}"
        )
        return self._post_json_safe(
            f"/auth/groups/{group_id}/add-owner",
            {"new_owner": new_owner},
            token=token,
            description="add_group_owner",
        )

    def remove_group_owner(self, token: str, group_id: str, old_owner: str) -> dict:
        """POST /auth/groups/{id}/remove-owner — remove an on-chain owner."""
        self.logger.info(
            f"  📤 remove_group_owner group_id={group_id[:8]}... old_owner={old_owner}"
        )
        return self._post_json_safe(
            f"/auth/groups/{group_id}/remove-owner",
            {"old_owner": old_owner},
            token=token,
            description="remove_group_owner",
        )

    def add_account_member(
        self,
        token: str,
        group_id: str,
        obligation_id: str,
        obligation_address: Optional[str] = None,
    ) -> dict:
        """
        POST /auth/groups/{id}/add-account-member — grant a group wallet
        permission to hold the given obligation/NFT. `obligation_address`
        is optional; the backend falls back to its configured default
        confidential-obligation address when None.
        """
        payload: dict = {"obligation_id": obligation_id}
        if obligation_address:
            payload["obligation_address"] = obligation_address
        self.logger.info(
            f"  📤 add_account_member group_id={group_id[:8]}... obligation_id={obligation_id}"
        )
        return self._post_json_safe(
            f"/auth/groups/{group_id}/add-account-member",
            payload,
            token=token,
            description="add_account_member",
        )

    def remove_account_member(
        self,
        token: str,
        group_id: str,
        obligation_id: str,
        obligation_address: Optional[str] = None,
    ) -> dict:
        """POST /auth/groups/{id}/remove-account-member."""
        payload: dict = {"obligation_id": obligation_id}
        if obligation_address:
            payload["obligation_address"] = obligation_address
        self.logger.info(
            f"  📤 remove_account_member group_id={group_id[:8]}... obligation_id={obligation_id}"
        )
        return self._post_json_safe(
            f"/auth/groups/{group_id}/remove-account-member",
            payload,
            token=token,
            description="remove_account_member",
        )

    def get_account_owners(self, token: str, group_id: str) -> dict:
        """GET /auth/groups/{id}/account-owners — returns {account_address, owners: [...]}"""
        return self._get_json_safe(
            f"/auth/groups/{group_id}/account-owners",
            token=token,
            description="get_account_owners",
            default={"status": "error", "owners": []},
        )

    def get_account_members(self, token: str, group_id: str) -> dict:
        """GET /auth/groups/{id}/account-members — returns {account_address, members: [...]}"""
        return self._get_json_safe(
            f"/auth/groups/{group_id}/account-members",
            token=token,
            description="get_account_members",
            default={"status": "error", "members": []},
        )

    # ------------------------------------------------------------------
    # Setup-phase operations.
    # Mirror `setup_system.sh` — create users, groups, add members, and
    # deploy group on-chain accounts. All handle 409 Conflict as idempotent
    # "already exists" (matching the shell's retry-safe behaviour).
    # ------------------------------------------------------------------

    def create_user(
        self,
        email: str,
        password: str,
        role: str,
        admin_token: Optional[str] = None,
    ) -> dict:
        """
        POST /auth/users — idempotent wrt email.

        Returns a dict:
            {"status": "created", "user_id": "..."}
            {"status": "exists"}   (HTTP 409)
            {"status": "error", "message": "..."}

        `admin_token` is optional: the first user can be created without
        auth; subsequent users typically need an admin JWT (though the
        auth service may allow creation without auth in dev — the shell
        passes a token when available and falls back to unauthenticated).
        """
        self.logger.info(f"  👤 create_user email={email} role={role}")
        import requests as _requests
        try:
            headers = {"Content-Type": "application/json"}
            if admin_token:
                headers["Authorization"] = f"Bearer {admin_token}"
            response = self.session.post(
                f"{self.base_url}/auth/users",
                json={"email": email, "password": password, "role": role},
                headers=headers,
                timeout=self.config.request_timeout,
            )
            if response.status_code == 200:
                data = response.json()
                user_id = (data.get("user") or {}).get("id") or data.get("id")
                return {"status": "created", "user_id": user_id}
            if response.status_code == 409:
                return {"status": "exists"}
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text[:200]}",
            }
        except _requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def create_group(
        self,
        creator_token: str,
        name: str,
        description: str,
        group_type: str = "project",
    ) -> dict:
        """
        POST /auth/groups — create a group as the caller identified by
        `creator_token`. The creator is the group's initial owner.

        Returns:
            {"status": "created", "group_id": "..."}
            {"status": "exists"}          (HTTP 409)
            {"status": "error", "message"}
        """
        self.logger.info(f"  🏢 create_group name={name} type={group_type}")
        import requests as _requests
        try:
            response = self.session.post(
                f"{self.base_url}/auth/groups",
                json={"name": name, "description": description, "group_type": group_type},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {creator_token}",
                },
                timeout=self.config.request_timeout,
            )
            if response.status_code == 200:
                return {"status": "created", "group_id": response.json().get("id")}
            if response.status_code == 409:
                return {"status": "exists"}
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text[:200]}",
            }
        except _requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def add_group_member(
        self,
        admin_token: str,
        group_id: str,
        user_id: str,
        role: str,
    ) -> dict:
        """
        POST /auth/groups/{id}/members — add a user to a group with a
        named role. Valid roles: owner, admin, member, viewer.
        """
        if role not in ("owner", "admin", "member", "viewer"):
            return {"status": "error", "message": f"invalid role: {role}"}

        self.logger.info(f"  ➕ add_group_member group={group_id[:8]}... user={user_id[:8]}... role={role}")
        import requests as _requests
        try:
            response = self.session.post(
                f"{self.base_url}/auth/groups/{group_id}/members",
                json={"user_id": user_id, "role": role},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {admin_token}",
                },
                timeout=self.config.request_timeout,
            )
            if response.status_code == 200:
                return {"status": "added"}
            if response.status_code == 409:
                return {"status": "exists"}
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {response.text[:200]}",
            }
        except _requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def group_account_status(self, token: str, group_id: str) -> Optional[str]:
        """
        GET /auth/groups/{id}/account-status — returns the status string
        (e.g. "deployed", "not_deployed") or None if the response is
        malformed / endpoint errored.
        """
        try:
            response = self._get(
                f"/auth/groups/{group_id}/account-status",
                token=token,
            )
            data = response.json()
            return (data.get("account_status") or {}).get("status")
        except Exception as e:
            self.logger.error(f"    ❌ group_account_status failed: {e}")
            return None

    # ------------------------------------------------------------------
    # External-key management (loan_management parity).
    #
    # Port of `loan_management/modules/register_external_key.py` REST
    # calls. The crypto primitives (generate key / sign message) live
    # in `yieldfabric.utils.crypto`; this class handles only the HTTP.
    # ------------------------------------------------------------------

    def get_user_id_from_profile(self, token: str) -> Optional[str]:
        """
        GET /auth/users/me — returns the logged-in user's UUID.

        Needed when we only have a JWT (e.g. after login) and need the
        user_id for downstream endpoints like `register_external_key`
        or `deploy-account`, neither of which extract it from the
        bearer themselves.
        """
        try:
            response = self._get("/auth/users/me", token=token)
            data = response.json()
            user = data.get("user") if isinstance(data, dict) else None
            if isinstance(user, dict):
                uid = user.get("id")
                return str(uid).strip() if uid else None
        except Exception as e:
            self.logger.debug(f"get_user_id_from_profile failed: {e}")
        return None

    def register_external_key(
        self,
        token: str,
        *,
        user_id: str,
        key_name: str,
        public_key: str,
        register_with_wallet: bool = False,
        expires_at: Optional[str] = None,
    ) -> dict:
        """
        POST /keys/external — register an external (client-generated)
        key for `user_id`. `public_key` is a 0x-prefixed Ethereum
        address. Returns the key pair record (includes `id` used by
        `register_key_with_specific_wallet`).
        """
        payload: dict = {
            "user_id": user_id,
            "key_name": key_name,
            "public_key": public_key,
            "register_with_wallet": register_with_wallet,
        }
        if expires_at is not None:
            payload["expires_at"] = expires_at
        try:
            response = self._post("/keys/external", payload, token=token)
            return response.json()
        except Exception as e:
            raise RuntimeError(f"register_external_key failed: {e}") from e

    def verify_external_key_ownership(
        self,
        token: str,
        *,
        public_key: str,
        message: str,
        signature: str,
        signature_format: str = "hex",
    ) -> dict:
        """
        POST /keys/external/verify-ownership — confirm (before
        registering) that the signer actually holds `public_key`.

        This call is what the frontend makes before POST /keys/external
        so the user gets a clear error if the ownership proof is
        malformed. The backend returns {"valid": bool, "message": ...}.
        """
        payload = {
            "public_key": public_key,
            "message": message,
            "signature": signature,
            "signature_format": signature_format,
        }
        try:
            response = self._post(
                "/keys/external/verify-ownership", payload, token=token
            )
            return response.json()
        except Exception as e:
            raise RuntimeError(f"verify_external_key_ownership failed: {e}") from e

    def get_user_keys(self, token: str, user_id: str) -> List[dict]:
        """
        GET /keys/users/{user_id}/keys — list every key pair registered
        to this user. Returns [] on any failure.
        """
        try:
            response = self._get(f"/keys/users/{user_id}/keys", token=token)
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.debug(f"get_user_keys failed: {e}")
            return []

    def get_key_id_by_address(
        self, token: str, user_id: str, address: str
    ) -> Optional[str]:
        """
        Look up a key's UUID id by its on-chain address. Normalises both
        sides to lowercase + 0x-prefixed before comparing, so a caller
        can pass any common casing. Returns None if the key isn't
        registered to this user.
        """
        want = (address or "").strip().lower()
        if not want:
            return None
        if not want.startswith("0x"):
            want = "0x" + want
        for k in self.get_user_keys(token, user_id):
            pk = (k.get("public_key") or "").strip().lower()
            if pk and not pk.startswith("0x"):
                pk = "0x" + pk
            if pk == want:
                kid = k.get("id")
                return str(kid) if kid else None
        return None

    def register_key_with_specific_wallet(
        self, token: str, *, key_id: str, wallet_address: str
    ) -> dict:
        """
        POST /keys/register-with-specific-wallet — register an already
        existing key as an owner of a specific wallet (e.g. a loan
        wallet). Returns the backend's response dict.
        """
        payload = {"key_id": key_id, "wallet_address": (wallet_address or "").strip()}
        try:
            response = self._post(
                "/keys/register-with-specific-wallet", payload, token=token
            )
            return response.json()
        except Exception as e:
            raise RuntimeError(f"register_key_with_specific_wallet failed: {e}") from e

    def deploy_group_account(self, token: str, group_id: str) -> dict:
        """
        POST /auth/groups/{id}/deploy-account — deploy the group's
        on-chain account. Safe to call only when status is "not_deployed";
        callers should check `group_account_status` first.
        """
        self.logger.info(f"  🚀 deploy_group_account group={group_id[:8]}...")
        try:
            response = self._post(
                f"/auth/groups/{group_id}/deploy-account",
                data={},
                token=token,
            )
            return response.json()
        except Exception as e:
            self.logger.error(f"    ❌ deploy_group_account failed: {e}")
            return {"status": "error", "message": str(e)}

