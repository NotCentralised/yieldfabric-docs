#!/usr/bin/env python3
"""
Generate an Ethereum key and register it as an external key for a YieldFabric user.

Uses the same flow as the app's RegisterMetaMaskKeyModal:
  - Generate key (or use existing address + sign with provided key)
  - Sign ownership message (Ethereum personal_sign)
  - Optionally verify ownership, then POST /keys/external

Run from the wisr directory. Requires: pip install eth-account requests

Environment (from .env or env):
  AUTH_SERVICE_URL   - Auth service base URL (default http://localhost:3000)
  USER_EMAIL        - User email to log in as (key will be registered for this user)
  USER_PASSWORD    - User password
  KEY_NAME         - Name for the key (default: "Script-generated external key")
  REGISTER_WITH_WALLET - Set to true/1 to also register key as wallet owner
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Run from wisr directory so modules resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.auth import get_user_id_from_profile, login_user
from modules.console import BLUE, CYAN, GREEN, RED, YELLOW, echo_with_color
from modules.config import load_env_files
from modules.register_external_key import (
    generate_and_register_external_key,
    generate_ethereum_key,
    register_external_key,
    sign_ownership_message,
)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    parser = argparse.ArgumentParser(
        description="Generate an Ethereum key and register it as an external key."
    )
    parser.add_argument(
        "--key-name",
        default=os.environ.get("KEY_NAME", "Script-generated external key"),
        help="Display name for the key",
    )
    parser.add_argument(
        "--register-with-wallet",
        action="store_true",
        default=os.environ.get("REGISTER_WITH_WALLET", "").strip().lower()
        in ("true", "1", "yes"),
        help="Also register this key as an owner of the user's wallet",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip ownership verification (still sign; backend may not require verify)",
    )
    parser.add_argument(
        "--save-key",
        metavar="FILE",
        help="Write private key to FILE (hex, one line). Use with extreme care.",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("USER_EMAIL", os.environ.get("ISSUER_EMAIL", "")),
        help="User email (default: USER_EMAIL or ISSUER_EMAIL)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("USER_PASSWORD", os.environ.get("ISSUER_PASSWORD", "")),
        help="User password",
    )
    args = parser.parse_args()

    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:3000").strip()
    if not args.email or not args.password:
        echo_with_color(RED, "Set USER_EMAIL/USER_PASSWORD (or ISSUER_EMAIL/ISSUER_PASSWORD) or pass --email and --password")
        return 1

    echo_with_color(BLUE, f"  🔐 Logging in as {args.email}...")
    token = login_user(auth_service_url, args.email, args.password)
    if not token:
        echo_with_color(RED, "  ❌ Login failed")
        return 1

    user_id = get_user_id_from_profile(auth_service_url, token)
    if not user_id:
        echo_with_color(RED, "  ❌ Could not get user ID from /auth/users/me")
        return 1
    echo_with_color(GREEN, f"  ✅ User ID: {user_id}")

    echo_with_color(CYAN, "  🔑 Generating key and registering external key...")
    try:
        key_pair, private_key_hex, address = generate_and_register_external_key(
            auth_service_url=auth_service_url,
            jwt_token=token,
            user_id=user_id,
            key_name=args.key_name,
            register_with_wallet=args.register_with_wallet,
            verify_ownership=not args.no_verify,
        )
    except Exception as e:
        echo_with_color(RED, f"  ❌ {e}")
        return 1

    echo_with_color(GREEN, "  ✅ External key registered")
    echo_with_color(CYAN, f"     Key ID:    {key_pair.get('id')}")
    echo_with_color(CYAN, f"     Address:  {address}")
    echo_with_color(CYAN, f"     Key name: {key_pair.get('key_name')}")

    if args.save_key:
        path = Path(args.save_key)
        path.write_text(private_key_hex.strip() + "\n")
        echo_with_color(YELLOW, f"  ⚠️  Private key written to {path} — keep it secret and secure")
    else:
        echo_with_color(YELLOW, "  ⚠️  Private key was generated but not saved. Use --save-key FILE to persist it (keep secure).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
