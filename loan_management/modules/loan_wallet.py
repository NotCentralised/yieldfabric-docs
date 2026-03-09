"""
Loan wallet naming convention: WLT-LOAN-{entity_id}-{loan_id}.
Shared by issue_workflow and payment_workflow so the convention lives in one place.
"""

import re


def sanitize_loan_id(loan_id: str) -> str:
    """Normalize loan id for use in wallet id (alphanumeric and hyphens only)."""
    return re.sub(r"[^a-zA-Z0-9-]", "-", str(loan_id)).strip("-") or "loan"


def loan_wallet_id(entity_id_raw: str, loan_id: str) -> str:
    """Return the standard loan wallet id for this entity and loan."""
    return f"WLT-LOAN-{entity_id_raw}-{sanitize_loan_id(loan_id)}"
