"""
Swap operations executor — create/complete/cancel across the three
swap flavours (unified `create_swap`, legacy `create_obligation_swap`,
legacy `create_payment_swap`), plus `complete_swap` and `cancel_swap`.

The three create-variants hit the same backend shape
(counterparty + optional initiator/counterparty detail blocks) so
share `_execute_create_swap_variant`.
"""

from typing import Optional

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation
from ..utils.graphql_input import (
    camelize_keys,
    normalize_initial_payments,
    put_if_present,
)


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
        input_obj = self._build_create_swap_input(params)
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

        counterparty = data.get("counterparty")
        outputs = {
            "swap_id": data.get("swapId"),
            "account_address": data.get("accountAddress"),
            "counterparty": counterparty,
            "counterparty_address": counterparty,
            "message": data.get("message"),
            "swap_result": data.get("swapResult"),
            "message_id": data.get("messageId"),
            "transaction_id": data.get("transactionId"),
            "signature": data.get("signature"),
            "timestamp": data.get("timestamp"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"{operation_name} successful! swap_id={outputs.get('swap_id')}",
        )

    def _build_create_swap_input(self, params) -> dict:
        """
        Convert the YAML-friendly swap shape to CreateSwapInput.

        YAML commands commonly use nested blocks:

            initiator:
              obligation_ids: [...]
            counterparty:
              id: someone@example.com
              expected_payments: {...}

        Payments GraphQL expects flat camelCase fields. This mirrors
        the shell runner's flattening logic while preserving callers
        that already provide the flat schema shape.
        """
        input_obj = {}
        put_if_present(input_obj, "swapId", params.swap_id or params.get("swapId"))

        counterparty = params.counterpart
        if isinstance(params.counterparty, dict):
            counterparty = params.counterparty.get("id") or counterparty
        elif params.counterparty:
            counterparty = params.counterparty
        put_if_present(input_obj, "counterparty", counterparty)

        put_if_present(input_obj, "deadline", params.get("deadline"))
        put_if_present(input_obj, "expiry", params.get("expiry"))
        put_if_present(input_obj, "walletId", params.get("wallet_id"))
        put_if_present(input_obj, "counterpartyWalletId", params.get("counterparty_wallet_id"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        put_if_present(input_obj, "name", params.get("name"))
        put_if_present(input_obj, "auctionBid", camelize_keys(params.get("auction_bid")))

        self._flatten_swap_side(input_obj, "initiator", params.initiator)
        counterparty_block = params.counterparty if isinstance(params.counterparty, dict) else None
        self._flatten_swap_side(input_obj, "counterparty", counterparty_block)

        # Also support callers that provide the canonical flat shape in
        # snake_case at top level.
        flat_fields = {
            "initiator_obligation_ids": "initiatorObligationIds",
            "initiator_contract_references": "initiatorContractReferences",
            "initiator_expected_payments": "initiatorExpectedPayments",
            "counterparty_obligation_ids": "counterpartyObligationIds",
            "counterparty_contract_references": "counterpartyContractReferences",
            "counterparty_expected_payments": "counterpartyExpectedPayments",
            "initiator_collateral_obligation_ids": "initiatorCollateralObligationIds",
            "initiator_collateral_contract_references": "initiatorCollateralContractReferences",
            "initiator_collateral_payments": "initiatorCollateralPayments",
            "counterparty_collateral_obligation_ids": "counterpartyCollateralObligationIds",
            "counterparty_collateral_contract_references": "counterpartyCollateralContractReferences",
            "counterparty_collateral_payments": "counterpartyCollateralPayments",
            "initiator_repurchase_obligation_ids": "initiatorRepurchaseObligationIds",
            "initiator_repurchase_contract_references": "initiatorRepurchaseContractReferences",
            "initiator_repurchase_payments": "initiatorRepurchasePayments",
            "counterparty_repurchase_obligation_ids": "counterpartyRepurchaseObligationIds",
            "counterparty_repurchase_contract_references": "counterpartyRepurchaseContractReferences",
            "counterparty_repurchase_payments": "counterpartyRepurchasePayments",
        }
        payment_fields = {
            "initiator_expected_payments",
            "counterparty_expected_payments",
            "initiator_collateral_payments",
            "counterparty_collateral_payments",
            "initiator_repurchase_payments",
            "counterparty_repurchase_payments",
        }
        for source, target in flat_fields.items():
            value = params.get(source)
            if source in payment_fields:
                value = normalize_initial_payments(value)
            else:
                value = camelize_keys(value)
            put_if_present(input_obj, target, value)

        return input_obj

    def _flatten_swap_side(self, input_obj: dict, side: str, block) -> None:
        """Flatten one nested `initiator` or `counterparty` swap block."""
        if not isinstance(block, dict):
            return

        prefix = side
        title_prefix = "initiator" if prefix == "initiator" else "counterparty"
        title_prefix = title_prefix[0].lower() + title_prefix[1:]

        field_map = {
            "obligation_ids": f"{title_prefix}ObligationIds",
            "contract_references": f"{title_prefix}ContractReferences",
            "collateral_obligation_ids": f"{title_prefix}CollateralObligationIds",
            "collateral_contract_references": f"{title_prefix}CollateralContractReferences",
            "collateral_payments": f"{title_prefix}CollateralPayments",
            "repurchase_obligation_ids": f"{title_prefix}RepurchaseObligationIds",
            "repurchase_contract_references": f"{title_prefix}RepurchaseContractReferences",
            "repurchase_payments": f"{title_prefix}RepurchasePayments",
        }

        for source, target in field_map.items():
            value = block.get(source)
            if source.endswith("_payments"):
                value = normalize_initial_payments(value)
            else:
                value = camelize_keys(value)
            put_if_present(input_obj, target, value)

        payments = block.get("expected_payments") or block.get("initial_payments")
        put_if_present(
            input_obj,
            f"{title_prefix}ExpectedPayments",
            normalize_initial_payments(payments),
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
