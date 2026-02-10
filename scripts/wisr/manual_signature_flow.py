#!/usr/bin/env python3
"""
Manual signature flow helpers: set wallet to Manual (so messages require app signing), poll for completion.

Usage:
  # Set a wallet to require manual signature for AcceptObligation (then trigger accept from Python; user signs in app)
  ./run.sh manual_signature_flow.py set-manual --wallet-id WLT-LOAN-<entity>-<loan> --message-type AcceptObligation

  # Poll until a message is completed (after user has signed in the app)
  ./run.sh manual_signature_flow.py wait --message-id <uuid> [--user-id <user_id>]

Environment: AUTH_SERVICE_URL, PAY_SERVICE_URL, ISSUER_EMAIL, ISSUER_PASSWORD (or USER_EMAIL, USER_PASSWORD).
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.auth import get_user_id_from_profile, login_user
from modules.console import BLUE, CYAN, GREEN, RED, echo_with_color
from modules.config import load_env_files
from modules.messages import get_message, get_messages_awaiting_signature, wait_for_message_completion
from modules.wallet_preferences import get_wallet_execution_mode_preferences, set_wallet_execution_mode_preference


def cmd_set_manual(
    pay_service_url: str,
    jwt_token: str,
    wallet_id: str,
    message_type: str,
) -> int:
    set_wallet_execution_mode_preference(
        pay_service_url, jwt_token, wallet_id, message_type, "Manual"
    )
    echo_with_color(GREEN, f"  ✅ Wallet {wallet_id} set to Manual for {message_type}")
    return 0


def cmd_wait(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    message_id: str,
    poll_interval: float,
    max_wait: float,
) -> int:
    echo_with_color(CYAN, f"  ⏳ Polling message {message_id} (max {max_wait}s)...")
    result = wait_for_message_completion(
        pay_service_url, jwt_token, user_id, message_id,
        poll_interval_seconds=poll_interval,
        max_wait_seconds=max_wait,
    )
    if result.get("executed"):
        echo_with_color(GREEN, "  ✅ Message completed")
        return 0
    echo_with_color(RED, f"  ❌ {result.get('error', 'Unknown')}")
    return 1


def cmd_list_awaiting(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
) -> int:
    messages = get_messages_awaiting_signature(pay_service_url, jwt_token, user_id)
    echo_with_color(CYAN, f"  📋 Messages awaiting signature: {len(messages)}")
    for m in messages:
        mid = m.get("id", "?")
        mtype = m.get("data", {}).get("message_type", "?")
        echo_with_color(BLUE, f"    {mid}  {mtype}")
    return 0


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    pay_service_url = os.environ.get("PAY_SERVICE_URL", "http://localhost:3002").strip()
    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:3000").strip()
    email = os.environ.get("USER_EMAIL", os.environ.get("ISSUER_EMAIL", "")).strip()
    password = os.environ.get("USER_PASSWORD", os.environ.get("ISSUER_PASSWORD", "")).strip()

    parser = argparse.ArgumentParser(description="Manual signature flow: set Manual, poll, or list awaiting")
    sub = parser.add_subparsers(dest="command", required=True)
    # set-manual
    p_set = sub.add_parser("set-manual", help="Set wallet execution mode to Manual for a message type")
    p_set.add_argument("--wallet-id", required=True, help="Wallet ID (e.g. WLT-LOAN-entity-loan)")
    p_set.add_argument("--message-type", required=True, help="e.g. AcceptObligation, Retrieve")
    # wait
    p_wait = sub.add_parser("wait", help="Poll until message is completed")
    p_wait.add_argument("--message-id", required=True, help="Message UUID")
    p_wait.add_argument("--user-id", default="", help="User ID (default: from /auth/users/me)")
    p_wait.add_argument("--poll-interval", type=float, default=2.0)
    p_wait.add_argument("--max-wait", type=float, default=300.0)
    # list-awaiting
    p_list = sub.add_parser("list-awaiting", help="List messages awaiting signature")
    p_list.add_argument("--user-id", default="", help="User ID (default: from /auth/users/me)")
    args = parser.parse_args()

    if not email or not password:
        echo_with_color(RED, "Set USER_EMAIL/USER_PASSWORD or ISSUER_EMAIL/ISSUER_PASSWORD")
        return 1

    echo_with_color(BLUE, f"  🔐 Logging in as {email}...")
    jwt_token = login_user(auth_service_url, email, password)
    if not jwt_token:
        echo_with_color(RED, "  ❌ Login failed")
        return 1
    user_id = args.user_id if args.user_id else get_user_id_from_profile(auth_service_url, jwt_token)
    if not user_id and args.command in ("wait", "list-awaiting"):
        echo_with_color(RED, "  ❌ Could not get user_id (set --user-id or ensure /auth/users/me returns id)")
        return 1

    if args.command == "set-manual":
        return cmd_set_manual(pay_service_url, jwt_token, args.wallet_id, args.message_type)
    if args.command == "wait":
        return cmd_wait(
            pay_service_url, jwt_token, user_id, args.message_id,
            args.poll_interval, args.max_wait,
        )
    if args.command == "list-awaiting":
        return cmd_list_awaiting(pay_service_url, jwt_token, user_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
