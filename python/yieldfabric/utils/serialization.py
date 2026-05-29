"""
JSON-safe value normalization.

PyYAML parses unquoted ISO timestamps into datetime/date objects, but
requests' json encoder cannot serialize those directly. Keep conversion
central so all REST and GraphQL payloads behave the same way.
"""

from datetime import date, datetime, timezone
from typing import Any


def json_safe(value: Any) -> Any:
    """Recursively convert Python values into JSON-serializable values."""
    if isinstance(value, datetime):
        if value.tzinfo is timezone.utc:
            return value.isoformat().replace("+00:00", "Z")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value
