"""
Ethereum-compatible key generation and signing helpers.

Ports `loan_management/modules/register_external_key.py` (the pure parts):

  - `generate_ethereum_key()` — create a new secp256k1 key pair.
  - `address_from_private_key()` — derive address from hex private key.
  - `ownership_message()` — format the string used for external-key
    registration; must match the frontend exactly so the backend
    accepts the ecrecover result.
  - `sign_ownership_message()` — personal_sign over `ownership_message`.
  - `sign_message_hash()` — personal_sign over a raw 32-byte hash;
    used by the manual-signature flow to sign an unsigned transaction
    produced by the backend.

All functions require `eth_account` at runtime (via eth_account.Account
and eth_account.messages.encode_defunct). The dependency is optional in
requirements.txt; if not installed, calls raise a clear RuntimeError.
"""

import time
from typing import Tuple

# eth-account is an optional dependency. Import lazily and give a
# helpful error message if the caller tries to use these helpers
# without having installed it.
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    _HAS_ETH_ACCOUNT = True
except ImportError:
    _HAS_ETH_ACCOUNT = False


_INSTALL_MSG = "eth_account is required for key/signature operations. Install with: pip install eth-account"


def _require_eth_account():
    if not _HAS_ETH_ACCOUNT:
        raise RuntimeError(_INSTALL_MSG)


# ----------------------------------------------------------------------

def generate_ethereum_key() -> Tuple[str, str]:
    """
    Generate a new Ethereum (secp256k1) key pair.

    Returns:
        (private_key_hex, address)
        - private_key_hex: 32-byte hex, no 0x prefix.
        - address: 0x-prefixed, checksummed address.
    """
    _require_eth_account()
    acct = Account.create()
    # acct.key.hex() may or may not include the 0x prefix depending on
    # eth-account version. Normalize to without-prefix for storage.
    priv_hex = acct.key.hex()
    if priv_hex.startswith("0x"):
        priv_hex = priv_hex[2:]
    return priv_hex, acct.address


def address_from_private_key(private_key_hex: str) -> str:
    """
    Derive the Ethereum address from a private key hex string (with or
    without 0x prefix).
    """
    _require_eth_account()
    key = private_key_hex.removeprefix("0x").strip()
    if not key:
        raise ValueError("private_key_hex is empty")
    acct = Account.from_key(key)
    return acct.address


# ----------------------------------------------------------------------
# Ownership message — MUST match the frontend's keysService.registerMetaMaskKey
# format character-for-character, otherwise ecrecover in the backend returns
# a different signer address than the one we claim ownership of.
# ----------------------------------------------------------------------

def ownership_message(address: str) -> str:
    """
    Standard ownership-proof message the backend expects for external
    key registration. The timestamp is in milliseconds to match the
    JavaScript `Date.now()` convention used by the frontend.
    """
    return (
        "Sign this message to prove ownership of your MetaMask wallet "
        "for YieldFabric key registration.\n\n"
        f"Account: {address}\n"
        f"Timestamp: {int(time.time() * 1000)}"
    )


def sign_ownership_message(address: str, private_key_hex: str) -> Tuple[str, str]:
    """
    personal_sign the ownership message for the given address. Returns
    `(message_text, signature_hex)` where signature_hex is 130 hex
    chars (65 bytes of r+s+v), no 0x prefix — the backend expects this
    shape for POST /keys/external/verify-ownership.

    Raises ValueError if the private key doesn't match the address.
    """
    _require_eth_account()
    key = private_key_hex.removeprefix("0x").strip()
    acct = Account.from_key(key)
    if acct.address.lower() != address.lower():
        raise ValueError("private key does not match the given address")

    message_text = ownership_message(address)
    message = encode_defunct(text=message_text)
    signed = acct.sign_message(message)
    sig_hex = signed.signature.hex()
    if sig_hex.startswith("0x"):
        sig_hex = sig_hex[2:]
    return message_text, sig_hex


def sign_message_hash(private_key_hex: str, message_hash_hex: str) -> str:
    """
    personal_sign a raw 32-byte hash.

    Used by the manual-signature flow: the backend emits an unsigned
    transaction whose `message_hash` is a 32-byte digest; the smart
    contract recovers the signer with
    `ecrecover(keccak256("\\x19Ethereum Signed Message:\\n32" || hash))`,
    so we sign the digest of that prefixed hash. `encode_defunct` with
    `primitive=<32 bytes>` applies that exact prefix.

    Returns 130 hex chars (65-byte r+s+v), no 0x prefix.
    """
    _require_eth_account()
    key = private_key_hex.removeprefix("0x").strip()
    acct = Account.from_key(key)

    msg_hex = (message_hash_hex or "").strip().removeprefix("0x").strip()
    if not msg_hex:
        raise ValueError("message_hash_hex is required")
    hash_bytes = bytes.fromhex(msg_hex)
    if len(hash_bytes) != 32:
        raise ValueError(f"message_hash must be 32 bytes, got {len(hash_bytes)}")

    message = encode_defunct(primitive=hash_bytes)
    signed = acct.sign_message(message)
    sig_hex = signed.signature.hex()
    if sig_hex.startswith("0x"):
        sig_hex = sig_hex[2:]
    return sig_hex
