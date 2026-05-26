"""
Minimal .env loader — zero external dependencies.

The shell harness (`setup_system.sh`) loads its config via `source .env`.
We mirror that for the Python CLI without taking a hard dependency on
python-dotenv: parse a small KEY=VALUE file and inject any keys that
aren't already set in the process environment.

Supported syntax (deliberately small — this is config, not a shell):
  - `KEY=VALUE` lines.
  - Blank lines and `#` comments ignored.
  - A leading `export ` prefix is stripped (so a file that doubles as a
    shell `source` target still works).
  - Surrounding single or double quotes on VALUE are stripped.
  - Inline trailing comments are NOT parsed (a `#` inside an unquoted
    value is kept verbatim) — keep secrets unquoted-and-clean or quote them.
"""

import os
from typing import Optional


def parse_dotenv(text: str) -> dict:
    """Parse .env file contents into a {KEY: VALUE} dict."""
    out: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


def load_dotenv(path: Optional[str] = None, *, override: bool = False) -> dict:
    """
    Load environment variables from a .env file into os.environ.

    Args:
        path: Explicit path to a .env file. If given and the file is
            missing, raises FileNotFoundError (an explicit request that
            can't be satisfied is an error). If None, look for ./.env and
            silently no-op when it's absent.
        override: When False (default), keys already present in the
            process environment are left untouched — real env wins over
            the file. When True, the file overrides.

    Returns:
        The dict of keys that were actually applied to os.environ.
    """
    if path is None:
        candidate = os.path.join(os.getcwd(), ".env")
        if not os.path.isfile(candidate):
            return {}
        path = candidate
    elif not os.path.isfile(path):
        raise FileNotFoundError(f".env file not found: {path}")

    with open(path, "r") as fh:
        parsed = parse_dotenv(fh.read())

    applied: dict = {}
    for key, value in parsed.items():
        if not override and key in os.environ:
            continue
        os.environ[key] = value
        applied[key] = value
    return applied
