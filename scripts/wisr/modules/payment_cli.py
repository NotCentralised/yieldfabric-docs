"""CLI: help text and argument parsing for the payment workflow script."""

import os
import sys
from pathlib import Path


def print_payment_usage() -> None:
    """Print help text for the payment workflow script."""
    print("Usage: payment_workflow.py [csv_file]")
    print()
    print("Arguments:")
    print("  csv_file   Path to payment CSV (default: wisr_payment_test.csv)")
    print()
    print("CSV columns (header): MAMBU_LOANID, MAMBU_PAYMENTDATE, MAMBU_TRANSACTION,")
    print("  DWH_PRINCIPAL, DWH_INTEREST, DWH_FEE, MAMBU_TOTAL_AMOUNT, MAMBU_ISDISHONOURED")
    print()
    print("Environment variables:")
    print("  ACCEPTOR_EMAIL       Entity that finds, accepts the payment, and creates the swap")
    print("  ACCEPTOR_PASSWORD    Password for ACCEPTOR_EMAIL")
    print("  ISSUER_EMAIL         Entity that owns loan wallets; required to complete swap as loan account.")
    print("  ISSUER_PASSWORD      Password for ISSUER_EMAIL (required for step 4).")
    print("  DENOMINATION         Asset ID for the swap (default: aud-token-asset)")
    print("  SWAP_DEADLINE        Optional; ISO deadline for the swap (default: 30 days from now)")
    print("  ACCEPT_ALL_POLL_INTERVAL_SEC  Poll interval for accept_all (default: 2)")
    print("  ACCEPT_ALL_TIMEOUT_SEC  Timeout for accept_all polling per party (default: 90)")
    print("  PAY_SERVICE_URL      Payments service URL")
    print("  AUTH_SERVICE_URL     Auth service URL")
    print("  PAYMENT_COUNT        Max rows to process (default: 100)")
    print()
    print("Flow per row:")
    print("  1) Find obligation initial payment for the loan (acceptor's contracts → contract → payments)")
    print("  2) Accept that payment for the CSV amount (DWH_PRINCIPAL) only, not the fill amount")
    print("  3) Create payment swap: credit DWH_PRINCIPAL (obligor=loan) vs cash MAMBU_TOTAL_AMOUNT (obligor=null), counterparty=loan account")
    print("  4) Loan account completes the swap (requires ISSUER_EMAIL + ISSUER_PASSWORD)")
    print("  5) Accept all payables by acceptor and by loan account")
    print()
    print("Example:")
    print("  python3 payment_workflow.py wisr_payment_test.csv")
    print("  ACCEPTOR_EMAIL=issuer@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 payment_workflow.py")


def parse_payment_cli_args(script_dir: Path) -> str:
    """Parse argv and env into csv_file path."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        csv_file = os.environ.get("PAYMENT_CSV", "").strip() or str(script_dir / "wisr_payment_test.csv")
        return csv_file
    csv_file = args[0]
    csv_path = Path(csv_file)
    if not csv_path.is_absolute() and (script_dir / csv_path).exists():
        csv_file = str(script_dir / csv_path)
    elif not csv_path.is_absolute() and csv_path.exists():
        csv_file = str(csv_path.resolve())
    return csv_file
