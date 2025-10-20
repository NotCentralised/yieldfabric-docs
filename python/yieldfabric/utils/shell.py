"""
Shell command utilities
"""

import subprocess
from typing import Optional


def evaluate_shell_command(command: str) -> Optional[str]:
    """
    Evaluate a shell command and return its output.
    
    Args:
        command: Shell command to evaluate
        
    Returns:
        Command output as string, or None if execution fails
    """
    try:
        result = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.PIPE
        )
        return result.strip()
    except subprocess.CalledProcessError as e:
        return None
    except Exception as e:
        return None


def is_shell_command(value: str) -> bool:
    """
    Check if a string appears to be a shell command substitution.
    
    Args:
        value: String to check
        
    Returns:
        True if value looks like a shell command (e.g., "$(date +%s)")
    """
    return isinstance(value, str) and value.startswith('$(') and value.endswith(')')


def extract_shell_command(value: str) -> Optional[str]:
    """
    Extract shell command from substitution syntax.
    
    Args:
        value: String in format "$(command)"
        
    Returns:
        Extracted command without $() wrapper, or None if invalid format
    """
    if is_shell_command(value):
        return value[2:-1]  # Remove "$(" and ")"
    return None

