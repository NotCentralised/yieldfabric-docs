"""
Common value-shape checks used across the framework.

Centralises the `if value and value != "null"` sentinel pattern that
showed up in a handful of places — a shell-YAML legacy where string
"null" sometimes leaks through instead of being converted to Python
None. Rather than scatter those checks, use these predicates.
"""

from typing import Any, Optional


# The string sentinels we treat as "not provided" alongside None / "".
# "null" comes from YAML/jq handling, "None" / "NONE" from places that
# stringify None on the way through the shell.
_EMPTY_SENTINELS = frozenset({"null", "None", "NONE"})


def is_provided(value: Any) -> bool:
    """
    True iff `value` is a meaningful user-supplied value — i.e. not
    None, not empty string, not one of the shell-YAML null sentinels.
    """
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        if stripped in _EMPTY_SENTINELS:
            return False
    return True


def coerce_null(value: Any) -> Optional[Any]:
    """
    Return None for any of the sentinel "null-ish" values, passthrough
    otherwise. Handy when mapping YAML-sourced strings to Python fields
    that expect Optional[X].
    """
    return value if is_provided(value) else None
