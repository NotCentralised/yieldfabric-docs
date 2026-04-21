"""
Query operations executor — read-only balance / obligations / groups.

Queries don't submit to MQ, so there's no message_id and the `wait`
parameter is a no-op (the listener flag, if set, logs a warning
via _maybe_wait_for_execution's "no message_id" branch).
"""

import json

from .base import BaseExecutor
from ..models import Command, CommandResponse


class QueryExecutor(BaseExecutor):
    """Executor for balance / obligations / list_groups."""

    def execute(self, command: Command) -> CommandResponse:
        command_type = command.type.lower()
        dispatch = {
            "balance": self._execute_balance,
            "obligations": self._execute_obligations,
            "list_groups": self._execute_list_groups,
        }
        handler = dispatch.get(command_type)
        if handler is None:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown query command type: {command_type}"]
            )
        return handler(command)

    # ------------------------------------------------------------------

    def _execute_balance(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        params = command.parameters
        denomination = params.denomination or params.asset_id

        self.log_parameters({
            "denomination": denomination,
            "obligor": params.obligor,
            "group_id": params.group_id,
        })

        response = self.payments_service.get_balance(
            denomination, params.obligor, params.group_id, token
        )
        if not response.success:
            message = response.get_error_message() or "Balance query failed"
            self.logger.error(f"    ❌ Balance query failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [message]
            )

        balance_data = response.get_data("balance", {})
        outputs = {
            "private_balance": balance_data.get("private_balance"),
            "public_balance": balance_data.get("public_balance"),
            "decimals": balance_data.get("decimals"),
            "beneficial_balance": balance_data.get("beneficial_balance"),
            "outstanding": balance_data.get("outstanding"),
            "locked_out": json.dumps(balance_data.get("locked_out", [])),
            "locked_in": json.dumps(balance_data.get("locked_in", [])),
            "denomination": denomination,
            "obligor": params.obligor,
            "group_id": params.group_id,
            "timestamp": response.get_data("timestamp"),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message="Balance retrieved successfully!",
        )

    def _execute_obligations(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        response = self.payments_service.get_obligations(token)
        if not response.success:
            message = response.get_error_message() or "Obligations query failed"
            self.logger.error(f"    ❌ Obligations query failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [message]
            )

        obligations = response.get_data("obligations", [])
        outputs = {
            "obligations": json.dumps(obligations),
            "count": len(obligations) if isinstance(obligations, list) else 0,
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"Found {outputs['count']} obligations",
        )

    def _execute_list_groups(self, command: Command) -> CommandResponse:
        self.log_command_start(command)
        token, err = self._acquire_token_or_error(command)
        if err:
            return err

        groups = self.auth_service.get_user_groups(token)
        outputs = {
            "groups": json.dumps(groups),
            "group_count": len(groups),
        }
        return self._finalize_success(
            command, token, outputs,
            success_message=f"Found {outputs['group_count']} groups",
        )
