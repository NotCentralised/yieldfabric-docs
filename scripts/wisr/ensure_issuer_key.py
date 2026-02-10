#!/usr/bin/env python3
"""
Ensure the issuer has an external key: create and save to a file on first run, register to issuer account.

Flow:
  - If the key file does not exist: generate a new private key, save it to a .txt file, and register
    it as an external key for the issuer user (first time).
  - If the key file exists: load the key and report the address; no registration (key already exists).

Environment (from .env or env):
  AUTH_SERVICE_URL         - Auth service base URL (default http://localhost:3000)
  ISSUER_EMAIL            - Issuer user email
  ISSUER_PASSWORD         - Issuer password
  ISSUER_EXTERNAL_KEY_FILE - Path to the private key file (default: ./issuer_external_key.txt)
  ISSUER_EXTERNAL_KEY_NAME - Display name for the key (default: "Issuer script external key")
  REGISTER_WITH_WALLET    - Set true/1 to also register key as wallet owner when creating

Run from the wisr directory. Requires: pip install eth-account requests
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.auth import get_user_id_from_profile, login_user
from modules.console import BLUE, CYAN, GREEN, RED, YELLOW, echo_with_color
from modules.config import load_env_files
from modules.register_external_key import ensure_issuer_external_key


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:3000").strip()
    issuer_email = os.environ.get("ISSUER_EMAIL", "").strip()
    issuer_password = os.environ.get("ISSUER_PASSWORD", "").strip()
    key_file = os.environ.get("ISSUER_EXTERNAL_KEY_FILE", "").strip() or str(script_dir / "issuer_external_key.txt")
    key_name = os.environ.get("ISSUER_EXTERNAL_KEY_NAME", "Issuer script external key").strip()
    register_with_wallet = os.environ.get("REGISTER_WITH_WALLET", "").strip().lower() in ("true", "1", "yes")

    if not issuer_email or not issuer_password:
        echo_with_color(RED, "Set ISSUER_EMAIL and ISSUER_PASSWORD (e.g. in .env)")
        return 1

    echo_with_color(BLUE, f"  🔐 Logging in as issuer: {issuer_email}")
    jwt_token = login_user(auth_service_url, issuer_email, issuer_password)
    if not jwt_token:
        echo_with_color(RED, "  ❌ Issuer login failed")
        return 1

    user_id = get_user_id_from_profile(auth_service_url, jwt_token)
    if not user_id:
        echo_with_color(RED, "  ❌ Could not get issuer user ID from /auth/users/me")
        return 1

    key_path = Path(key_file)
    if not key_path.is_absolute():
        key_path = (script_dir / key_path).resolve()

    echo_with_color(CYAN, f"  📁 Key file: {key_path}")
    if key_path.exists():
        echo_with_color(BLUE, "  Key file already exists; loading (no registration).")
    else:
        echo_with_color(BLUE, "  Key file not found; creating key and registering to issuer account.")

    try:
        address, private_key_hex, key_pair, key_id = ensure_issuer_external_key(
            auth_service_url=auth_service_url,
            jwt_token=jwt_token,
            user_id=user_id,
            key_file_path=key_path,
            key_name=key_name,
            register_with_wallet=register_with_wallet,
            verify_ownership=True,
        )
    except Exception as e:
        echo_with_color(RED, f"  ❌ {e}")
        return 1

    echo_with_color(GREEN, f"  ✅ Issuer external key address: {address}")
    if key_pair is not None:
        echo_with_color(GREEN, f"  ✅ Key registered (first time). Key ID: {key_pair.get('id')}")
        echo_with_color(YELLOW, f"  ⚠️  Private key saved to: {key_path} — keep it secret.")
    else:
        echo_with_color(CYAN, "  (Key was already present; no registration performed.)")
    if key_id:
        echo_with_color(BLUE, f"  Key ID (for registering with loan wallets): {key_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
