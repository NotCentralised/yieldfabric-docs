"""
YieldFabric Script Utilities
Contains common utility functions used across all modules.
"""

import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import yaml
import requests
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def echo_with_color(color: str, message: str) -> None:
    """Print a message with color formatting."""
    print(f"{color}{message}{Colors.NC}")


def check_service_running(service_name: str, service_url: str) -> bool:
    """Check if a service is running at the given URL."""
    try:
        # Try health endpoint first, then root
        health_urls = [f"{service_url}/health", service_url]
        for url in health_urls:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 404]:  # 404 is ok for root endpoint
                return True
    except (requests.RequestException, requests.Timeout):
        pass
    
    # Legacy: port-based check for localhost
    if not service_url.startswith(('http://', 'https://')):
        try:
            import socket
            host, port = 'localhost', int(service_url)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except (ValueError, socket.error):
            pass
    
    return False


def check_yq_available() -> bool:
    """Check if yq is available for YAML parsing."""
    try:
        subprocess.run(['yq', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def parse_yaml(yaml_file: str, query: str) -> Optional[str]:
    """Parse YAML using yq command line tool."""
    if not check_yq_available():
        echo_with_color(Colors.RED, "yq is required for YAML parsing but not installed")
        echo_with_color(Colors.YELLOW, "Install yq: brew install yq (macOS) or see https://github.com/mikefarah/yq")
        return None
    
    try:
        result = subprocess.run(
            ['yq', 'eval', query, yaml_file],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def parse_yaml_python(yaml_file: str) -> Dict[str, Any]:
    """Parse YAML file using Python yaml library."""
    try:
        with open(yaml_file, 'r') as file:
            return yaml.safe_load(file)
    except (FileNotFoundError, yaml.YAMLError) as e:
        echo_with_color(Colors.RED, f"Error parsing YAML file {yaml_file}: {e}")
        return {}


class CommandOutputStore:
    """Store and retrieve command outputs for variable substitution."""
    
    def __init__(self):
        self.outputs: Dict[str, str] = {}
    
    def store_command_output(self, command_name: str, field_name: str, value: str) -> None:
        """Store a command output value."""
        key = f"{command_name}_{field_name}"
        self.outputs[key] = value
    
    def get_command_output(self, command_name: str, field_name: str) -> Optional[str]:
        """Retrieve a stored command output value."""
        key = f"{command_name}_{field_name}"
        return self.outputs.get(key)
    
    def substitute_variables(self, value: str) -> str:
        """Substitute variables in command parameters."""
        if not value:
            return value
        
        # Handle shell command substitution
        if '$(date +%s)' in value:
            try:
                result = subprocess.run(['date', '+%s'], capture_output=True, text=True, check=True)
                evaluated_value = result.stdout.strip()
                echo_with_color(Colors.CYAN, f"    🔄 Substituting {value} -> {evaluated_value}")
                return evaluated_value
            except subprocess.CalledProcessError:
                return value
        
        # Handle JSON arrays with variable references
        if value.startswith('[') and value.endswith(']') and '$' in value:
            result = value
            # Find all variable references in the JSON array
            pattern = r'\$[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*'
            matches = re.findall(pattern, result)
            
            for var_ref in matches:
                command_name, field_name = var_ref[1:].split('.', 1)
                stored_value = self.get_command_output(command_name, field_name)
                if stored_value:
                    echo_with_color(Colors.CYAN, f"    🔄 Substituting {var_ref} -> {stored_value} in JSON array")
                    result = result.replace(var_ref, stored_value)
                else:
                    echo_with_color(Colors.YELLOW, f"    ⚠️  Variable {var_ref} not found in stored outputs")
                    break
            
            return result
        
        # Handle single variable references
        pattern = r'\$[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*'
        match = re.search(pattern, value)
        if match:
            var_ref = match.group(0)
            command_name, field_name = var_ref[1:].split('.', 1)
            stored_value = self.get_command_output(command_name, field_name)
            if stored_value:
                echo_with_color(Colors.CYAN, f"    🔄 Substituting {value} -> {stored_value}")
                return stored_value
            else:
                echo_with_color(Colors.YELLOW, f"    ⚠️  Variable {value} not found in stored outputs")
        
        return value
    
    def debug_show_variables(self) -> None:
        """Debug function to show all stored variables."""
        echo_with_color(Colors.PURPLE, "🔍 Debug: All stored variables:")
        for key, value in self.outputs.items():
            echo_with_color(Colors.BLUE, f"  {key} = {value}")


# Global command output store instance
command_output_store = CommandOutputStore()
