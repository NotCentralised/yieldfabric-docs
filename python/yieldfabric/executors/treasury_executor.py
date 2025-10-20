"""
Treasury operations executor
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


class TreasuryExecutor(BaseExecutor):
    """Executor for treasury operations (mint, burn, total_supply)."""
    
    def execute(self, command: Command) -> CommandResponse:
        """Execute treasury command."""
        command_type = command.type.lower()
        
        if command_type == "mint":
            return self._execute_mint(command)
        elif command_type == "burn":
            return self._execute_burn(command)
        elif command_type == "total_supply":
            return self._execute_total_supply(command)
        else:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown treasury command type: {command_type}"]
            )
    
    def _execute_mint(self, command: Command) -> CommandResponse:
        """Execute mint command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        denomination = params.denomination or params.asset_id
        amount = params.amount
        policy_secret = params.policy_secret
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "denomination": denomination,
            "amount": amount,
            "policy_secret": "***" if policy_secret else None,
            "idempotency_key": idempotency_key
        })
        
        mutation = GraphQLMutation.MINT
        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(amount),
            }
        }
        
        if policy_secret:
            variables["input"]["policySecret"] = policy_secret
        
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Mint failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Mint failed"]
            )
        
        mint_data = response.get_data("mint", {})
        if mint_data.get("success"):
            outputs = {
                "account_address": mint_data.get("accountAddress"),
                "message": mint_data.get("message"),
                "mint_result": mint_data.get("mintResult"),
                "message_id": mint_data.get("messageId"),
                "timestamp": mint_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Mint successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = mint_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Mint failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_burn(self, command: Command) -> CommandResponse:
        """Execute burn command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        denomination = params.denomination or params.asset_id
        amount = params.amount
        policy_secret = params.policy_secret
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "denomination": denomination,
            "amount": amount,
            "policy_secret": "***" if policy_secret else None,
            "idempotency_key": idempotency_key
        })
        
        mutation = GraphQLMutation.BURN
        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(amount),
            }
        }
        
        if policy_secret:
            variables["input"]["policySecret"] = policy_secret
        
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Burn failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Burn failed"]
            )
        
        burn_data = response.get_data("burn", {})
        if burn_data.get("success"):
            outputs = {
                "account_address": burn_data.get("accountAddress"),
                "message": burn_data.get("message"),
                "burn_result": burn_data.get("burnResult"),
                "message_id": burn_data.get("messageId"),
                "timestamp": burn_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Burn successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = burn_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Burn failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_total_supply(self, command: Command) -> CommandResponse:
        """Execute total supply query."""
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
        
        self.log_parameters({
            "denomination": denomination,
            "obligor": obligor
        })
        
        response = self.payments_service.get_total_supply(denomination, obligor, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Total supply query failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Total supply query failed"]
            )
        
        total_supply = response.get_data("total_supply")
        decimals = response.get_data("decimals")
        timestamp = response.get_data("timestamp")
        
        outputs = {
            "total_supply": total_supply,
            "decimals": decimals,
            "denomination": denomination,
            "obligor": obligor,
            "timestamp": timestamp,
        }
        self.store_outputs(command.name, outputs)
        
        self.logger.success("    ✅ Total supply retrieved successfully!")
        self.logger.info("  📋 Total Supply Information:")
        self.logger.info(f"      Total Supply: {total_supply}")
        self.logger.info(f"      Decimals: {decimals}")
        self.logger.info(f"      Denomination: {denomination}")
        if obligor:
            self.logger.info(f"      Obligor: {obligor}")
        
        self.log_command_success(command)
        return CommandResponse.success_response(command.name, command.type, outputs)

