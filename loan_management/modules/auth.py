"""Auth service: login, user profile, deploy account, service health check."""

import sys
from typing import Optional

import requests

from .console import BLUE, CYAN, GREEN, RED, echo_with_color


def check_service_running(service_name: str, service_url: str) -> bool:
    """Check if a service is running and reachable."""
    echo_with_color(BLUE, f"  🔍 Checking if {service_name} is running...")
    try:
        if service_url.startswith(("http://", "https://")):
            for url in (f"{service_url.rstrip('/')}/health", service_url.rstrip("/")):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code < 500:
                        echo_with_color(GREEN, f"    ✅ {service_name} is reachable")
                        return True
                except Exception:
                    continue
            echo_with_color(RED, f"    ❌ {service_name} is not reachable at {service_url}")
            return False
        else:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", int(service_url)))
            sock.close()
            if result == 0:
                echo_with_color(GREEN, f"    ✅ {service_name} is running on port {service_url}")
                return True
            echo_with_color(RED, f"    ❌ {service_name} is not running on port {service_url}")
            return False
    except Exception as e:
        echo_with_color(RED, f"    ❌ Error checking {service_name}: {e}")
        return False


def get_user_id_from_profile(auth_service_url: str, jwt_token: str) -> Optional[str]:
    """Get the current user's ID (UUID) from GET /auth/users/me. Required for deploy-account."""
    try:
        response = requests.get(
            f"{auth_service_url}/auth/users/me",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        user = data.get("user") if isinstance(data, dict) else None
        if not user or not isinstance(user, dict):
            return None
        user_id = user.get("id")
        return str(user_id).strip() if user_id else None
    except Exception:
        return None


def deploy_user_account(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
) -> dict:
    """
    Deploy an on-chain wallet account for a user (auth service).
    Returns dict with success, new_account_address, message, or error.
    """
    echo_with_color(CYAN, f"  📤 Deploying wallet account for user {user_id}...", file=sys.stderr)
    try:
        response = requests.post(
            f"{auth_service_url}/auth/users/{user_id}/deploy-account",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}",
            },
            timeout=60,
        )
        if not response.text:
            return {"success": False, "error": "Empty response"}
        try:
            data = response.json()
        except Exception:
            return {"success": False, "error": response.text}
        if response.status_code == 200:
            return {
                "success": True,
                "message": data.get("message"),
                "user_id": data.get("user_id"),
                "new_account_address": data.get("new_account_address"),
                "status": data.get("status"),
            }
        return {
            "success": False,
            "error": data.get("error", data.get("message", response.text)),
            "status_code": response.status_code,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(auth_service_url: str, email: str, password: str) -> Optional[str]:
    """Login user and return JWT token."""
    echo_with_color(BLUE, f"  🔐 Logging in user: {email}", file=sys.stderr)
    services_json = ["vault", "payments"]
    payload = {"email": email, "password": password, "services": services_json}
    try:
        response = requests.post(
            f"{auth_service_url}/auth/login/with-services",
            json=payload,
            timeout=30,
        )
        echo_with_color(BLUE, "    📡 Login response received", file=sys.stderr)
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token") or data.get("jwt")
            if token and token != "null":
                echo_with_color(GREEN, "    ✅ Login successful", file=sys.stderr)
                return token
            echo_with_color(RED, "    ❌ No token in response", file=sys.stderr)
            echo_with_color(RED, f"    Response: {response.text}", file=sys.stderr)
            return None
        echo_with_color(RED, f"    ❌ Login failed: HTTP {response.status_code}", file=sys.stderr)
        echo_with_color(RED, f"    Response: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        echo_with_color(RED, f"    ❌ Login failed: {e}", file=sys.stderr)
        return None


def deploy_issuer_account(
    auth_service_url: str,
    issuer_email: str,
    issuer_password: str,
) -> dict:
    """Deploy the on-chain wallet account for the issuer. Logs in, resolves user_id, then deploy-account."""
    echo_with_color(CYAN, "🔐 Deploying issuer account (wallet)...", file=sys.stderr)
    token = login_user(auth_service_url, issuer_email, issuer_password)
    if not token:
        return {"success": False, "error": "Failed to login as issuer"}
    user_id = get_user_id_from_profile(auth_service_url, token)
    if not user_id:
        return {"success": False, "error": "Could not get issuer user_id from /auth/users/me"}
    return deploy_user_account(auth_service_url, token, user_id)
