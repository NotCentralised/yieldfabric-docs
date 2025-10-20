"""
YAML file validator
"""

from typing import List, Tuple

from ..core.yaml_parser import YAMLParser
from ..utils.logger import get_logger


class YAMLValidator:
    """Validator for YAML command files."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize validator.
        
        Args:
            debug: Enable debug logging
        """
        self.logger = get_logger(debug=debug)
        self.parser = YAMLParser(debug=debug)
    
    def validate(self, yaml_file: str) -> Tuple[bool, List[str]]:
        """
        Validate YAML file structure and content.
        
        Args:
            yaml_file: Path to YAML file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check file structure
        if not self.parser.validate_structure(yaml_file):
            errors.append("Invalid YAML structure")
            return (False, errors)
        
        # Parse commands
        commands = self.parser.parse_file(yaml_file)
        
        if not commands:
            errors.append("No valid commands found in YAML file")
            return (False, errors)
        
        # Validate each command
        for i, command in enumerate(commands):
            command_errors = self._validate_command(command, i)
            errors.extend(command_errors)
        
        is_valid = len(errors) == 0
        return (is_valid, errors)
    
    def _validate_command(self, command, index: int) -> List[str]:
        """Validate a single command."""
        errors = []
        
        # Basic validation is handled by Command model
        # Additional validation can be added here
        
        return errors

