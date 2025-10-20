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

