"""
Swap operations executor
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


class SwapExecutor(BaseExecutor):
    """Executor for swap operations."""
    
    def execute(self, command: Command) -> CommandResponse:
        """Execute swap command."""
        command_type = command.type.lower()
        
        if command_type == "create_swap":
            return self._execute_create_swap(command)
        elif command_type == "create_obligation_swap":
            return self._execute_create_obligation_swap(command)
        elif command_type == "create_payment_swap":
            return self._execute_create_payment_swap(command)
        elif command_type == "complete_swap":
            return self._execute_complete_swap(command)
        elif command_type == "cancel_swap":
            return self._execute_cancel_swap(command)
        else:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown swap command type: {command_type}"]
            )
    
    def _execute_create_swap(self, command: Command) -> CommandResponse:
        """Execute unified create swap command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CREATE_SWAP
        variables = {
            "input": {
                "counterparty": params.counterpart,
            }
        }
        
        # Add initiator parameters
        if params.initiator:
            variables["input"]["initiator"] = params.initiator
        
        # Add counterparty parameters
        if params.counterparty:
            variables["input"]["counterparty"] = params.counterparty
        
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Create swap failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Create swap failed"]
            )
        
        swap_data = response.get_data("createSwap", {})
        if swap_data.get("success"):
            outputs = {
                "swap_id": swap_data.get("swapId"),
                "account_address": swap_data.get("accountAddress"),
                "counterparty_address": swap_data.get("counterpartyAddress"),
                "message": swap_data.get("message"),
                "swap_result": swap_data.get("swapResult"),
                "message_id": swap_data.get("messageId"),
                "timestamp": swap_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Create swap successful!")
            self.logger.info(f"      Swap ID: {outputs.get('swap_id')}")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = swap_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Create swap failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_create_obligation_swap(self, command: Command) -> CommandResponse:
        """Execute create obligation swap command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CREATE_OBLIGATION_SWAP
        variables = {
            "input": {
                "counterparty": params.counterpart,
            }
        }
        
        # Add initiator parameters
        if params.initiator:
            variables["input"]["initiator"] = params.initiator
        
        # Add counterparty parameters  
        if params.counterparty:
            variables["input"]["counterparty"] = params.counterparty
        
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Create obligation swap failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Create obligation swap failed"]
            )
        
        swap_data = response.get_data("createObligationSwap", {})
        if swap_data.get("success"):
            outputs = {
                "swap_id": swap_data.get("swapId"),
                "account_address": swap_data.get("accountAddress"),
                "counterparty_address": swap_data.get("counterpartyAddress"),
                "message": swap_data.get("message"),
                "swap_result": swap_data.get("swapResult"),
                "message_id": swap_data.get("messageId"),
                "timestamp": swap_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Create obligation swap successful!")
            self.logger.info(f"      Swap ID: {outputs.get('swap_id')}")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = swap_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Create obligation swap failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_create_payment_swap(self, command: Command) -> CommandResponse:
        """Execute create payment swap command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CREATE_PAYMENT_SWAP
        variables = {
            "input": {
                "counterparty": params.counterpart,
            }
        }
        
        # Add initiator parameters
        if params.initiator:
            variables["input"]["initiator"] = params.initiator
        
        # Add counterparty parameters
        if params.counterparty:
            variables["input"]["counterparty"] = params.counterparty
        
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Create payment swap failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Create payment swap failed"]
            )
        
        swap_data = response.get_data("createPaymentSwap", {})
        if swap_data.get("success"):
            outputs = {
                "swap_id": swap_data.get("swapId"),
                "account_address": swap_data.get("accountAddress"),
                "counterparty_address": swap_data.get("counterpartyAddress"),
                "message": swap_data.get("message"),
                "swap_result": swap_data.get("swapResult"),
                "message_id": swap_data.get("messageId"),
                "timestamp": swap_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Create payment swap successful!")
            self.logger.info(f"      Swap ID: {outputs.get('swap_id')}")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = swap_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Create payment swap failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_complete_swap(self, command: Command) -> CommandResponse:
        """Execute complete swap command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.COMPLETE_SWAP
        variables = {
            "input": {
                "swapId": params.swap_id,
            }
        }
        
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Complete swap failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Complete swap failed"]
            )
        
        swap_data = response.get_data("completeSwap", {})
        if swap_data.get("success"):
            outputs = {
                "swap_id": swap_data.get("swapId"),
                "account_address": swap_data.get("accountAddress"),
                "message": swap_data.get("message"),
                "complete_result": swap_data.get("completeResult"),
                "message_id": swap_data.get("messageId"),
                "timestamp": swap_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Complete swap successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = swap_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Complete swap failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_cancel_swap(self, command: Command) -> CommandResponse:
        """Execute cancel swap command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CANCEL_SWAP
        variables = {
            "input": {
                "swapId": params.swap_id,
            }
        }
        
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Cancel swap failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Cancel swap failed"]
            )
        
        swap_data = response.get_data("cancelSwap", {})
        if swap_data.get("success"):
            outputs = {
                "swap_id": swap_data.get("swapId"),
                "account_address": swap_data.get("accountAddress"),
                "message": swap_data.get("message"),
                "cancel_result": swap_data.get("cancelResult"),
                "message_id": swap_data.get("messageId"),
                "timestamp": swap_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Cancel swap successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = swap_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Cancel swap failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])

