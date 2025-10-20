"""
Core runner class for YieldFabric
"""

import time
from typing import List, Optional

from ..config import YieldFabricConfig
from ..models import Command, CommandResponse
from ..services import AuthService, PaymentsService
from ..executors import (
    PaymentExecutor,
    ObligationExecutor,
    QueryExecutor,
    SwapExecutor,
    TreasuryExecutor
)
from ..validation import YAMLValidator, ServiceValidator
from ..core.output_store import OutputStore
from ..core.yaml_parser import YAMLParser
from ..utils.logger import get_logger


class YieldFabricRunner:
    """Main runner class for executing YieldFabric commands."""
    
    def __init__(self, config: Optional[YieldFabricConfig] = None):
        """
        Initialize runner.
        
        Args:
            config: Optional configuration object. If None, creates from environment.
        """
        self.config = config or YieldFabricConfig.from_env()
        self.logger = get_logger(debug=self.config.debug)
        
        # Initialize services
        self.auth_service = AuthService(self.config)
        self.payments_service = PaymentsService(self.config)
        
        # Initialize core components
        self.output_store = OutputStore(debug=self.config.debug)
        self.yaml_parser = YAMLParser(debug=self.config.debug)
        
        # Initialize executors
        self.payment_executor = PaymentExecutor(
            self.auth_service, self.payments_service,
            self.output_store, self.config
        )
        self.obligation_executor = ObligationExecutor(
            self.auth_service, self.payments_service,
            self.output_store, self.config
        )
        self.query_executor = QueryExecutor(
            self.auth_service, self.payments_service,
            self.output_store, self.config
        )
        self.swap_executor = SwapExecutor(
            self.auth_service, self.payments_service,
            self.output_store, self.config
        )
        self.treasury_executor = TreasuryExecutor(
            self.auth_service, self.payments_service,
            self.output_store, self.config
        )
        
        # Initialize validators
        self.yaml_validator = YAMLValidator(debug=self.config.debug)
        self.service_validator = ServiceValidator(
            self.auth_service, self.payments_service,
            debug=self.config.debug
        )
    
    def execute_file(self, yaml_file: str) -> bool:
        """
        Execute all commands from a YAML file.
        
        Args:
            yaml_file: Path to YAML file
            
        Returns:
            True if all commands executed successfully
        """
        self.logger.cyan("🚀 Executing all commands from YAML file...")
        self.logger.separator()
        
        # Validate YAML structure
        is_valid, errors = self.yaml_validator.validate(yaml_file)
        if not is_valid:
            self.logger.error("❌ YAML validation failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False
        
        # Validate services
        if not self.service_validator.validate_services():
            return False
        
        # Parse commands
        commands = self.yaml_parser.parse_file(yaml_file)
        
        if not commands:
            self.logger.error("❌ No commands found in YAML file")
            return False
        
        self.logger.success(f"✅ Found {len(commands)} commands to execute")
        self.logger.separator()
        
        # Execute commands
        success_count = 0
        total_count = len(commands)
        
        for i, command in enumerate(commands):
            self.logger.section(f"Command {i+1}/{total_count}: {command.name}")
            
            # Substitute variables in parameters
            substituted_params = self.output_store.substitute_params(command.parameters.to_dict())
            command.parameters = type(command.parameters).from_dict(substituted_params)
            
            # Execute command
            response = self.execute_command(command)
            
            if response.success:
                success_count += 1
            
            self.logger.separator()
            
            # Wait between commands (except for the last one)
            if i + 1 < total_count:
                self.logger.waiting(self.config.command_delay)
                time.sleep(self.config.command_delay)
        
        # Summary
        self.logger.section("Execution Summary")
        self.logger.info(f"Total commands: {total_count}")
        self.logger.success(f"Successful: {success_count}")
        
        if success_count < total_count:
            self.logger.error(f"Failed: {total_count - success_count}")
        
        if success_count == total_count:
            self.logger.success("✅ All commands executed successfully!")
            return True
        else:
            self.logger.warning("⚠️  Some commands failed")
            return False
    
    def execute_command(self, command: Command) -> CommandResponse:
        """
        Execute a single command.
        
        Args:
            command: Command to execute
            
        Returns:
            CommandResponse object
        """
        command_type = command.type.lower()
        
        # Route to appropriate executor
        if command_type in ["deposit", "withdraw", "instant", "accept"]:
            return self.payment_executor.execute(command)
        
        elif command_type in ["create_obligation", "accept_obligation",
                              "transfer_obligation", "cancel_obligation"]:
            return self.obligation_executor.execute(command)
        
        elif command_type in ["balance", "obligations", "list_groups"]:
            return self.query_executor.execute(command)
        
        elif command_type in ["create_swap", "create_obligation_swap",
                              "create_payment_swap", "complete_swap", "cancel_swap"]:
            return self.swap_executor.execute(command)
        
        elif command_type in ["mint", "burn", "total_supply"]:
            return self.treasury_executor.execute(command)
        
        else:
            self.logger.error(f"❌ Unknown command type: {command_type}")
            return CommandResponse.error_response(
                command.name, command.type,
                [f"Unknown command type: {command_type}"]
            )
    
    def show_status(self, yaml_file: str) -> bool:
        """
        Show status of commands and services.
        
        Args:
            yaml_file: Path to YAML file
            
        Returns:
            True if status check passed
        """
        self.logger.section("YieldFabric Status Check")
        
        # Check services
        self.logger.subsection("Service Status")
        services_ok = self.service_validator.validate_services()
        self.logger.separator()
        
        # Check YAML file
        self.logger.subsection("YAML File Status")
        is_valid, errors = self.yaml_validator.validate(yaml_file)
        
        if is_valid:
            commands = self.yaml_parser.parse_file(yaml_file)
            self.logger.success(f"✅ YAML file is valid")
            self.logger.info(f"   Found {len(commands)} commands")
            
            for i, command in enumerate(commands):
                self.logger.info(f"   {i+1}. {command.name} ({command.type})")
        else:
            self.logger.error("❌ YAML file has errors:")
            for error in errors:
                self.logger.error(f"  - {error}")
        
        self.logger.separator()
        
        return services_ok and is_valid
    
    def close(self):
        """Close service connections."""
        self.auth_service.close()
        self.payments_service.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

