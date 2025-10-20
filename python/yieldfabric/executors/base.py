"""
Base executor class
"""

from typing import Optional

from ..config import YieldFabricConfig
from ..models import Command, CommandResponse
from ..services import AuthService, PaymentsService
from ..core.output_store import OutputStore
from ..utils.logger import get_logger


class BaseExecutor:
    """Base class for command executors."""
    
    def __init__(self, auth_service: AuthService, payments_service: PaymentsService,
                 output_store: OutputStore, config: YieldFabricConfig):
        """
        Initialize executor.
        
        Args:
            auth_service: Auth service client
            payments_service: Payments service client
            output_store: Output store for variable substitution
            config: YieldFabric configuration
        """
        self.auth_service = auth_service
        self.payments_service = payments_service
        self.output_store = output_store
        self.config = config
        self.logger = get_logger(debug=config.debug)
    
    def execute(self, command: Command) -> CommandResponse:
        """
        Execute a command.
        
        Args:
            command: Command to execute
            
        Returns:
            CommandResponse object
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def get_token(self, command: Command) -> Optional[str]:
        """
        Get JWT token for user (with optional group delegation).
        
        Args:
            command: Command containing user information
            
        Returns:
            JWT token or None if authentication fails
        """
        user = command.user
        
        if user.group:
            # Login with group delegation
            return self.auth_service.login_with_group(user.id, user.password, user.group)
        else:
            # Regular login
            return self.auth_service.login(user.id, user.password)
    
    def store_outputs(self, command_name: str, data: dict):
        """
        Store command outputs for variable substitution.
        
        Args:
            command_name: Name of the command
            data: Dictionary of field names and values to store
        """
        for field_name, value in data.items():
            if value is not None:
                self.output_store.store(command_name, field_name, value)
    
    def log_command_start(self, command: Command):
        """Log command start."""
        self.logger.command_start(command.name, command.type)
        self.logger.info(f"  User: {command.user.id}")
        if command.user.group:
            self.logger.cyan(f"  Group: {command.user.group} (delegation)")
    
    def log_command_success(self, command: Command):
        """Log command success."""
        self.logger.command_success(command.name)
    
    def log_command_failure(self, command: Command):
        """Log command failure."""
        self.logger.command_failure(command.name)
    
    def log_parameters(self, params: dict):
        """Log command parameters."""
        self.logger.info("  Parameters after substitution:")
        for key, value in params.items():
            if value is not None and value != "" and value != "null":
                self.logger.parameter(key, str(value))

