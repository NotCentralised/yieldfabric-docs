"""
Output store for variable substitution
"""

import json
import re
from typing import Any, Dict, Optional

from ..utils.logger import get_logger
from ..utils.shell import is_shell_command, extract_shell_command, evaluate_shell_command


class OutputStore:
    """Store and retrieve command outputs for variable substitution."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize output store.
        
        Args:
            debug: Enable debug logging
        """
        self._storage: Dict[str, Any] = {}
        self.logger = get_logger(debug=debug)
    
    def store(self, command_name: str, field_name: str, value: Any):
        """
        Store a command output value.
        
        Args:
            command_name: Name of the command
            field_name: Name of the field
            value: Value to store
        """
        key = f"{command_name}_{field_name}"
        self._storage[key] = value
        self.logger.stored_output(command_name, field_name, str(value))
    
    def get(self, command_name: str, field_name: str) -> Optional[Any]:
        """
        Retrieve a stored command output value.
        
        Args:
            command_name: Name of the command
            field_name: Name of the field
            
        Returns:
            Stored value or None if not found
        """
        key = f"{command_name}_{field_name}"
        value = self._storage.get(key)
        self.logger.debug(f"🔍 DEBUG: Retrieved {key} = {value}")
        return value
    
    def clear(self):
        """Clear all stored values."""
        self._storage.clear()
        self.logger.debug("🔍 DEBUG: Output store cleared")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all stored values."""
        return self._storage.copy()
    
    def substitute(self, value: Any) -> Any:
        """
        Substitute variables in a value.
        
        Supports:
        - Single variable: "$command_name.field_name"
        - String with embedded variables: "text $var1.field text"
        - Shell commands: "$(date +%s)"
        - JSON arrays/objects with variables
        
        Args:
            value: Value to substitute
            
        Returns:
            Value with substitutions applied
        """
        if not isinstance(value, str):
            return value
        
        # Handle shell command substitution
        if is_shell_command(value):
            shell_cmd = extract_shell_command(value)
            if shell_cmd:
                result = evaluate_shell_command(shell_cmd)
                if result is not None:
                    self.logger.substitution(value, result)
                    return result
                else:
                    self.logger.warning(f"    ⚠️  Shell command failed: {value}")
                    return value
        
        # Handle JSON array with variable references
        if value.startswith('[') and value.endswith(']') and '$' in value:
            try:
                json_array = json.loads(value)
                if isinstance(json_array, list):
                    substituted_array = self._substitute_list(json_array)
                    result = json.dumps(substituted_array)
                    self.logger.substitution(value, result)
                    return result
            except json.JSONDecodeError:
                pass  # Not valid JSON, proceed with string substitution
        
        # Handle JSON object with variable references
        if value.startswith('{') and value.endswith('}') and '$' in value:
            try:
                json_obj = json.loads(value)
                if isinstance(json_obj, dict):
                    substituted_obj = self._substitute_dict(json_obj)
                    result = json.dumps(substituted_obj)
                    self.logger.substitution(value, result)
                    return result
            except json.JSONDecodeError:
                pass  # Not valid JSON, proceed with string substitution
        
        # Handle single variable or string with embedded variables
        pattern = r'\$([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
        
        def replace_var(match):
            command_name = match.group(1)
            field_name = match.group(2)
            var_ref = f"${command_name}.{field_name}"
            
            stored_value = self.get(command_name, field_name)
            if stored_value is not None:
                self.logger.substitution(var_ref, str(stored_value))
                return str(stored_value)
            else:
                self.logger.warning(f"    ⚠️  Variable '{var_ref}' not found in stored outputs")
                return var_ref  # Return original if not found
        
        # Check if entire value is a single variable reference
        full_match = re.fullmatch(pattern, value)
        if full_match:
            command_name = full_match.group(1)
            field_name = full_match.group(2)
            stored_value = self.get(command_name, field_name)
            if stored_value is not None:
                self.logger.substitution(value, str(stored_value))
                return stored_value  # Return raw value (not stringified)
        
        # Replace all variable references in string
        result = re.sub(pattern, replace_var, value)
        if result != value:
            self.logger.substitution(value, result)
        return result
    
    def _substitute_list(self, lst: list) -> list:
        """Recursively substitute variables in a list."""
        result = []
        for item in lst:
            if isinstance(item, str):
                result.append(self.substitute(item))
            elif isinstance(item, dict):
                result.append(self._substitute_dict(item))
            elif isinstance(item, list):
                result.append(self._substitute_list(item))
            else:
                result.append(item)
        return result
    
    def _substitute_dict(self, dct: dict) -> dict:
        """Recursively substitute variables in a dictionary."""
        result = {}
        for key, value in dct.items():
            if isinstance(value, str):
                result[key] = self.substitute(value)
            elif isinstance(value, dict):
                result[key] = self._substitute_dict(value)
            elif isinstance(value, list):
                result[key] = self._substitute_list(value)
            else:
                result[key] = value
        return result
    
    def substitute_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute variables in all parameter values.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Dictionary with substitutions applied
        """
        return self._substitute_dict(params)


# Global instance
_global_output_store: Optional[OutputStore] = None


def get_output_store(debug: bool = False) -> OutputStore:
    """Get or create global output store instance."""
    global _global_output_store
    if _global_output_store is None or _global_output_store.logger.debug_mode != debug:
        _global_output_store = OutputStore(debug=debug)
    return _global_output_store


def set_output_store(store: OutputStore):
    """Set global output store instance."""
    global _global_output_store
    _global_output_store = store

