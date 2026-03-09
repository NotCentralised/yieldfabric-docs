"""Configuration: action modes, env loading, boolean env parsing."""

import os
from pathlib import Path

from .console import YELLOW, echo_with_color

# Action modes
ACTION_ISSUE_ONLY = "issue_only"
ACTION_ISSUE_SWAP = "issue_swap"
ACTION_ISSUE_SWAP_COMPLETE = "issue_swap_complete"
VALID_ACTION_MODES = (ACTION_ISSUE_ONLY, ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE)


def parse_bool_env(key: str, default: bool = False) -> bool:
    """Return True if env key is true/1/yes (case-insensitive)."""
    return os.environ.get(key, "").strip().lower() in ("true", "1", "yes")


def parse_bool_env_with_mode_default(
    key: str,
    action_mode: str,
    default_for_swap_complete: bool,
) -> bool:
    """Parse bool env; if unset and action_mode is issue_swap_complete, use default_for_swap_complete."""
    raw = os.environ.get(key, "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    if action_mode == ACTION_ISSUE_SWAP_COMPLETE:
        return default_for_swap_complete
    return False


def load_env_files(script_dir: Path, repo_root: Path) -> None:
    """Load environment variables from .env files."""
    env_files = [
        repo_root / ".env",
        repo_root / ".env.local",
        script_dir / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            value = value.strip("\"'").strip()
                            os.environ[key.strip()] = value
            except Exception as e:
                echo_with_color(YELLOW, f"  ⚠️  Warning: Could not load {env_file}: {e}")
