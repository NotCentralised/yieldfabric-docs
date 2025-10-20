"""
YieldFabric Validation Module
Contains functions for validating commands and showing status.
"""

import os
from typing import Any, Dict, List, Optional
from .utils import Colors, echo_with_color, check_service_running, check_yq_available, parse_yaml


class CommandValidator:
    """Validate command structures and system status."""
    
    def __init__(self, pay_service_url: str = "https://pay.yieldfabric.io", 
                 auth_service_url: str = "https://auth.yieldfabric.io"):
        self.pay_service_url = pay_service_url
        self.auth_service_url = auth_service_url
    
    def validate_commands_file(self, yaml_file: str) -> bool:
        """Validate commands.yaml file structure."""
        echo_with_color(Colors.CYAN, f"Validating {yaml_file}...")
        
        if not os.path.exists(yaml_file):
            echo_with_color(Colors.RED, f"Commands file not found: {yaml_file}")
            return False
        
        if not check_yq_available():
            echo_with_color(Colors.RED, "yq is required for YAML validation")
            return False
        
        # Basic structure validation
        has_commands = parse_yaml(yaml_file, '.commands | length > 0')
        if has_commands != "true":
            echo_with_color(Colors.RED, f"No commands defined in {yaml_file}")
            return False
        
        # Validate each command structure
        command_count = int(parse_yaml(yaml_file, '.commands | length') or 0)
        for i in range(command_count):
            command_name = parse_yaml(yaml_file, f".commands[{i}].name")
            command_type = parse_yaml(yaml_file, f".commands[{i}].type")
            user_id = parse_yaml(yaml_file, f".commands[{i}].user.id")
            user_password = parse_yaml(yaml_file, f".commands[{i}].user.password")
            
            if not command_name:
                echo_with_color(Colors.RED, f"Error: Command {i} missing 'name' field")
                return False
            
            if not command_type:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'type' field")
                return False
            
            if not user_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'user.id' field")
                return False
            
            if not user_password:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'user.password' field")
                return False
            
            # Validate command type specific parameters
            if not self._validate_command_parameters(yaml_file, i, command_name, command_type):
                return False
        
        echo_with_color(Colors.GREEN, "Commands file validation passed")
        return True
    
    def _validate_command_parameters(self, yaml_file: str, command_index: int, 
                                   command_name: str, command_type: str) -> bool:
        """Validate parameters for a specific command type."""
        if command_type == "deposit":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            amount = parse_yaml(yaml_file, f".commands[{command_index}].parameters.amount")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not amount:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.amount' field")
                return False
        
        elif command_type == "withdraw":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            amount = parse_yaml(yaml_file, f".commands[{command_index}].parameters.amount")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not amount:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.amount' field")
                return False
        
        elif command_type == "instant":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            amount = parse_yaml(yaml_file, f".commands[{command_index}].parameters.amount")
            destination_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.destination_id")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not amount:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.amount' field")
                return False
            if not destination_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.destination_id' field")
                return False
        
        elif command_type == "accept":
            payment_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.payment_id")
            
            if not payment_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.payment_id' field")
                return False
        
        elif command_type == "balance":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            obligor = parse_yaml(yaml_file, f".commands[{command_index}].parameters.obligor")
            group_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.group_id")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not obligor:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.obligor' field")
                return False
            if not group_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.group_id' field")
                return False
        
        elif command_type == "create_obligation":
            counterpart = parse_yaml(yaml_file, f".commands[{command_index}].parameters.counterpart")
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            
            if not counterpart:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.counterpart' field")
                return False
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
        
        elif command_type == "accept_obligation":
            contract_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.contract_id")
            
            if not contract_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.contract_id' field")
                return False
        
        elif command_type == "transfer_obligation":
            contract_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.contract_id")
            destination_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.destination_id")
            
            if not contract_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.contract_id' field")
                return False
            if not destination_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.destination_id' field")
                return False
        
        elif command_type == "cancel_obligation":
            contract_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.contract_id")
            
            if not contract_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.contract_id' field")
                return False
        
        elif command_type == "obligations":
            # Obligations command doesn't require any specific parameters
            pass
        
        elif command_type == "total_supply":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
        
        elif command_type == "mint":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            amount = parse_yaml(yaml_file, f".commands[{command_index}].parameters.amount")
            policy_secret = parse_yaml(yaml_file, f".commands[{command_index}].parameters.policy_secret")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not amount:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.amount' field")
                return False
            if not policy_secret:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.policy_secret' field")
                return False
        
        elif command_type == "burn":
            denomination = parse_yaml(yaml_file, f".commands[{command_index}].parameters.denomination")
            amount = parse_yaml(yaml_file, f".commands[{command_index}].parameters.amount")
            policy_secret = parse_yaml(yaml_file, f".commands[{command_index}].parameters.policy_secret")
            
            if not denomination:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.denomination' field")
                return False
            if not amount:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.amount' field")
                return False
            if not policy_secret:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.policy_secret' field")
                return False
        
        elif command_type == "create_obligation_swap":
            swap_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.swap_id")
            counterparty = parse_yaml(yaml_file, f".commands[{command_index}].parameters.counterparty")
            obligation_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.obligation_id")
            deadline = parse_yaml(yaml_file, f".commands[{command_index}].parameters.deadline")
            
            if not swap_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.swap_id' field")
                return False
            if not counterparty:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.counterparty' field")
                return False
            if not obligation_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.obligation_id' field")
                return False
            if not deadline:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.deadline' field")
                return False
        
        elif command_type == "create_payment_swap":
            swap_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.swap_id")
            counterparty = parse_yaml(yaml_file, f".commands[{command_index}].parameters.counterparty")
            deadline = parse_yaml(yaml_file, f".commands[{command_index}].parameters.deadline")
            
            if not swap_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.swap_id' field")
                return False
            if not counterparty:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.counterparty' field")
                return False
            if not deadline:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.deadline' field")
                return False
        
        elif command_type == "complete_swap":
            swap_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.swap_id")
            
            if not swap_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.swap_id' field")
                return False
        
        elif command_type == "cancel_swap":
            swap_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.swap_id")
            key = parse_yaml(yaml_file, f".commands[{command_index}].parameters.key")
            value = parse_yaml(yaml_file, f".commands[{command_index}].parameters.value")
            
            if not swap_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.swap_id' field")
                return False
            if not key:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.key' field")
                return False
            if not value:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.value' field")
                return False
        
        elif command_type == "list_groups":
            # list_groups doesn't require any specific parameters
            pass
        
        elif command_type == "create_swap":
            swap_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.swap_id")
            counterparty_id = parse_yaml(yaml_file, f".commands[{command_index}].parameters.counterparty.id")
            deadline = parse_yaml(yaml_file, f".commands[{command_index}].parameters.deadline")
            
            if not swap_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.swap_id' field")
                return False
            if not counterparty_id:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.counterparty.id' field")
                return False
            if not deadline:
                echo_with_color(Colors.RED, f"Error: Command '{command_name}' missing 'parameters.deadline' field")
                return False
        
        else:
            echo_with_color(Colors.RED, f"Error: Command '{command_name}' has unsupported type: '{command_type}'")
            echo_with_color(Colors.YELLOW, "Supported types: deposit, withdraw, instant, accept, balance, create_obligation, accept_obligation, transfer_obligation, cancel_obligation, obligations, total_supply, mint, burn, create_obligation_swap, create_payment_swap, create_swap, complete_swap, cancel_swap, list_groups")
            return False
        
        return True
    
    def show_commands_status(self, yaml_file: str) -> bool:
        """Show commands execution status and requirements."""
        echo_with_color(Colors.CYAN, "YieldFabric GraphQL Commands Execution Status")
        echo_with_color(Colors.CYAN, "=====================================================")
        
        # Check services
        echo_with_color(Colors.BLUE, "Service Status:")
        if check_service_running("Auth Service", self.auth_service_url):
            echo_with_color(Colors.GREEN, f"   Auth Service ({self.auth_service_url}) - Running")
        else:
            echo_with_color(Colors.RED, f"   Auth Service ({self.auth_service_url}) - Not running")
            echo_with_color(Colors.YELLOW, "   Start the auth service first: cd ../yieldfabric-auth && cargo run")
            return False
        
        if check_service_running("Payments Service", self.pay_service_url):
            echo_with_color(Colors.GREEN, f"   Payments Service ({self.pay_service_url}) - Running")
            echo_with_color(Colors.BLUE, f"   GraphQL endpoint available at: {self.pay_service_url}/graphql")
        else:
            echo_with_color(Colors.RED, f"   Payments Service ({self.pay_service_url}) - Not running")
            echo_with_color(Colors.YELLOW, "   Start the payments service first: cd ../yieldfabric-payments && cargo run")
            return False
        
        # Check commands file
        echo_with_color(Colors.BLUE, "Commands File:")
        if os.path.exists(yaml_file):
            echo_with_color(Colors.GREEN, f"   {yaml_file} - Found")
            
            if check_yq_available():
                command_count = parse_yaml(yaml_file, '.commands | length')
                echo_with_color(Colors.BLUE, f"   Commands defined: {command_count}")
                
                # Show command details
                for i in range(int(command_count or 0)):
                    command_name = parse_yaml(yaml_file, f".commands[{i}].name")
                    command_type = parse_yaml(yaml_file, f".commands[{i}].type")
                    user_id = parse_yaml(yaml_file, f".commands[{i}].user.id")
                    echo_with_color(Colors.BLUE, f"   Command {i+1}: '{command_name}' ({command_type}) - User: {user_id}")
            else:
                echo_with_color(Colors.YELLOW, "   yq not available - cannot parse YAML")
        else:
            echo_with_color(Colors.RED, f"   {yaml_file} - Not found")
            return False
        
        # Check yq availability
        echo_with_color(Colors.BLUE, "YAML Parser:")
        if check_yq_available():
            echo_with_color(Colors.GREEN, "   yq - Available")
        else:
            echo_with_color(Colors.RED, "   yq - Not available")
            echo_with_color(Colors.YELLOW, "   Install yq: brew install yq (macOS) or see https://github.com/mikefarah/yq")
            return False
        
        return True


# Global command validator instance
command_validator = CommandValidator()
