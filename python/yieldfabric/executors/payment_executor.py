"""
Payment operations executor
"""

from typing import Dict

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


class PaymentExecutor(BaseExecutor):
    """Executor for payment operations (deposit, withdraw, instant, accept)."""
    
    def execute(self, command: Command) -> CommandResponse:
        """Execute payment command."""
        command_type = command.type.lower()
        
        if command_type == "deposit":
            return self._execute_deposit(command)
        elif command_type == "withdraw":
            return self._execute_withdraw(command)
        elif command_type == "instant":
            return self._execute_instant(command)
        elif command_type == "accept":
            return self._execute_accept(command)
        else:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown payment command type: {command_type}"]
            )
    
    def _execute_deposit(self, command: Command) -> CommandResponse:
        """Execute deposit command."""
        self.log_command_start(command)
        
        # Get token
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                ["Failed to get JWT token"]
            )
        
        # Prepare parameters
        params = command.parameters
        denomination = params.denomination or params.asset_id
        amount = params.amount
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "denomination": denomination,
            "amount": amount,
            "idempotency_key": idempotency_key
        })
        
        # Build GraphQL mutation
        mutation = GraphQLMutation.DEPOSIT
        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(amount),
            }
        }
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        # Execute mutation
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Deposit failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type,
                [response.get_error_message() or "Deposit failed"]
            )
        
        # Extract and store outputs
        deposit_data = response.get_data("deposit", {})
        if deposit_data.get("success"):
            outputs = {
                "account_address": deposit_data.get("accountAddress"),
                "message": deposit_data.get("message"),
                "message_id": deposit_data.get("messageId"),
                "deposit_result": deposit_data.get("depositResult"),
                "timestamp": deposit_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Deposit successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = deposit_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Deposit failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_withdraw(self, command: Command) -> CommandResponse:
        """Execute withdraw command."""
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
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "denomination": denomination,
            "amount": amount,
            "idempotency_key": idempotency_key
        })
        
        mutation = GraphQLMutation.WITHDRAW
        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(amount),
            }
        }
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Withdraw failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Withdraw failed"]
            )
        
        withdraw_data = response.get_data("withdraw", {})
        if withdraw_data.get("success"):
            outputs = {
                "message_id": withdraw_data.get("messageId"),
                "account_address": withdraw_data.get("accountAddress"),
                "withdraw_result": withdraw_data.get("withdrawResult"),
                "timestamp": withdraw_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Withdraw successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = withdraw_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Withdraw failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_instant(self, command: Command) -> CommandResponse:
        """Execute instant payment command."""
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
        destination_id = params.destination_id
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "denomination": denomination,
            "amount": amount,
            "destination_id": destination_id,
            "idempotency_key": idempotency_key
        })
        
        mutation = GraphQLMutation.INSTANT
        variables = {
            "input": {
                "assetId": denomination,
                "amount": str(amount),
                "destinationId": destination_id,
            }
        }
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Instant payment failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Instant payment failed"]
            )
        
        instant_data = response.get_data("instant", {})
        if instant_data.get("success"):
            outputs = {
                "account_address": instant_data.get("accountAddress"),
                "destination_id": instant_data.get("destinationId"),
                "message": instant_data.get("message"),
                "id_hash": instant_data.get("idHash"),
                "message_id": instant_data.get("messageId"),
                "payment_id": instant_data.get("paymentId"),
                "send_result": instant_data.get("sendResult"),
                "timestamp": instant_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Instant payment successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = instant_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Instant payment failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_accept(self, command: Command) -> CommandResponse:
        """Execute accept payment command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        payment_id = params.payment_id
        idempotency_key = params.idempotency_key
        
        self.log_parameters({
            "payment_id": payment_id,
            "idempotency_key": idempotency_key
        })
        
        mutation = GraphQLMutation.ACCEPT
        variables = {
            "input": {
                "paymentId": payment_id,
            }
        }
        if idempotency_key:
            variables["input"]["idempotencyKey"] = idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Accept failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Accept failed"]
            )
        
        accept_data = response.get_data("accept", {})
        if accept_data.get("success"):
            outputs = {
                "account_address": accept_data.get("accountAddress"),
                "message": accept_data.get("message"),
                "id_hash": accept_data.get("idHash"),
                "message_id": accept_data.get("messageId"),
                "accept_result": accept_data.get("acceptResult"),
                "timestamp": accept_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Accept successful!")
            for key, value in outputs.items():
                if value:
                    self.logger.info(f"      {key}: {value}")
            
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = accept_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Accept failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])

