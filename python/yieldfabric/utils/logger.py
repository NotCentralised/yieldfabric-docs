"""
Enhanced logging utility for YieldFabric
"""

import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""
    
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class YieldFabricLogger:
    """Enhanced logger with colored output and debug mode."""
    
    def __init__(self, debug: bool = False, colorize: bool = True):
        """
        Initialize logger.
        
        Args:
            debug: Enable debug logging
            colorize: Enable colored output
        """
        self.debug_mode = debug
        self.colorize = colorize
    
    def _print(self, color: str, message: str, file=None):
        """Print with optional color."""
        if file is None:
            file = sys.stdout
        
        if self.colorize:
            print(f"{color}{message}{Colors.NC}", file=file)
        else:
            print(message, file=file)
    
    def success(self, message: str):
        """Log success message in green."""
        self._print(Colors.GREEN, message)
    
    def error(self, message: str):
        """Log error message in red."""
        self._print(Colors.RED, message, file=sys.stderr)
    
    def warning(self, message: str):
        """Log warning message in yellow."""
        self._print(Colors.YELLOW, message)
    
    def info(self, message: str):
        """Log info message in blue."""
        self._print(Colors.BLUE, message)
    
    def debug(self, message: str):
        """Log debug message in purple (only if debug mode is enabled)."""
        if self.debug_mode:
            self._print(Colors.PURPLE, message)
    
    def cyan(self, message: str):
        """Log message in cyan."""
        self._print(Colors.CYAN, message)
    
    def section(self, title: str, char: str = "=", length: int = 80):
        """Log a section header."""
        self._print(Colors.CYAN, char * length)
        self._print(Colors.CYAN, title)
        self._print(Colors.CYAN, char * length)
    
    def subsection(self, title: str, char: str = "-", length: int = 60):
        """Log a subsection header."""
        self._print(Colors.BLUE, char * length)
        self._print(Colors.BLUE, title)
    
    def command_start(self, command_name: str, command_type: str):
        """Log command start."""
        self._print(Colors.PURPLE, f"🚀 Executing command: {command_name}")
        self._print(Colors.BLUE, f"  Type: {command_type}")
    
    def command_success(self, command_name: str):
        """Log command success."""
        self._print(Colors.GREEN, f"✅ Command {command_name} completed successfully")
    
    def command_failure(self, command_name: str):
        """Log command failure."""
        self._print(Colors.RED, f"❌ Command {command_name} failed")
    
    def parameter(self, name: str, value: str):
        """Log a parameter."""
        self._print(Colors.BLUE, f"  {name}: {value}")
    
    def stored_output(self, command_name: str, field_name: str, value: str):
        """Log stored output for variable substitution."""
        if self.debug_mode:
            self._print(Colors.PURPLE, f"🔍 DEBUG: Stored {command_name}_{field_name} = {value}")
    
    def substitution(self, original: str, substituted: str):
        """Log variable substitution."""
        if self.debug_mode:
            self._print(Colors.CYAN, f"  🔄 Substituting '{original}' -> '{substituted}'")
    
    def api_request(self, method: str, endpoint: str):
        """Log API request."""
        self._print(Colors.BLUE, f"  📤 {method} {endpoint}")
    
    def api_response(self, status_code: int, success: bool):
        """Log API response."""
        color = Colors.GREEN if success else Colors.RED
        symbol = "✅" if success else "❌"
        self._print(color, f"  📡 Response: {status_code} {symbol}")
    
    def waiting(self, seconds: int):
        """Log waiting message."""
        self._print(Colors.CYAN, f"⏳ Waiting {seconds} seconds before next command...")
    
    def separator(self, length: int = 80):
        """Log separator line."""
        self._print(Colors.CYAN, "")


# Global logger instance (can be configured)
_global_logger: Optional[YieldFabricLogger] = None


def get_logger(debug: bool = False, colorize: bool = True) -> YieldFabricLogger:
    """Get or create global logger instance."""
    global _global_logger
    if _global_logger is None or _global_logger.debug_mode != debug or _global_logger.colorize != colorize:
        _global_logger = YieldFabricLogger(debug=debug, colorize=colorize)
    return _global_logger


def set_logger(logger: YieldFabricLogger):
    """Set global logger instance."""
    global _global_logger
    _global_logger = logger

