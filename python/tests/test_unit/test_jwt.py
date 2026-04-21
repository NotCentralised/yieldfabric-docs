"""Unit tests for yieldfabric.utils.jwt."""

import base64
import json

from yieldfabric.utils.jwt import extract_claim, get_entity_id, get_sub


def _make_jwt(payload: dict) -> str:
    """
    Build a structurally-valid JWT for testing claim extraction.
    Signature is intentionally garbage — we never verify, we only
    decode the payload.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = "ignored-signature-bytes"
    return f"{header}.{body}.{sig}"


# ---- extract_claim ------------------------------------------------------


def test_extract_claim_returns_named_claim():
    token = _make_jwt({"sub": "user-123", "role": "Operator"})
    assert extract_claim(token, "sub") == "user-123"
    assert extract_claim(token, "role") == "Operator"


def test_extract_claim_prefers_first_non_empty_name():
    # acting_as present → win over sub.
    token = _make_jwt({"sub": "user-1", "acting_as": "group-9"})
    assert extract_claim(token, "acting_as", "sub") == "group-9"

    # acting_as absent → fall back to sub.
    token = _make_jwt({"sub": "user-1"})
    assert extract_claim(token, "acting_as", "sub") == "user-1"

    # acting_as present but empty string → still fall back.
    token = _make_jwt({"sub": "user-1", "acting_as": ""})
    assert extract_claim(token, "acting_as", "sub") == "user-1"


def test_extract_claim_returns_none_for_missing_claim():
    token = _make_jwt({"sub": "user-1"})
    assert extract_claim(token, "nope") is None


def test_extract_claim_rejects_malformed_tokens():
    assert extract_claim("", "sub") is None
    assert extract_claim("not-a-jwt", "sub") is None
    assert extract_claim("two.parts", "sub") is None
    # Four parts (no such thing as a JWT with 4 segments).
    assert extract_claim("a.b.c.d", "sub") is None
    # Valid 3 segments but payload isn't base64-json.
    assert extract_claim("aaa.not-base64.bbb", "sub") is None


def test_extract_claim_handles_padding_correctly():
    # JWT payloads omit base64 padding; ensure we re-add it.
    payload = {"sub": "padding-needed"}
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    # Confirm we built one that actually needs padding for decoding.
    assert len(raw) % 4 != 0, "test setup: expected a payload whose raw encoding is not a multiple of 4"
    token = f"x.{raw}.y"
    assert extract_claim(token, "sub") == "padding-needed"


def test_extract_claim_returns_none_for_non_object_payload():
    # Edge case: payload decodes but isn't a dict.
    body = base64.urlsafe_b64encode(b'"just a string"').rstrip(b"=").decode()
    token = f"h.{body}.s"
    assert extract_claim(token, "sub") is None


# ---- get_entity_id ------------------------------------------------------


def test_get_entity_id_prefers_acting_as():
    token = _make_jwt({"sub": "user-1", "acting_as": "group-2"})
    assert get_entity_id(token) == "group-2"


def test_get_entity_id_falls_back_to_sub():
    token = _make_jwt({"sub": "user-1"})
    assert get_entity_id(token) == "user-1"


def test_get_entity_id_returns_none_on_malformed():
    assert get_entity_id("nope") is None


def test_get_entity_id_ignores_non_string_claims():
    # If sub is a number (shouldn't happen in practice), we return None
    # rather than coercing.
    token = _make_jwt({"sub": 12345})
    assert get_entity_id(token) is None


# ---- get_sub ------------------------------------------------------------


def test_get_sub_returns_only_sub():
    # Unlike get_entity_id, get_sub ignores acting_as.
    token = _make_jwt({"sub": "user-1", "acting_as": "group-9"})
    assert get_sub(token) == "user-1"


def test_get_sub_returns_none_when_missing():
    token = _make_jwt({"acting_as": "group-only"})
    assert get_sub(token) is None
