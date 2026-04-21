"""
Composed-operation executor.

Submits multiple sub-operations as a single atomic GraphQL mutation
(`executeComposedOperations`). The backend sequences them internally
with shared on-chain state; the caller does NOT iterate over the
sub-operations locally — this is a single server-side atomic execution.

YAML shape:

    - name: swap_and_transfer
      type: composed_operation
      user: ...
      parameters:
        idempotency_key: ...
        operations:
          - operation_type: complete_swap
            operation_data: { swap_id: "$some.swap_id", ... }
          - operation_type: transfer_obligation
            operation_data: { contract_id: "...", destination_id: "..." }

Operation-type strings in YAML are snake_case (matching the shell);
the backend enum is PascalCase. We map between the two here.
"""

import json
from typing import Optional

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


# YAML operation_type → backend OperationType enum value.
OPERATION_TYPE_ENUM = {
    "deposit": "Deposit",
    "withdraw": "Withdraw",
    "instant": "InstantSend",
    "instant_send": "InstantSend",
    "create_obligation": "CreateObligation",
    "accept_obligation": "AcceptObligation",
    "transfer_obligation": "TransferObligation",
    "cancel_obligation": "CancelObligation",
    "create_swap": "CreateSwap",
    "complete_swap": "CompleteSwap",
    "cancel_swap": "CancelSwap",
}


def _transform_create_obligation_payments(op_data: dict) -> dict:
    """
    Mirror the shell's transformation at executors_additional.sh:137-170.

    Single-operation `create_obligation` accepts the ergonomic
    `{payer, payee}` payment shape. Composed operations go through
    MQ/serde, which expects flat `VaultPayment` fields. If this operation
    uses the ergonomic shape, flatten it; otherwise leave alone.
    """
    initial_payments = op_data.get("initial_payments")
    if not isinstance(initial_payments, dict):
        return op_data
    payments = initial_payments.get("payments")
    if not isinstance(payments, list) or not payments:
        return op_data
    # Detect ergonomic shape by presence of nested payer/payee in the first entry.
    first = payments[0]
    if not isinstance(first, dict) or "payer" not in first:
        return op_data

    def _flatten(p: dict) -> dict:
        payer = p.get("payer") or {}
        payee = p.get("payee") or {}
        return {
            "oracle_address": p.get("oracle_address"),
            "oracle_owner": p.get("owner"),
            "oracle_key_sender": payer.get("key", "0"),
            "oracle_value_sender_secret": payer.get("valueSecret", "0"),
            "oracle_key_recipient": payee.get("key", "0"),
            "oracle_value_recipient_secret": payee.get("valueSecret", "0"),
            "unlock_sender": payer.get("unlock"),
            "unlock_receiver": payee.get("unlock"),
            "linear_vesting": p.get("linear_vesting", False),
        }

    out = dict(op_data)
    out["initial_payments"] = dict(initial_payments)
    out["initial_payments"]["payments"] = [_flatten(p) for p in payments]
    return out


class ComposedExecutor(BaseExecutor):
    """Executor for `composed_operation` — single atomic multi-op mutation."""

    def execute(self, command: Command) -> CommandResponse:
        if command.type.lower() != "composed_operation":
            return CommandResponse.error_response(
                command.name, command.type,
                [f"ComposedExecutor only handles composed_operation, got {command.type}"]
            )

        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        operations = params.get("operations")
        if not isinstance(operations, list) or not operations:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["composed_operation requires a non-empty `operations` list"]
            )

        # Build backend-shaped operation list. Each entry is
        # {operationType: <Enum>, operationData: "<json-string>"}.
        backend_ops = []
        for i, op in enumerate(operations):
            op_type = op.get("operation_type")
            op_data = op.get("operation_data") or {}
            enum_value = OPERATION_TYPE_ENUM.get(op_type)
            if not enum_value:
                self.log_command_failure(command)
                return CommandResponse.error_response(
                    command.name, command.type,
                    [f"operation[{i}]: unknown operation_type {op_type!r}"]
                )

            # Per-op-type pre-transforms (mirrors shell behaviour).
            if op_type == "create_obligation":
                op_data = _transform_create_obligation_payments(op_data)

            backend_ops.append({
                "operationType": enum_value,
                "operationData": json.dumps(op_data),
            })

        self.log_parameters({
            "operation_count": len(backend_ops),
            "idempotency_key": params.idempotency_key,
        })

        variables = {"input": {"operations": backend_ops}}
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key

        response = self.payments_service.graphql_mutation(
            GraphQLMutation.EXECUTE_COMPOSED_OPERATIONS, variables, token
        )
        if not response.success:
            return self._finalize_graphql_error(
                command, response, operation_name="composed_operation"
            )

        data = response.get_data("executeComposedOperations", {})
        if not data.get("success"):
            return self._finalize_business_error(
                command,
                data.get("message", "composed_operation not successful"),
                operation_name="composed_operation",
            )

        outputs = {
            "message": data.get("message"),
            "message_id": data.get("messageId"),
            "composed_id": data.get("composedId"),
            "account_address": data.get("accountAddress"),
            "operation_count": data.get("operationCount"),
        }

        # Surface per-sub-operation results so downstream commands can
        # reference them via `$name[index].field` — e.g. if op 0 is a
        # create_swap, its swap_id will be at `$composed_cmd[0].swap_id`.
        # Matches the shell's composed-op chaining syntax.
        for idx, sub in enumerate(data.get("operationResults") or []):
            if not isinstance(sub, dict):
                continue
            for k, v in sub.items():
                if v is None:
                    continue
                self.output_store.store(command.name, f"[{idx}].{_snake(k)}", v)

        return self._finalize_success(
            command, token, outputs,
            success_message=f"composed_operation ok: {outputs['operation_count']} ops executed",
        )


def _snake(name: str) -> str:
    """camelCase → snake_case (simple, handles GraphQL field names)."""
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
