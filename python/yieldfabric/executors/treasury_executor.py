"""
Treasury operations executor — mint, burn, total_supply.
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


class TreasuryExecutor(BaseExecutor):
    """Executor for mint / burn / total_supply."""

    def execute(self, command: Command) -> CommandResponse:
        command_type = command.type.lower()
        dispatch = {
            "mint": self._execute_mint,
            "burn": self._execute_burn,
            "total_supply": self._execute_total_supply,
        }
        handler = dispatch.get(command_type)
        if handler is None:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown treasury command type: {command_type}"]
            )
        return handler(command)

    # ------------------------------------------------------------------
    # mint / burn share shape: {assetId, amount, policySecret?, idem?}.
    # ------------------------------------------------------------------

    def _execute_mint(self, command: Command) -> CommandResponse:
        return self._execute_treasury_mutation(
            command, GraphQLMutation.MINT, "mint", "Mint",
            result_field="mintResult", output_key="mint_result",
        )

    def _execute_burn(self, command: Command) -> CommandResponse:
        return self._execute_treasury_mutation(
            command, GraphQLMutation.BURN, "burn", "Burn",
            result_field="burnResult", output_key="burn_result",
        )

    def _execute_treasury_mutation(
        self,
        command: Command,
        mutation: str,
        response_root: str,
        operation_name: str,
        *,
        result_field: str,
        output_key: str,
    ) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        denomination = params.denomination or params.asset_id

        self.log_parameters({
            "denomination": denomination,
            "amount": params.amount,
            "policy_secret": "***" if params.policy_secret else None,
            "idempotency_key": params.idempotency_key,
        })

        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(params.amount),
            }
        }
        if params.policy_secret:
            variables["input"]["policySecret"] = params.policy_secret
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

    # ------------------------------------------------------------------
    # total_supply — read query; no message_id, no wait.
    # ------------------------------------------------------------------

    def _execute_total_supply(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        denomination = params.denomination or params.asset_id
        obligor = params.obligor

        self.log_parameters({"denomination": denomination, "obligor": obligor})

        response = self.payments_service.get_total_supply(denomination, obligor, token)
        if not response.success:
            # get_total_supply returns RESTResponse; use a lightweight
            # local error path (not graphql-shaped, so we don't use
            # _finalize_graphql_error which expects a GraphQLResponse).
            message = (
                response.get_error_message() or "Total supply query failed"
            )
            self.logger.error(f"    ❌ Total supply query failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [message]
            )

        outputs = {
            "total_supply": response.get_data("total_supply"),
            "decimals": response.get_data("decimals"),
            "denomination": denomination,
            "obligor": obligor,
            "timestamp": response.get_data("timestamp"),
        }
        self.store_outputs(command.name, outputs)

        self.logger.success("    ✅ Total supply retrieved successfully!")
        self.logger.info(
            f"    Total Supply: {outputs['total_supply']}  "
            f"Decimals: {outputs['decimals']}  Denomination: {denomination}"
            + (f"  Obligor: {obligor}" if obligor else "")
        )
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)
