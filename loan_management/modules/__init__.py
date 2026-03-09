"""
Wisr issue workflow: reusable modules for the composed contract issue workflow.

Use from the CLI via issue_workflow.py, or import for reuse:

  from modules.console import echo_with_color
  from modules.config import load_env_files, parse_bool_env, ACTION_ISSUE_ONLY
  from modules.auth import login_user, deploy_issuer_account
  from modules.payments import issue_composed_contract_workflow, accept_obligation_graphql
  from modules.messages import get_message, wait_for_message_completion, get_messages_awaiting_signature
  from modules.wallet_preferences import set_wallet_execution_mode_preference
  from modules.loan_csv import extract_loan_data, convert_currency_to_wei, convert_date_to_iso
  from modules.cli import parse_cli_args, print_usage
"""

from .console import echo_with_color
from .config import (
    ACTION_ISSUE_ONLY,
    ACTION_ISSUE_SWAP,
    ACTION_ISSUE_SWAP_COMPLETE,
    VALID_ACTION_MODES,
    load_env_files,
    parse_bool_env,
    parse_bool_env_with_mode_default,
)
from .auth import (
    check_service_running,
    deploy_issuer_account,
    deploy_user_account,
    get_user_id_from_profile,
    login_user,
)
from .payments import (
    accept_all_tokens,
    accept_obligation_graphql,
    accept_payment,
    burn_tokens,
    find_obligation_initial_payment,
    find_obligation_initial_payment_from_loan,
    find_obligation_initial_payment_id,
    query_contract_with_payments,
    query_loan_by_id,
    query_payments_by_entity,
    query_payments_by_wallet,
    complete_swap,
    complete_swap_as_wallet,
    create_payment_swap,
    create_wallet_in_payments,
    deposit_tokens,
    get_default_wallet_id,
    get_wallet_by_id,
    get_total_supply,
    instant_send,
    issue_composed_contract_issue_swap_workflow,
    issue_composed_contract_workflow,
    mint_tokens,
    poll_accept_all_until_ready,
    poll_swap_completion,
    poll_workflow_status,
    query_swap_status,
)
from .messages import (
    get_message,
    get_messages_awaiting_signature,
    get_unsigned_transaction,
    poll_until_sign_and_submit_manual_message,
    sign_and_submit_manual_message,
    submit_signed_message,
    wait_for_message_completion,
    wait_for_unsigned_transaction_ready,
)
from .wallet_preferences import (
    get_wallet_execution_mode_preferences,
    set_wallet_execution_mode_preference,
)
from .loan_csv import (
    convert_currency_to_wei,
    convert_date_to_iso,
    extract_loan_data,
    safe_get,
)
from .cli import parse_cli_args, print_usage

__all__ = [
    "echo_with_color",
    "ACTION_ISSUE_ONLY",
    "ACTION_ISSUE_SWAP",
    "ACTION_ISSUE_SWAP_COMPLETE",
    "VALID_ACTION_MODES",
    "load_env_files",
    "parse_bool_env",
    "parse_bool_env_with_mode_default",
    "check_service_running",
    "deploy_issuer_account",
    "deploy_user_account",
    "get_user_id_from_profile",
    "login_user",
    "accept_all_tokens",
    "accept_obligation_graphql",
    "accept_payment",
    "find_obligation_initial_payment",
    "find_obligation_initial_payment_from_loan",
    "find_obligation_initial_payment_id",
    "query_contract_with_payments",
    "query_loan_by_id",
    "query_payments_by_entity",
    "query_payments_by_wallet",
    "burn_tokens",
    "complete_swap",
    "complete_swap_as_wallet",
    "create_payment_swap",
    "create_wallet_in_payments",
    "deposit_tokens",
    "get_default_wallet_id",
    "get_wallet_by_id",
    "get_total_supply",
    "instant_send",
    "issue_composed_contract_issue_swap_workflow",
    "issue_composed_contract_workflow",
    "mint_tokens",
    "poll_accept_all_until_ready",
    "poll_swap_completion",
    "poll_workflow_status",
    "query_swap_status",
    "get_message",
    "get_messages_awaiting_signature",
    "get_unsigned_transaction",
    "poll_until_sign_and_submit_manual_message",
    "sign_and_submit_manual_message",
    "submit_signed_message",
    "wait_for_message_completion",
    "wait_for_unsigned_transaction_ready",
    "get_wallet_execution_mode_preferences",
    "set_wallet_execution_mode_preference",
    "convert_currency_to_wei",
    "convert_date_to_iso",
    "extract_loan_data",
    "safe_get",
    "parse_cli_args",
    "print_usage",
]
