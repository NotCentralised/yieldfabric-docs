"""
Shared workflow helpers: summary, preflight, banner.
Keeps issue_workflow and payment_workflow DRY.
"""

from typing import Optional

from .console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW, echo_with_color
from .auth import check_service_running


BANNER_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def print_workflow_summary(
    total: int,
    success_count: int,
    fail_count: int,
    *,
    total_label: str = "Total processed",
    success_label: str = "Successful",
    fail_label: str = "Failed",
    success_message: Optional[str] = None,
    failure_message: Optional[str] = None,
) -> None:
    """Print the standard workflow summary block (banner, counts, optional success/failure messages)."""
    print()
    echo_with_color(PURPLE, BANNER_LINE)
    echo_with_color(CYAN, "📊 Summary")
    echo_with_color(PURPLE, BANNER_LINE)
    echo_with_color(BLUE, f"  {total_label}: {total}")
    echo_with_color(GREEN, f"  {success_label}: {success_count}")
    echo_with_color(RED, f"  {fail_label}: {fail_count}")
    print()
    if success_count > 0 and success_message:
        echo_with_color(GREEN, success_message)
    if success_count == 0 and failure_message:
        echo_with_color(RED, failure_message)


def run_preflight_checks(
    auth_service_url: str,
    pay_service_url: str,
    *,
    pay_extra_lines: Optional[list[tuple[str, str]]] = None,
) -> bool:
    """
    Check auth and payments services are reachable.
    Prints error messages and returns False if any check fails.
    pay_extra_lines: optional list of (color, message) to print after pay service unreachable (e.g. hint to start server).
    """
    if not check_service_running("Auth Service", auth_service_url):
        echo_with_color(RED, f"❌ Auth service is not reachable at {auth_service_url}")
        return False
    if not check_service_running("Payments Service", pay_service_url):
        echo_with_color(RED, f"❌ Payments service is not reachable at {pay_service_url}")
        if pay_extra_lines:
            for color, msg in pay_extra_lines:
                echo_with_color(color, msg)
        return False
    return True
