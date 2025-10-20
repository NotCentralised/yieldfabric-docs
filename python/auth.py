"""
YieldFabric Authentication Module
Contains functions for user authentication and group delegation.
"""

import json
import requests
from typing import Optional
from .utils import Colors, echo_with_color, check_service_running


class AuthService:
    """Handle authentication and group delegation operations."""
    
    def __init__(self, auth_service_url: str = "https://auth.yieldfabric.io"):
        self.auth_service_url = auth_service_url
    
    def get_group_id_by_name(self, token: str, group_name: str) -> Optional[str]:
        """Get group ID by name from auth service."""
        echo_with_color(Colors.BLUE, f"  🔍 Looking up group ID for: {group_name}")
        
        try:
            response = requests.get(
                f"{self.auth_service_url}/auth/groups",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            response.raise_for_status()
            
            groups = response.json()
            for group in groups:
                if group.get('name') == group_name:
                    group_id = group.get('id')
                    if group_id and group_id != "null":
                        echo_with_color(Colors.GREEN, f"    ✅ Found group ID: {group_id[:8]}...")
                        return group_id
            
            echo_with_color(Colors.RED, f"    ❌ Group not found: {group_name}")
            return None
            
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Failed to retrieve groups list: {e}")
            return None
    
    def create_delegation_token(self, user_token: str, group_id: str, group_name: str) -> Optional[str]:
        """Create delegation JWT token for a specific group."""
        echo_with_color(Colors.BLUE, f"  🎫 Creating delegation JWT for group: {group_name}")
        echo_with_color(Colors.BLUE, f"    Group ID: {group_id[:8]}...")
        
        try:
            payload = {
                "group_id": group_id,
                "delegation_scope": ["CryptoOperations", "ReadGroup", "UpdateGroup", "ManageGroupMembers"],
                "expiry_seconds": 3600
            }
            
            response = requests.post(
                f"{self.auth_service_url}/auth/delegation/jwt",
                headers={
                    "Authorization": f"Bearer {user_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )
            
            echo_with_color(Colors.BLUE, f"    Delegation response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                delegation_token = (
                    data.get('delegation_jwt') or 
                    data.get('token') or 
                    data.get('delegation_token') or 
                    data.get('jwt')
                )
                
                if delegation_token and delegation_token != "null":
                    echo_with_color(Colors.GREEN, "    ✅ Delegation JWT created successfully")
                    return delegation_token
                else:
                    echo_with_color(Colors.RED, "    ❌ Failed to create delegation JWT")
                    echo_with_color(Colors.YELLOW, f"    Response: {response.text}")
                    return None
            else:
                echo_with_color(Colors.RED, f"    ❌ Failed to create delegation JWT: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Failed to create delegation JWT: {e}")
            return None
    
    def login_user(self, email: str, password: str, group_name: Optional[str] = None) -> Optional[str]:
        """Login user and get JWT token (with optional group delegation)."""
        echo_with_color(Colors.BLUE, f"  🔐 Logging in user: {email}")
        
        services_json = ["vault", "payments"]
        payload = {
            "email": email,
            "password": password,
            "services": services_json
        }
        
        try:
            response = requests.post(
                f"{self.auth_service_url}/auth/login/with-services",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            
            echo_with_color(Colors.BLUE, f"    📡 Login response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                token = (
                    data.get('token') or 
                    data.get('access_token') or 
                    data.get('jwt')
                )
                
                if token and token != "null":
                    echo_with_color(Colors.GREEN, "    ✅ Login successful")
                    
                    # If group name is specified, create delegation token
                    if group_name and group_name != "null":
                        echo_with_color(Colors.CYAN, f"  🏢 Group delegation requested for: {group_name}")
                        
                        # Get group ID by name
                        group_id = self.get_group_id_by_name(token, group_name)
                        if group_id:
                            # Create delegation token
                            delegation_token = self.create_delegation_token(token, group_id, group_name)
                            if delegation_token:
                                echo_with_color(Colors.GREEN, "    ✅ Group delegation successful")
                                return delegation_token
                            else:
                                echo_with_color(Colors.YELLOW, "    ⚠️  Delegation failed, using regular token")
                                return token
                        else:
                            echo_with_color(Colors.YELLOW, "    ⚠️  Group not found, using regular token")
                            return token
                    else:
                        return token
                else:
                    echo_with_color(Colors.RED, "    ❌ No token in response")
                    return None
            else:
                echo_with_color(Colors.RED, f"    ❌ Login failed: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Login failed: {e}")
            return None


# Global auth service instance
auth_service = AuthService()
