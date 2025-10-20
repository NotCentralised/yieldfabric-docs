"""
Obligation operations executor
"""

from .base import BaseExecutor
from ..models import Command, CommandResponse
from ..utils.graphql import GraphQLMutation


class ObligationExecutor(BaseExecutor):
    """Executor for obligation operations."""
    
    def execute(self, command: Command) -> CommandResponse:
        """Execute obligation command."""
        command_type = command.type.lower()
        
        if command_type == "create_obligation":
            return self._execute_create_obligation(command)
        elif command_type == "accept_obligation":
            return self._execute_accept_obligation(command)
        elif command_type == "transfer_obligation":
            return self._execute_transfer_obligation(command)
        elif command_type == "cancel_obligation":
            return self._execute_cancel_obligation(command)
        else:
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown obligation command type: {command_type}"]
            )
    
    def _execute_create_obligation(self, command: Command) -> CommandResponse:
        """Execute create obligation command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CREATE_OBLIGATION
        variables = {
            "input": {
                "counterpart": params.counterpart,
                "denomination": params.denomination or params.asset_id,
            }
        }
        
        # Add optional parameters
        if params.obligation_address:
            variables["input"]["obligationAddress"] = params.obligation_address
        if params.obligation_group_id:
            variables["input"]["obligationGroupId"] = params.obligation_group_id
        if params.obligor:
            variables["input"]["obligor"] = params.obligor
        if params.notional:
            variables["input"]["notional"] = str(params.notional)
        if params.expiry:
            variables["input"]["expiry"] = params.expiry
        if params.data:
            variables["input"]["data"] = params.data
        if params.initial_payments:
            variables["input"]["initialPayments"] = params.initial_payments
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Create obligation failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Create obligation failed"]
            )
        
        obligation_data = response.get_data("createObligation", {})
        if obligation_data.get("success"):
            outputs = {
                "account_address": obligation_data.get("accountAddress"),
                "contract_id": obligation_data.get("contractId"),
                "transaction_id": obligation_data.get("transactionId"),
                "message": obligation_data.get("message"),
                "message_id": obligation_data.get("messageId"),
                "obligation_result": obligation_data.get("obligationResult"),
                "signature": obligation_data.get("signature"),
                "timestamp": obligation_data.get("timestamp"),
                "id_hash": obligation_data.get("idHash"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Create obligation successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = obligation_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Create obligation failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_accept_obligation(self, command: Command) -> CommandResponse:
        """Execute accept obligation command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.ACCEPT_OBLIGATION
        variables = {
            "input": {
                "contractId": params.contract_id,
            }
        }
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Accept obligation failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Accept obligation failed"]
            )
        
        obligation_data = response.get_data("acceptObligation", {})
        if obligation_data.get("success"):
            outputs = {
                "account_address": obligation_data.get("accountAddress"),
                "obligation_id": obligation_data.get("obligationId"),
                "message": obligation_data.get("message"),
                "message_id": obligation_data.get("messageId"),
                "transaction_id": obligation_data.get("transactionId"),
                "signature": obligation_data.get("signature"),
                "timestamp": obligation_data.get("timestamp"),
                "accept_result": obligation_data.get("acceptResult"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Accept obligation successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = obligation_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Accept obligation failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_transfer_obligation(self, command: Command) -> CommandResponse:
        """Execute transfer obligation command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.TRANSFER_OBLIGATION
        variables = {
            "input": {
                "contractId": params.contract_id,
                "destinationId": params.destination_id,
            }
        }
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Transfer obligation failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Transfer obligation failed"]
            )
        
        transfer_data = response.get_data("transferObligation", {})
        if transfer_data.get("success"):
            outputs = {
                "message": transfer_data.get("message"),
                "account_address": transfer_data.get("accountAddress"),
                "obligation_id": transfer_data.get("obligationId"),
                "destination_id": transfer_data.get("destinationId"),
                "destination_address": transfer_data.get("destinationAddress"),
                "transfer_result": transfer_data.get("transferResult"),
                "message_id": transfer_data.get("messageId"),
                "transaction_id": transfer_data.get("transactionId"),
                "signature": transfer_data.get("signature"),
                "timestamp": transfer_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Transfer obligation successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = transfer_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Transfer obligation failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])
    
    def _execute_cancel_obligation(self, command: Command) -> CommandResponse:
        """Execute cancel obligation command."""
        self.log_command_start(command)
        
        token = self.get_token(command)
        if not token:
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, ["Failed to get JWT token"]
            )
        
        params = command.parameters
        
        mutation = GraphQLMutation.CANCEL_OBLIGATION
        variables = {
            "input": {
                "contractId": params.contract_id,
            }
        }
        if params.idempotency_key:
            variables["input"]["idempotencyKey"] = params.idempotency_key
        
        response = self.payments_service.graphql_mutation(mutation, variables, token)
        
        if not response.success:
            self.logger.error(f"    ❌ Cancel obligation failed: {response.get_error_message()}")
            self.log_command_failure(command)
            return CommandResponse.error_response(
                command.name, command.type, [response.get_error_message() or "Cancel obligation failed"]
            )
        
        cancel_data = response.get_data("cancelObligation", {})
        if cancel_data.get("success"):
            outputs = {
                "message": cancel_data.get("message"),
                "account_address": cancel_data.get("accountAddress"),
                "obligation_id": cancel_data.get("obligationId"),
                "cancel_result": cancel_data.get("cancelResult"),
                "message_id": cancel_data.get("messageId"),
                "transaction_id": cancel_data.get("transactionId"),
                "signature": cancel_data.get("signature"),
                "timestamp": cancel_data.get("timestamp"),
            }
            self.store_outputs(command.name, outputs)
            
            self.logger.success("    ✅ Cancel obligation successful!")
            self.log_command_success(command)
            return CommandResponse.success_response(command.name, command.type, outputs)
        else:
            message = cancel_data.get("message", "Operation not successful")
            self.logger.error(f"    ❌ Cancel obligation failed: {message}")
            self.log_command_failure(command)
            return CommandResponse.error_response(command.name, command.type, [message])

