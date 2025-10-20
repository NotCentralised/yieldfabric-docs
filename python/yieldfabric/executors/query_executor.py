"""
Query operations executor
"""

import json

from .base import BaseExecutor
from ..models import Command, CommandResponse


class QueryExecutor(BaseExecutor):
    """Executor for query operations (balance, obligations, list_groups)."""
    
    def execute(self, command: Command) -> CommandResponse:
        """Execute query command."""
        command_type = command.type.lower()
        
        if command_type == "balance":
            return self._execute_balance(command)
        elif command_type == "obligations":
            return self._execute_obligations(command)
        elif command_type == "list_groups":
            return self._execute_list_groups(command)
        else:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown query command type: {command_type}"]
            )
    
    def _execute_balance(self, command: Command) -> CommandResponse:
        """Execute balance query."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        denomination = params.denomination or params.asset_id
        obligor = params.obligor
        group_id = params.group_id
        
        self.log_parameters({
            "denomination": denomination,
            "obligor": obligor,
            "group_id": group_id
        })
        
        response = self.payments_service.get_balance(denomination, obligor, group_id, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Balance query failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Balance query failed"]
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
            "obligor": obligor,
            "group_id": group_id,
            "timestamp": response.get_data("timestamp"),
        }
        self.store_outputs(command.name, outputs)
        
        self.logger.success("    ✅ Balance retrieved successfully!")
        self.logger.info("  📋 Balance Information:")
        self.logger.info(f"      Private Balance: {outputs['private_balance']}")
        self.logger.info(f"      Public Balance: {outputs['public_balance']}")
        self.logger.info(f"      Beneficial Balance: {outputs['beneficial_balance']}")
        
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)
    
    def _execute_obligations(self, command: Command) -> CommandResponse:
        """Execute obligations query."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        response = self.payments_service.get_obligations(token)
        
        if not response.success:
            self.logger.error(f"    ❌ Obligations query failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Obligations query failed"]
            )
        
        obligations = response.get_data("obligations", [])
        
        outputs = {
            "obligations": json.dumps(obligations),
            "count": len(obligations) if isinstance(obligations, list) else 0,
        }
        self.store_outputs(command.name, outputs)
        
        self.logger.success(f"    ✅ Found {outputs['count']} obligations")
        
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)
    
    def _execute_list_groups(self, command: Command) -> CommandResponse:
        """Execute list groups query."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        groups = self.auth_service.get_user_groups(token)
        
        outputs = {
            "groups": json.dumps(groups),
            "group_count": len(groups),
        }
        self.store_outputs(command.name, outputs)
        
        self.logger.success(f"    ✅ Found {outputs['group_count']} groups")
        for group in groups:
            self.logger.info(f"      • {group.get('name')} (ID: {group.get('id')})")
        
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

