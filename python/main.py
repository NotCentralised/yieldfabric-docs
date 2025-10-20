"""
YieldFabric GraphQL Commands Execution Script - Python Port
Reads a YAML file and executes each command sequentially using GraphQL mutations.
"""

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

from .utils import Colors, echo_with_color, command_output_store, parse_yaml, check_service_running
from .auth import auth_service
from .executors import command_executor
from .executors_additional import additional_command_executor
from .validation import command_validator


class YieldFabricCommandRunner:
    """Main class for executing YieldFabric commands."""
    
    def __init__(self, pay_service_url: str = "https://pay.yieldfabric.io",
                 auth_service_url: str = "https://auth.yieldfabric.io"):
        self.pay_service_url = pay_service_url
        self.auth_service_url = auth_service_url
        self.command_delay = int(os.environ.get('COMMAND_DELAY', '3'))
    
    def execute_command(self, command_index: int, commands_file: str) -> bool:
        """Execute a single command based on its index in the YAML file."""
        echo_with_color(Colors.PURPLE, f"🔍 DEBUG: execute_command called with index {command_index}")
        
        # Parse command details
        command_name = parse_yaml(commands_file, f".commands[{command_index}].name")
        command_type = parse_yaml(commands_file, f".commands[{command_index}].type")
        user_email = parse_yaml(commands_file, f".commands[{command_index}].user.id")
        user_password = parse_yaml(commands_file, f".commands[{command_index}].user.password")
        group_name = parse_yaml(commands_file, f".commands[{command_index}].user.group")
        
        # Parse command parameters
        denomination = parse_yaml(commands_file, f".commands[{command_index}].parameters.denomination")
        amount = parse_yaml(commands_file, f".commands[{command_index}].parameters.amount")
        destination_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.destination_id")
        payment_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.payment_id")
        idempotency_key = parse_yaml(commands_file, f".commands[{command_index}].parameters.idempotency_key")
        asset_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.asset_id")
        obligor = parse_yaml(commands_file, f".commands[{command_index}].parameters.obligor")
        group_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.group_id")
        
        # Use asset_id if denomination is not provided (for backward compatibility)
        if not denomination or denomination == "null":
            denomination = asset_id
        
        # Parse create_obligation specific parameters
        counterpart = parse_yaml(commands_file, f".commands[{command_index}].parameters.counterpart")
        obligation_address = parse_yaml(commands_file, f".commands[{command_index}].parameters.obligation_address")
        obligation_group_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.obligation_group_id")
        notional = parse_yaml(commands_file, f".commands[{command_index}].parameters.notional")
        expiry = parse_yaml(commands_file, f".commands[{command_index}].parameters.expiry")
        data = parse_yaml(commands_file, f".commands[{command_index}].parameters.data")
        initial_payments_amount = parse_yaml(commands_file, f".commands[{command_index}].parameters.initial_payments.amount")
        initial_payments_json = parse_yaml(commands_file, f".commands[{command_index}].parameters.initial_payments.payments")
        
        # Parse accept_obligation specific parameters
        contract_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.contract_id")
        
        # Parse transfer_obligation specific parameters
        transfer_contract_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.contract_id")
        transfer_destination_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.destination_id")
        
        # Parse cancel_obligation specific parameters
        cancel_contract_id = parse_yaml(commands_file, f".commands[{command_index}].parameters.contract_id")
        
        # Parse treasury specific parameters
        policy_secret = parse_yaml(commands_file, f".commands[{command_index}].parameters.policy_secret")
        
        # Apply variable substitution to parameters
        echo_with_color(Colors.CYAN, "  🔄 Applying variable substitution to parameters...")
        denomination = command_output_store.substitute_variables(denomination or "")
        amount = command_output_store.substitute_variables(amount or "")
        destination_id = command_output_store.substitute_variables(destination_id or "")
        payment_id = command_output_store.substitute_variables(payment_id or "")
        idempotency_key = command_output_store.substitute_variables(idempotency_key or "")
        obligor = command_output_store.substitute_variables(obligor or "")
        group_id = command_output_store.substitute_variables(group_id or "")
        group_name = command_output_store.substitute_variables(group_name or "")
        
        # Apply variable substitution to create_obligation specific parameters
        counterpart = command_output_store.substitute_variables(counterpart or "")
        obligation_address = command_output_store.substitute_variables(obligation_address or "")
        obligation_group_id = command_output_store.substitute_variables(obligation_group_id or "")
        notional = command_output_store.substitute_variables(notional or "")
        expiry = command_output_store.substitute_variables(expiry or "")
        data = command_output_store.substitute_variables(data or "")
        initial_payments_amount = command_output_store.substitute_variables(initial_payments_amount or "")
        
        # Apply variable substitution to accept_obligation specific parameters
        contract_id = command_output_store.substitute_variables(contract_id or "")
        
        # Apply variable substitution to transfer_obligation specific parameters
        transfer_contract_id = command_output_store.substitute_variables(transfer_contract_id or "")
        transfer_destination_id = command_output_store.substitute_variables(transfer_destination_id or "")
        
        # Apply variable substitution to cancel_obligation specific parameters
        cancel_contract_id = command_output_store.substitute_variables(cancel_contract_id or "")
        
        # Apply variable substitution to treasury specific parameters
        policy_secret = command_output_store.substitute_variables(policy_secret or "")
        
        echo_with_color(Colors.PURPLE, f"🚀 Executing command {command_index + 1}: {command_name}")
        echo_with_color(Colors.BLUE, f"  Type: {command_type}")
        echo_with_color(Colors.BLUE, f"  User: {user_email}")
        if group_name:
            echo_with_color(Colors.CYAN, f"  Group: {group_name} (delegation)")
        echo_with_color(Colors.BLUE, "  Parameters after substitution:")
        if denomination:
            echo_with_color(Colors.BLUE, f"    denomination: {denomination}")
        if amount:
            echo_with_color(Colors.BLUE, f"    amount: {amount}")
        if destination_id:
            echo_with_color(Colors.BLUE, f"    destination_id: {destination_id}")
        if payment_id:
            echo_with_color(Colors.BLUE, f"    payment_id: {payment_id}")
        if idempotency_key:
            echo_with_color(Colors.BLUE, f"    idempotency_key: {idempotency_key}")
        if obligor:
            echo_with_color(Colors.BLUE, f"    obligor: {obligor}")
        if group_id:
            echo_with_color(Colors.BLUE, f"    group_id: {group_id}")
        
        # Execute command based on type
        try:
            if command_type == "deposit":
                return command_executor.execute_deposit(
                    command_name, user_email, user_password, denomination, amount, 
                    idempotency_key, group_name
                )
            elif command_type == "withdraw":
                return command_executor.execute_withdraw(
                    command_name, user_email, user_password, denomination, amount, 
                    idempotency_key, group_name
                )
            elif command_type == "instant":
                return command_executor.execute_instant(
                    command_name, user_email, user_password, denomination, amount, 
                    destination_id, idempotency_key, group_name
                )
            elif command_type == "accept":
                return command_executor.execute_accept(
                    command_name, user_email, user_password, payment_id, 
                    idempotency_key, group_name
                )
            elif command_type == "balance":
                return command_executor.execute_balance(
                    command_name, user_email, user_password, denomination, 
                    obligor, group_id, group_name
                )
            elif command_type == "create_obligation":
                # Parse data and initial_payments_json as JSON if they exist
                data_dict = None
                if data and data != "null" and data != "{}":
                    try:
                        import json
                        data_dict = json.loads(data)
                    except json.JSONDecodeError:
                        data_dict = {}
                
                initial_payments_list = None
                if initial_payments_json and initial_payments_json != "null" and initial_payments_json != "[]":
                    try:
                        import json
                        initial_payments_list = json.loads(initial_payments_json)
                    except json.JSONDecodeError:
                        initial_payments_list = []
                
                return additional_command_executor.execute_create_obligation(
                    command_name, user_email, user_password, counterpart, denomination,
                    notional, expiry, obligor, obligation_address, obligation_group_id,
                    data_dict, initial_payments_amount, initial_payments_list,
                    idempotency_key, group_name
                )
            elif command_type == "accept_obligation":
                return additional_command_executor.execute_accept_obligation(
                    command_name, user_email, user_password, contract_id, 
                    idempotency_key, group_name
                )
            elif command_type == "obligations":
                return additional_command_executor.execute_obligations(
                    command_name, user_email, user_password, group_name
                )
            elif command_type == "list_groups":
                return additional_command_executor.execute_list_groups(
                    command_name, user_email, user_password, group_name
                )
            else:
                echo_with_color(Colors.RED, f"❌ Unknown command type: {command_type}")
                return False
        except Exception as e:
            echo_with_color(Colors.RED, f"❌ Error executing command {command_name}: {e}")
            return False
    
    def execute_all_commands(self, yaml_file: str) -> bool:
        """Execute all commands from the YAML file."""
        echo_with_color(Colors.CYAN, "🚀 Executing all commands from commands.yaml using GraphQL mutations...")
        echo_with_color(Colors.CYAN, "")
        
        # Validate commands file
        if not command_validator.validate_commands_file(yaml_file):
            echo_with_color(Colors.RED, "❌ Commands file validation failed")
            return False
        
        # Check service status
        if not check_service_running("Auth Service", self.auth_service_url):
            echo_with_color(Colors.RED, f"❌ Auth service is not reachable at {self.auth_service_url}")
            echo_with_color(Colors.YELLOW, "Please check your connection or start the auth service:")
            echo_with_color(Colors.YELLOW, "   Local: cd ../yieldfabric-auth && cargo run")
            echo_with_color(Colors.YELLOW, "   Remote: Verify {self.auth_service_url} is accessible")
            return False
        
        if not check_service_running("Payments Service", self.pay_service_url):
            echo_with_color(Colors.RED, f"❌ Payments service is not reachable at {self.pay_service_url}")
            echo_with_color(Colors.YELLOW, "Please check your connection or start the payments service:")
            echo_with_color(Colors.YELLOW, "   Local: cd ../yieldfabric-payments && cargo run")
            echo_with_color(Colors.BLUE, f"   GraphQL endpoint will be available at: {self.pay_service_url}/graphql")
            return False
        
        # Get command count
        command_count = int(parse_yaml(yaml_file, '.commands | length') or 0)
        success_count = 0
        total_count = command_count
        
        echo_with_color(Colors.GREEN, f"✅ Found {command_count} commands to execute")
        echo_with_color(Colors.CYAN, "")
        
        # Execute each command sequentially
        for i in range(command_count):
            echo_with_color(Colors.PURPLE, "=" * 80)
            echo_with_color(Colors.CYAN, f"🔍 DEBUG: About to execute command {i+1} (index {i})")
            
            if self.execute_command(i, yaml_file):
                success_count += 1
                echo_with_color(Colors.GREEN, f"✅ Command {i+1} completed successfully")
            else:
                echo_with_color(Colors.RED, f"❌ Command {i+1} failed")
                echo_with_color(Colors.YELLOW, "Continuing with next command...")
            
            echo_with_color(Colors.CYAN, "")
            
            # Add configurable wait between commands (except for the last command)
            if i + 1 < command_count:
                echo_with_color(Colors.CYAN, f"⏳ Waiting {self.command_delay} seconds before next command...")
                time.sleep(self.command_delay)
        
        echo_with_color(Colors.PURPLE, "=" * 80)
        echo_with_color(Colors.GREEN, "🎉 Commands execution completed!")
        echo_with_color(Colors.BLUE, f"   Successful: {success_count}/{total_count}")
        
        if success_count == total_count:
            echo_with_color(Colors.GREEN, "   ✅ All commands executed successfully!")
            return True
        else:
            echo_with_color(Colors.YELLOW, "   ⚠️  Some commands failed")
            return False
    
    def show_commands_status(self, yaml_file: str) -> bool:
        """Show commands status and requirements."""
        return command_validator.show_commands_status(yaml_file)
    
    def show_stored_variables(self) -> None:
        """Show all stored variables for debugging."""
        command_output_store.debug_show_variables()
    
    def show_help(self) -> None:
        """Show help message."""
        echo_with_color(Colors.CYAN, "YieldFabric GraphQL Commands Execution Script - Python Port")
        echo_with_color(Colors.CYAN, "=============================================================")
        echo_with_color(Colors.CYAN, "")
        echo_with_color(Colors.CYAN, "Usage: python -m yieldfabric.main [command] [yaml_file]")
        echo_with_color(Colors.CYAN, "")
        echo_with_color(Colors.CYAN, "Commands:")
        echo_with_color(Colors.GREEN, "  execute     - Execute all commands from YAML file (default)")
        echo_with_color(Colors.GREEN, "  status      - Show current status and requirements")
        echo_with_color(Colors.GREEN, "  validate    - Validate YAML file structure")
        echo_with_color(Colors.GREEN, "  variables   - Show stored variables for debugging")
        echo_with_color(Colors.GREEN, "  help        - Show this help message")
        echo_with_color(Colors.CYAN, "")
        echo_with_color(Colors.CYAN, "Examples:")
        echo_with_color(Colors.CYAN, "  python -m yieldfabric.main execute commands.yaml")
        echo_with_color(Colors.CYAN, "  python -m yieldfabric.main status commands.yaml")
        echo_with_color(Colors.CYAN, "  python -m yieldfabric.main validate commands.yaml")
        echo_with_color(Colors.CYAN, "")
        echo_with_color(Colors.CYAN, "Environment Variables:")
        echo_with_color(Colors.CYAN, "  COMMAND_DELAY - Delay between commands in seconds (default: 3)")
        echo_with_color(Colors.CYAN, "  PAY_SERVICE_URL - Payments service URL (default: https://pay.yieldfabric.io)")
        echo_with_color(Colors.CYAN, "  AUTH_SERVICE_URL - Auth service URL (default: https://auth.yieldfabric.io)")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='YieldFabric GraphQL Commands Execution Script')
    parser.add_argument('command', nargs='?', default='execute', 
                       choices=['execute', 'status', 'validate', 'variables', 'help'],
                       help='Command to execute')
    parser.add_argument('yaml_file', nargs='?', default='commands.yaml',
                       help='YAML file containing commands')
    
    args = parser.parse_args()
    
    # Get service URLs from environment variables
    pay_service_url = os.environ.get('PAY_SERVICE_URL', 'https://pay.yieldfabric.io')
    auth_service_url = os.environ.get('AUTH_SERVICE_URL', 'https://auth.yieldfabric.io')
    
    # Create command runner
    runner = YieldFabricCommandRunner(pay_service_url, auth_service_url)
    
    # Handle commands
    if args.command == 'execute':
        if not os.path.exists(args.yaml_file):
            echo_with_color(Colors.RED, f"YAML file not found: {args.yaml_file}")
            sys.exit(1)
        success = runner.execute_all_commands(args.yaml_file)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        if not os.path.exists(args.yaml_file):
            echo_with_color(Colors.RED, f"YAML file not found: {args.yaml_file}")
            sys.exit(1)
        success = runner.show_commands_status(args.yaml_file)
        sys.exit(0 if success else 1)
    
    elif args.command == 'validate':
        if not os.path.exists(args.yaml_file):
            echo_with_color(Colors.RED, f"YAML file not found: {args.yaml_file}")
            sys.exit(1)
        success = command_validator.validate_commands_file(args.yaml_file)
        sys.exit(0 if success else 1)
    
    elif args.command == 'variables':
        runner.show_stored_variables()
        sys.exit(0)
    
    elif args.command == 'help':
        runner.show_help()
        sys.exit(0)
    
    else:
        echo_with_color(Colors.RED, f"Unknown command: {args.command}")
        runner.show_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
