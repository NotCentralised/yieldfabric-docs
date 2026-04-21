"""
JWT claim extraction (no signature verification).

Used internally to resolve `sub` / `acting_as` when we need to name the
entity that owns an MQ message. We NEVER re-verify the signature here
— the backend already did that when it issued the token; we just need
to read the payload.

Before this module existed, three different files re-implemented the
same base64-decode + JSON-parse + `payload.get("sub")` dance. Keep the
single source of truth here.
"""

import base64
import json
from typing import Any, Optional


def extract_claim(token: str, *claim_names: str) -> Optional[Any]:
    """
    Return the first non-empty claim found in `claim_names`, in order.

    Silent on failure: returns None for malformed tokens, base64/JSON
    decode errors, or missing claims. Callers who need stricter handling
    should check the return value and error themselves.

    Example:
        # prefer acting_as (delegation), fall back to sub
        entity_id = extract_claim(jwt, "acting_as", "sub")
    """
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for name in claim_names:
        value = payload.get(name)
        if value:  # skip None / empty string / 0
            return value
    return None


def get_entity_id(token: str) -> Optional[str]:
    """
    MQ-message entity_id: `acting_as` if delegating, else `sub`.

    This is what the `/api/users/{entity_id}/messages/{id}` endpoint
    expects — for group-delegated operations the message is owned by
    the group, not the acting user.
    """
    value = extract_claim(token, "acting_as", "sub")
    return value if isinstance(value, str) else None


def get_sub(token: str) -> Optional[str]:
    """
    Strictly the `sub` claim — the user's UUID. Use when you need
    the user (not the group) regardless of delegation context.
    """
    value = extract_claim(token, "sub")
    return value if isinstance(value, str) else None
