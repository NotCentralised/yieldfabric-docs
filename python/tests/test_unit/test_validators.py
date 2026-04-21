"""Unit tests for yieldfabric.utils.validators."""

from yieldfabric.utils.validators import coerce_null, is_provided


# ---- is_provided --------------------------------------------------------


def test_is_provided_rejects_none():
    assert is_provided(None) is False


def test_is_provided_rejects_empty_string():
    assert is_provided("") is False


def test_is_provided_rejects_whitespace_only():
    # Whitespace-only is treated as "not provided" — matches shell YAML
    # convention where empty fields often come through as bare spaces.
    assert is_provided("   ") is False
    assert is_provided("\t\n") is False


def test_is_provided_rejects_shell_null_sentinels():
    # These come through from the shell harness / yq handling.
    assert is_provided("null") is False
    assert is_provided("None") is False
    assert is_provided("NONE") is False


def test_is_provided_accepts_meaningful_strings():
    assert is_provided("value") is True
    assert is_provided("0") is True  # zero-as-string IS a user value
    assert is_provided("false") is True  # string "false" is not a sentinel
    assert is_provided("NULL  ") is True  # different casing is not "null"
    assert is_provided(" x ") is True   # surrounding whitespace is stripped


def test_is_provided_accepts_non_string_truthy():
    # Non-strings only check for not-None; 0/False/[] are callers'
    # problem if they're using is_provided on them.
    assert is_provided(0) is True
    assert is_provided(False) is True  # non-string, not None → provided
    assert is_provided({}) is True
    assert is_provided([]) is True


# ---- coerce_null --------------------------------------------------------


def test_coerce_null_returns_none_for_sentinels():
    assert coerce_null(None) is None
    assert coerce_null("") is None
    assert coerce_null("null") is None
    assert coerce_null("None") is None
    assert coerce_null("NONE") is None
    assert coerce_null("  ") is None


def test_coerce_null_passthrough_for_real_values():
    assert coerce_null("real") == "real"
    assert coerce_null("0") == "0"
    assert coerce_null(42) == 42
    # Non-string falsy values pass through (not in the sentinel set).
    assert coerce_null(0) == 0
