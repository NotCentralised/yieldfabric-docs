"""
Swap operations executor — create/complete/cancel across the three
swap flavours (unified `create_swap`, legacy `create_obligation_swap`,
legacy `create_payment_swap`), plus `complete_swap` and `cancel_swap`.

The three create-variants hit the same backend shape
(counterparty + optional initiator/counterparty detail blocks) so
share `_execute_create_swap_variant`.
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


# Per-swap-variant metadata: (mutation, response_root, op_name).
_SWAP_VARIANTS = {
    "create_swap": (GraphQLMutation.CREATE_SWAP, "createSwap", "Create swap"),
    "create_obligation_swap": (
        GraphQLMutation.CREATE_OBLIGATION_SWAP,
        "createObligationSwap",
        "Create obligation swap",
    ),
    "create_payment_swap": (
        GraphQLMutation.CREATE_PAYMENT_SWAP,
        "createPaymentSwap",
        "Create payment swap",
    ),
}


class SwapExecutor(BaseExecutor):
    """Executor for swap operations."""

    def execute(self, command: Command) -> CommandResponse:
        command_type = command.type.lower()
        if command_type in _SWAP_VARIANTS:
            return self._execute_create_swap_variant(command, command_type)
        if command_type == "complete_swap":
            return self._execute_terminal_swap(
                command,
                mutation=GraphQLMutation.COMPLETE_SWAP,
                response_root="completeSwap",
                operation_name="Complete swap",
                result_field="completeResult",
                output_key="complete_result",
            )
        if command_type == "cancel_swap":
            return self._execute_terminal_swap(
                command,
                mutation=GraphQLMutation.CANCEL_SWAP,
                response_root="cancelSwap",
                operation_name="Cancel swap",
                result_field="cancelResult",
                output_key="cancel_result",
            )
        return CommandResponse.error_response(
            command.name, command.type,
            [f"Unknown swap command type: {command_type}"]
        )

    # ------------------------------------------------------------------

    def _execute_create_swap_variant(
        self, command: Command, command_type: str
    ) -> CommandResponse:
        """Shared create-{swap,obligation_swap,payment_swap} implementation."""
        mutation, response_root, operation_name = _SWAP_VARIANTS[command_type]

        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        input_obj = {"counterparty": params.counterpart}
        if params.initiator:
            input_obj["initiator"] = params.initiator
        if params.counterparty:
            input_obj["counterparty"] = params.counterparty
        if params.idempotency_key:
            input_obj["idempotencyKey"] = params.idempotency_key

        response = self.payments_service.graphql_mutation(
            mutation, {"input": input_obj}, token
        )
        if not response.success:
            return self._finalize_graphql_error(
                command, response, operation_name=operation_name
            )

        data = response.get_data(response_root, {})
        if not data.get("success"):
            return self._finalize_business_error(
                command,
                data.get("message", f"{operation_name} not successful"),
                operation_name=operation_name,
            )

        outputs = {
            "swap_id": data.get("swapId"),
            "account_address": data.get("accountAddress"),
            "counterparty_address": data.get("counterpartyAddress"),
            "message": data.get("message"),
            "swap_result": data.get("swapResult"),
            "message_id": data.get("messageId"),
            "timestamp": data.get("timestamp"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"{operation_name} successful! swap_id={outputs.get('swap_id')}",
        )

    def _execute_terminal_swap(
        self,
        command: Command,
        *,
        mutation: str,
        response_root: str,
        operation_name: str,
        result_field: str,
        output_key: str,
    ) -> CommandResponse:
        """
        Shared implementation for `complete_swap` and `cancel_swap` —
        both take just `{swapId, idempotencyKey?}` and return a uniform
        result shape, differing only in the result-field name.
        """
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        variables = {"input": {"swapId": params.swap_id}}
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key

        response = self.payments_service.graphql_mutation(mutation, variables, token)
        if not response.success:
            return self._finalize_graphql_error(
                command, response, operation_name=operation_name
            )

        data = response.get_data(response_root, {})
        if not data.get("success"):
            return self._finalize_business_error(
                command,
                data.get("message", f"{operation_name} not successful"),
                operation_name=operation_name,
            )

        outputs = {
            "swap_id": data.get("swapId"),
            "account_address": data.get("accountAddress"),
            "message": data.get("message"),
            output_key: data.get(result_field),
            "message_id": data.get("messageId"),
            "timestamp": data.get("timestamp"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"{operation_name} successful!",
        )
