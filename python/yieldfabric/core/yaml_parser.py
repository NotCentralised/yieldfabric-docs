"""
YAML parser for YieldFabric commands
"""

import json
import re
from typing import Any, List, Optional
import yaml

from ..models import Command
from ..utils.logger import get_logger


class YAMLParser:
    """Parser for YAML command files."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize YAML parser.
        
        Args:
            debug: Enable debug logging
        """
        self.logger = get_logger(debug=debug)
    
    def parse_file(self, yaml_file: str) -> List[Command]:
        """
        Parse a YAML file and return list of commands.
        
        Args:
            yaml_file: Path to YAML file
            
        Returns:
            List of Command objects
        """
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            commands = []
            if 'commands' in data and isinstance(data['commands'], list):
                for cmd_data in data['commands']:
                    try:
                        command = Command.from_dict(cmd_data)
                        commands.append(command)
                    except Exception as e:
                        self.logger.error(f"Failed to parse command: {e}")
                        self.logger.debug(f"Command data: {cmd_data}")
            
            return commands
        
        except FileNotFoundError:
            self.logger.error(f"YAML file not found: {yaml_file}")
            return []
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error parsing YAML: {e}")
            return []
    
    def query(self, yaml_file: str, query_path: str) -> Optional[Any]:
        """
        Query a YAML file using a simple path notation.
        
        Supports:
        - ".commands[0].name" - access array by index
        - ".commands | length" - get array length
        - ".users[] | select(.id == 'email') | .password" - filter and select
        
        Args:
            yaml_file: Path to YAML file
            query_path: Query path (yq-like syntax)
            
        Returns:
            Query result or None
        """
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Handle special queries
            if ' | length' in query_path:
                base_path = query_path.split(' | length')[0].strip()
                value = self._navigate_path(data, base_path)
                if isinstance(value, list):
                    return len(value)
                return 0
            
            # Handle select queries
            if ' | select(' in query_path:
                return self._handle_select_query(data, query_path)
            
            # Handle simple path navigation
            return self._navigate_path(data, query_path)
        
        except FileNotFoundError:
            self.logger.error(f"YAML file not found: {yaml_file}")
            return None
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Query error for '{query_path}': {e}")
            return None
    
    def _navigate_path(self, data: Any, path: str) -> Optional[Any]:
        """Navigate through data using dot notation path."""
        if path.startswith('.'):
            path = path[1:]
        
        if not path:
            return data
        
        current = data
        
        # Parse path elements
        elements = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)(?:\[(\d+)\])?', path)
        
        for element, index in elements:
            if isinstance(current, dict) and element in current:
                current = current[element]
                if index:
                    idx = int(index)
                    if isinstance(current, list) and 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
            else:
                return None
        
        return current
    
    def _handle_select_query(self, data: Any, query: str) -> Optional[Any]:
        """Handle select-style queries."""
        # Parse query like: ".users[] | select(.id == 'email') | .password"
        parts = query.split(' | ')
        
        if len(parts) < 3:
            return None
        
        # Get base path and convert to list
        base_path = parts[0].replace('[]', '').strip()
        items = self._navigate_path(data, base_path)
        
        if not isinstance(items, list):
            return None
        
        # Parse select condition
        select_part = parts[1].strip()
        match = re.search(r'select\(\.([a-zA-Z_][a-zA-Z0-9_]*)\s*==\s*["\']([^"\']+)["\']\)', select_part)
        
        if not match:
            return None
        
        field = match.group(1)
        value = match.group(2)
        
        # Filter items
        filtered = [item for item in items if isinstance(item, dict) and item.get(field) == value]
        
        if not filtered:
            return None
        
        # Get final field from first match
        final_path = parts[2].strip()
        return self._navigate_path(filtered[0], final_path)
    
    def get_command_count(self, yaml_file: str) -> int:
        """Get number of commands in YAML file."""
        count = self.query(yaml_file, '.commands | length')
        return int(count) if count is not None else 0
    
    def get_command_at_index(self, yaml_file: str, index: int) -> Optional[Command]:
        """Get command at specific index."""
        commands = self.parse_file(yaml_file)
        if 0 <= index < len(commands):
            return commands[index]
        return None
    
    def validate_structure(self, yaml_file: str) -> bool:
        """Validate YAML file structure."""
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                self.logger.error("YAML root must be a dictionary")
                return False
            
            if 'commands' not in data:
                self.logger.error("YAML must have 'commands' key")
                return False
            
            if not isinstance(data['commands'], list):
                self.logger.error("'commands' must be a list")
                return False
            
            if len(data['commands']) == 0:
                self.logger.warning("No commands found in YAML file")
                return True
            
            # Validate each command
            for i, cmd in enumerate(data['commands']):
                if not isinstance(cmd, dict):
                    self.logger.error(f"Command {i} must be a dictionary")
                    return False
                
                required_fields = ['name', 'type', 'user', 'parameters']
                for field in required_fields:
                    if field not in cmd:
                        self.logger.error(f"Command {i} missing required field: {field}")
                        return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

