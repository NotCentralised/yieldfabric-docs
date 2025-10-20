"""
Command parameter validator
"""

from typing import List, Tuple

from ..models import Command
from ..utils.logger import get_logger


class CommandValidator:
    """Validator for command parameters."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize validator.
        
        Args:
            debug: Enable debug logging
        """
        self.logger = get_logger(debug=debug)
    
    def validate_command(self, command: Command) -> Tuple[bool, List[str]]:
        """
        Validate command parameters.
        
        Args:
            command: Command to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        # Basic validation handled by models
        # Can be extended with specific validation logic
        return (True, [])

