"""
GraphQL input normalization helpers.

The YAML command files are intentionally ergonomic and use snake_case
keys. Payments GraphQL inputs are camelCase, and some legacy YAML
payment blocks use payer/payee nesting that the schema does not accept
directly. Keep those wire-shape translations here so executors stay
small and consistent.
"""

from copy import deepcopy
from typing import Any, Dict, Optional


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase; pass existing camelCase through."""
    if "_" not in name:
        return name

    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def camelize_keys(value: Any) -> Any:
    """Recursively convert non-private dict keys from snake_case to camelCase."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            wire_key = key if key.startswith("_") else snake_to_camel(key)
            if wire_key not in out:
                out[wire_key] = camelize_keys(item)
        return out
    if isinstance(value, list):
        return [camelize_keys(item) for item in value]
    return value


def compact_optional_fields(value: Any) -> Any:
    """Drop absent optional values from GraphQL input objects."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            compacted = compact_optional_fields(item)
            if compacted is None or compacted == "":
                continue
            if compacted == [] or compacted == {}:
                continue
            out[key] = compacted
        return out
    if isinstance(value, list):
        return [
            item
            for item in (compact_optional_fields(item) for item in value)
            if item is not None and item != "" and item != {} and item != []
        ]
    return value


def normalize_payment(payment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert YAML payment shorthand into VaultPaymentInput.

    `{id: ...}` is a script-local label, not a GraphQL field. When the
    legacy payer/payee shape is present, map it to the flat oracle /
    unlock fields expected by the schema. Already-flat fields are kept.
    """
    original = deepcopy(payment)
    camel = camelize_keys(original)

    payer = original.get("payer") or {}
    payee = original.get("payee") or {}
    owner = original.get("owner") or original.get("oracle_owner")

    has_legacy_shape = bool(payer or payee or owner or "id" in original)
    allowed = {
        "oracleAddress",
        "oracleOwner",
        "oracleKeySender",
        "oracleValueSender",
        "oracleValueSenderSecret",
        "oracleKeyRecipient",
        "oracleValueRecipient",
        "oracleValueRecipientSecret",
        "unlockSender",
        "unlockReceiver",
        "linearVesting",
    }

    if not has_legacy_shape:
        return compact_optional_fields(
            {key: value for key, value in camel.items() if key in allowed}
        )

    return compact_optional_fields({
        "oracleAddress": camel.get("oracleAddress"),
        "oracleOwner": camel.get("oracleOwner", owner),
        "oracleKeySender": str(payer.get("key", camel.get("oracleKeySender", "0"))),
        "oracleValueSender": camel.get("oracleValueSender"),
        "oracleValueSenderSecret": str(
            payer.get(
                "valueSecret",
                payer.get("value_secret", camel.get("oracleValueSenderSecret", "0")),
            )
        ),
        "oracleKeyRecipient": str(payee.get("key", camel.get("oracleKeyRecipient", "0"))),
        "oracleValueRecipient": camel.get("oracleValueRecipient"),
        "oracleValueRecipientSecret": str(
            payee.get(
                "valueSecret",
                payee.get("value_secret", camel.get("oracleValueRecipientSecret", "0")),
            )
        ),
        "unlockSender": payer.get("unlock", camel.get("unlockSender", "")),
        "unlockReceiver": payee.get("unlock", camel.get("unlockReceiver", "")),
        "linearVesting": bool(
            original.get("linear_vesting", camel.get("linearVesting", False))
        ),
    })


def normalize_initial_payments(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize an InitialPaymentsInput-style block for GraphQL variables."""
    if not value:
        return value

    out = camelize_keys(deepcopy(value))
    if "amount" in out and out["amount"] is not None:
        out["amount"] = str(out["amount"])
    payments = out.get("payments")
    if isinstance(payments, list):
        out["payments"] = [
            normalize_payment(payment) if isinstance(payment, dict) else payment
            for payment in payments
        ]
    return compact_optional_fields(out)


def put_if_present(target: Dict[str, Any], key: str, value: Any) -> None:
    """Assign `target[key] = value` only when value is meaningfully present."""
    if value is None:
        return
    if value == [] or value == {}:
        return
    target[key] = value
