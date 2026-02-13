#!/usr/bin/env python3
"""
Manual signature flow: set Manual, list awaiting, sign with Python key, submit, or poll for completion.

Usage:
  # Set wallet to Manual (message then requires signing)
  ./run.sh manual_signature_flow.py set-manual --wallet-id WLT-LOAN-<entity>-<loan> --message-type AcceptObligation

  # Sign and submit using the issuer private key (Python signs; no app needed)
  ./run.sh manual_signature_flow.py sign-and-submit --message-id <uuid> [--key-file issuer_external_key.txt]

  # Concurrent listener: poll for messages awaiting signature and sign them with the private key
  ./run.sh manual_signature_flow.py listen [--key-file issuer_external_key.txt] [--poll-interval 5]

  # Poll until a message is completed
  ./run.sh manual_signature_flow.py wait --message-id <uuid> [--user-id <user_id>]

  # List messages awaiting signature
  ./run.sh manual_signature_flow.py list-awaiting

Environment: AUTH_SERVICE_URL, PAY_SERVICE_URL, ISSUER_EMAIL, ISSUER_PASSWORD (or USER_EMAIL, USER_PASSWORD).
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.auth import get_user_id_from_profile, login_user
from modules.console import BLUE, CYAN, GREEN, RED, echo_with_color
from modules.config import load_env_files
from modules.messages import (
    get_messages_awaiting_signature,
    sign_and_submit_manual_message,
    wait_for_message_completion,
)
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


def cmd_listen(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    key_file: Path,
    poll_interval: float,
    once: bool,
    max_workers: int,
) -> int:
    """Concurrently poll for messages awaiting signature and sign them with the private key."""
    if not key_file.exists():
        echo_with_color(RED, f"  ❌ Key file not found: {key_file}")
        return 1
    private_key_hex = key_file.read_text().strip().removeprefix("0x").strip()
    if not private_key_hex:
        echo_with_color(RED, "  ❌ Key file is empty")
        return 1

    echo_with_color(CYAN, f"  🎧 Listening for messages awaiting signature (key: {key_file.name}, poll every {poll_interval}s). Ctrl+C to stop.")
    signed_ids: set[str] = set()
    cycle = 0

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                cycle += 1
                try:
                    messages = get_messages_awaiting_signature(pay_service_url, jwt_token, user_id)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ List awaiting failed: {e}")
                    if once:
                        return 1
                    time.sleep(poll_interval)
                    continue

                new_messages = [m for m in messages if m.get("id") and m["id"] not in signed_ids]
                if new_messages:
                    echo_with_color(BLUE, f"  📬 Cycle {cycle}: {len(new_messages)} new message(s) awaiting signature")
                    futures = {}
                    for m in new_messages:
                        mid = m["id"]
                        signed_ids.add(mid)
                        fut = executor.submit(
                            sign_and_submit_manual_message,
                            pay_service_url,
                            jwt_token,
                            user_id,
                            mid,
                            private_key_hex,
                        )
                        futures[fut] = mid

                    for fut in as_completed(futures):
                        mid = futures[fut]
                        try:
                            result = fut.result()
                            echo_with_color(GREEN, f"  ✅ Signed and submitted message {mid}: {result.get('message', result)}")
                        except Exception as e:
                            echo_with_color(RED, f"  ❌ Failed to sign message {mid}: {e}")
                            signed_ids.discard(mid)  # allow retry next cycle

                if once:
                    break
                time.sleep(poll_interval)
    except KeyboardInterrupt:
        echo_with_color(CYAN, "\n  👋 Listener stopped.")
        return 0

    return 0


def cmd_sign_and_submit(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    message_id: str,
    key_file: Path,
) -> int:
    if not key_file.exists():
        echo_with_color(RED, f"  ❌ Key file not found: {key_file}")
        return 1
    private_key_hex = key_file.read_text().strip().removeprefix("0x").strip()
    if not private_key_hex:
        echo_with_color(RED, "  ❌ Key file is empty")
        return 1
    echo_with_color(CYAN, f"  🔑 Signing message {message_id} with key from {key_file.name}...")
    try:
        result = sign_and_submit_manual_message(
            pay_service_url, jwt_token, user_id, message_id, private_key_hex
        )
        echo_with_color(GREEN, f"  ✅ Signature submitted: {result.get('message', result)}")
        return 0
    except Exception as e:
        echo_with_color(RED, f"  ❌ {e}")
        return 1


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
    # listen
    p_listen = sub.add_parser(
        "listen",
        help="Concurrently poll for messages awaiting signature and sign them with the private key",
    )
    p_listen.add_argument(
        "--key-file",
        default="",
        help="Path to file with private key hex (default: issuer_external_key.txt in script dir)",
    )
    p_listen.add_argument("--user-id", default="", help="User ID (default: from /auth/users/me)")
    p_listen.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between polls (default: 5)",
    )
    p_listen.add_argument(
        "--once",
        action="store_true",
        help="Run one poll cycle and exit (default: run until Ctrl+C)",
    )
    p_listen.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Max concurrent sign-and-submit tasks (default: 4)",
    )
    # sign-and-submit
    p_sign = sub.add_parser(
        "sign-and-submit",
        help="Get unsigned tx, sign with private key from file, submit signature (Python signs)",
    )
    p_sign.add_argument("--message-id", required=True, help="Message UUID")
    p_sign.add_argument(
        "--key-file",
        default="",
        help="Path to file with private key hex (default: issuer_external_key.txt in script dir)",
    )
    p_sign.add_argument("--user-id", default="", help="User ID (default: from /auth/users/me)")
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
    if not user_id and args.command in ("wait", "list-awaiting", "sign-and-submit", "listen"):
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
    if args.command == "listen":
        key_file = Path(args.key_file) if args.key_file else (script_dir / "issuer_external_key.txt")
        if not key_file.is_absolute():
            key_file = (script_dir / key_file).resolve()
        return cmd_listen(
            pay_service_url,
            jwt_token,
            user_id,
            key_file,
            args.poll_interval,
            args.once,
            args.max_workers,
        )
    if args.command == "sign-and-submit":
        key_file = Path(args.key_file) if args.key_file else (script_dir / "issuer_external_key.txt")
        if not key_file.is_absolute():
            key_file = (script_dir / key_file).resolve()
        return cmd_sign_and_submit(
            pay_service_url, jwt_token, user_id, args.message_id, key_file
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
