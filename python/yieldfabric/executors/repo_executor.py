"""
Repo-lifecycle executor — `repurchase_swap`, `expire_collateral`,
`initiate_roll`, `complete_roll`.

These wrap the payments-direct repo mutations the base `SwapExecutor`
doesn't cover. They settle through the MQ exactly like `createSwap`, so
each finalizes via `_finalize_success` (which auto-waits for on-chain
settlement unless the command sets `wait: false`).

Inputs flow through the `CommandParameters` raw-param catch-all, so the
YAML can pass any of the backend fields without model changes. Id lists
pass through unchanged; `*_contract_references` are camelized
(`composed_contract_id` -> `composedContractId`); payment blocks use the
ergonomic `{id, payer{unlock}, payee{unlock}}` shape and are flattened by
`normalize_initial_payments`.
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation
from ..utils.graphql_input import (
    camelize_keys,
    normalize_initial_payments,
    put_if_present,
)


class RepoExecutor(BaseExecutor):
    """Executor for repo-lifecycle operations (repurchase / forfeit / roll)."""

    def execute(self, command: Command) -> CommandResponse:
        t = command.type.lower()
        if t == "repurchase_swap":
            return self._repurchase_swap(command)
        if t == "expire_collateral":
            return self._expire_collateral(command)
        if t == "expire_swap":
            return self._expire_swap(command)
        if t == "cancel_roll":
            return self._cancel_roll(command)
        if t == "initiate_roll":
            return self._initiate_roll(command)
        if t == "complete_roll":
            return self._complete_roll(command)
        return CommandResponse.error_response(
            command.name, command.type, [f"Unknown repo command type: {t}"]
        )

    # ------------------------------------------------------------------

    def _repurchase_swap(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "swapId", params.swap_id or params.get("swap_id"))
        put_if_present(input_obj, "repurchaseObligationIds", params.get("repurchase_obligation_ids"))
        put_if_present(
            input_obj, "repurchaseContractReferences",
            camelize_keys(params.get("repurchase_contract_references")),
        )
        put_if_present(input_obj, "repurchasePaymentIds", params.get("repurchase_payment_ids"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.REPURCHASE_SWAP, "repurchaseSwap", "Repurchase swap",
            input_obj,
            {"swap_id": "swapId", "repurchase_result": "repurchaseResult",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    def _expire_collateral(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "swapId", params.swap_id or params.get("swap_id"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.EXPIRE_COLLATERAL, "expireCollateral", "Expire collateral",
            input_obj,
            {"swap_id": "swapId", "expire_result": "expireResult",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    def _expire_swap(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "swapId", params.swap_id or params.get("swap_id"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.EXPIRE_SWAP, "expireSwap", "Expire swap",
            input_obj,
            {"swap_id": "swapId", "expire_result": "expireResult",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    def _cancel_roll(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "newSwapId", params.get("new_swap_id"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.CANCEL_ROLL, "cancelRoll", "Cancel roll",
            input_obj,
            {"new_swap_id": "newSwapId", "cancel_result": "cancelResult",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    def _initiate_roll(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "oldSwapId", params.get("old_swap_id"))
        put_if_present(input_obj, "newSwapId", params.get("new_swap_id"))
        put_if_present(input_obj, "newCounterparty", params.get("new_counterparty"))
        put_if_present(input_obj, "newCounterpartyWalletId", params.get("new_counterparty_wallet_id"))
        put_if_present(input_obj, "newDeadline", params.get("new_deadline"))
        put_if_present(input_obj, "newExpiry", params.get("new_expiry"))
        put_if_present(input_obj, "name", params.get("name"))
        for src, tgt in (
            ("new_counterparty_expected_payments", "newCounterpartyExpectedPayments"),
            ("new_initiator_expected_payments", "newInitiatorExpectedPayments"),
            ("new_initiator_repurchase_payments", "newInitiatorRepurchasePayments"),
            ("new_counterparty_repurchase_payments", "newCounterpartyRepurchasePayments"),
        ):
            put_if_present(input_obj, tgt, normalize_initial_payments(params.get(src)))
        put_if_present(input_obj, "repurchaseObligationIds", params.get("repurchase_obligation_ids"))
        put_if_present(
            input_obj, "repurchaseContractReferences",
            camelize_keys(params.get("repurchase_contract_references")),
        )
        put_if_present(input_obj, "repurchasePaymentIds", params.get("repurchase_payment_ids"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.INITIATE_ROLL, "initiateRoll", "Initiate roll",
            input_obj,
            {"old_swap_id": "oldSwapId", "new_swap_id": "newSwapId",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    def _complete_roll(self, command: Command) -> CommandResponse:
        params = command.parameters
        input_obj: dict = {}
        put_if_present(input_obj, "newSwapId", params.get("new_swap_id"))
        put_if_present(input_obj, "walletId", params.get("wallet_id"))
        put_if_present(input_obj, "requireManualSignature", params.get("require_manual_signature"))
        return self._run(
            command, GraphQLMutation.COMPLETE_ROLL, "completeRoll", "Complete roll",
            input_obj,
            {"new_swap_id": "newSwapId",
             "transaction_id": "transactionId", "signature": "signature"},
        )

    # ------------------------------------------------------------------

    def _run(self, command, mutation, response_root, operation_name, input_obj, outputs_extra):
        """Shared submit → settle → store tail for every repo mutation."""
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        if params.idempotency_key:
            input_obj["idempotencyKey"] = params.idempotency_key

        response = self.payments_service.graphql_mutation(mutation, {"input": input_obj}, token)
        if not response.success:
            return self._finalize_graphql_error(command, response, operation_name=operation_name)

        data = response.get_data(response_root, {})
        if not data.get("success"):
            return self._finalize_business_error(
                command, data.get("message", f"{operation_name} not successful"),
                operation_name=operation_name,
            )

        outputs = {
            "account_address": data.get("accountAddress"),
            "message": data.get("message"),
            "message_id": data.get("messageId"),
            "timestamp": data.get("timestamp"),
        }
        for out_key, data_key in outputs_extra.items():
            outputs[out_key] = data.get(data_key)
        return self._finalize_success(
            command, token, outputs, success_message=f"{operation_name} successful!",
        )
