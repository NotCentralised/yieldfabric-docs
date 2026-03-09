"""Console output: colors and colored echo."""

import sys

# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
PURPLE = "\033[0;35m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color


def echo_with_color(color: str, message: str, file=sys.stdout) -> None:
    """Print a colored message."""
    print(f"{color}{message}{NC}", file=file)
