"""
Register an external key with the YieldFabric auth service.

Mirrors the flow in yieldfabric-app:
- RegisterMetaMaskKeyModal / keysService.registerMetaMaskKey():
  1. (MetaMask: connect and get account; we generate a key instead)
  2. Build ownership message and sign it (Ethereum personal_sign format)
  3. Optionally verify ownership via POST /keys/external/verify-ownership
  4. Register via POST /keys/external

Usage:
  - Generate key and register in one go: generate_and_register_external_key(...)
  - Or use stepwise: generate_ethereum_key(), sign_ownership_message(), register_external_key()
"""

import time
from pathlib import Path
from typing import Any, List, Optional, Union

import requests

# Optional: eth_account for key generation and signing. Install with: pip install eth-account
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    _HAS_ETH_ACCOUNT = True
except ImportError:
    _HAS_ETH_ACCOUNT = False


# Message format must match the frontend (keys.ts registerMetaMaskKey)
def _ownership_message(account: str) -> str:
    return (
        f"Sign this message to prove ownership of your MetaMask wallet for YieldFabric key registration.\n\n"
        f"Account: {account}\n"
        f"Timestamp: {int(time.time() * 1000)}"
    )


def address_from_private_key(private_key_hex: str) -> str:
    """
    Derive the Ethereum address (0x-prefixed) from a private key hex string.

    Raises:
        RuntimeError: If eth_account is not installed or key is invalid.
    """
    if not _HAS_ETH_ACCOUNT:
        raise RuntimeError(
            "eth_account is required. Install with: pip install eth-account"
        )
    key = private_key_hex.removeprefix("0x").strip()
    acct = Account.from_key(key)
    return acct.address


def generate_ethereum_key() -> tuple[str, str]:
    """
    Generate a new Ethereum key pair (secp256k1).

    Returns:
        (private_key_hex, address) - address is 0x-prefixed (use as public_key for registration).

    Raises:
        RuntimeError: If eth_account is not installed.
    """
    if not _HAS_ETH_ACCOUNT:
        raise RuntimeError(
            "eth_account is required for key generation. Install with: pip install eth-account"
        )
    acct = Account.create()
    # Private key as hex (without 0x) for storage; address is the "public key" for external keys
    return acct.key.hex(), acct.address


def sign_ownership_message(address: str, private_key_hex: str) -> tuple[str, str]:
    """
    Sign the standard ownership message in Ethereum personal_sign format.

    Args:
        address: 0x-prefixed Ethereum address (must match the key that owns private_key).
        private_key_hex: Private key as hex string (with or without 0x).

    Returns:
        (message, signature_hex) - signature_hex is 130 chars (65 bytes r+s+v), no 0x prefix.

    Raises:
        RuntimeError: If eth_account is not installed.
    """
    if not _HAS_ETH_ACCOUNT:
        raise RuntimeError(
            "eth_account is required for signing. Install with: pip install eth-account"
        )
    key = private_key_hex.removeprefix("0x").strip()
    acct = Account.from_key(key)
    if acct.address.lower() != address.lower():
        raise ValueError("Private key does not match the given address")
    message_text = _ownership_message(address)
    message = encode_defunct(text=message_text)
    signed = acct.sign_message(message)
    # Backend expects 130 hex chars (65 bytes); strip 0x if present
    sig_hex = signed.signature.hex()
    if sig_hex.startswith("0x"):
        sig_hex = sig_hex[2:]
    return message_text, sig_hex


def verify_external_key_ownership(
    auth_service_url: str,
    jwt_token: str,
    public_key: str,
    message: str,
    signature: str,
    signature_format: str = "hex",
) -> dict[str, Any]:
    """
    Call POST /keys/external/verify-ownership to verify that the signature was produced
    by the holder of public_key (Ethereum address).

    Returns:
        JSON response dict with 'valid', 'message', etc.
    """
    url = f"{auth_service_url.rstrip('/')}/keys/external/verify-ownership"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    payload = {
        "public_key": public_key,
        "message": message,
        "signature": signature,
        "signature_format": signature_format,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Verify ownership failed ({resp.status_code}): {msg}")
    return resp.json()


def get_user_keys(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
) -> List[dict]:
    """
    Get all key pairs for a user (GET /keys/users/:user_id/keys).

    Returns:
        List of key pair dicts (id, public_key, key_name, ...).
    """
    url = f"{auth_service_url.rstrip('/')}/keys/users/{user_id}/keys"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Get user keys failed ({resp.status_code}): {msg}")
    data = resp.json()
    return data if isinstance(data, list) else []


def get_key_id_by_address(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
    address: str,
) -> Optional[str]:
    """
    Find a user key whose public_key matches the given address (0x-prefixed).
    Returns the key id (UUID string) or None if not found.
    """
    keys = get_user_keys(auth_service_url, jwt_token, user_id)
    want = (address or "").strip().lower()
    if not want:
        return None
    if not want.startswith("0x"):
        want = "0x" + want
    for k in keys:
        pk = (k.get("public_key") or "").strip().lower()
        if not pk.startswith("0x"):
            pk = "0x" + pk
        if pk == want:
            return str(k.get("id", ""))
    return None


def register_key_with_specific_wallet(
    auth_service_url: str,
    jwt_token: str,
    key_id: str,
    wallet_address: str,
) -> dict[str, Any]:
    """
    Register a key as an owner of a specific wallet (POST /keys/register-with-specific-wallet).
    Used to register the issuer external key with a loan wallet.
    """
    url = f"{auth_service_url.rstrip('/')}/keys/register-with-specific-wallet"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    payload = {"key_id": key_id, "wallet_address": (wallet_address or "").strip()}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("error", err.get("details", resp.text))
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Register key with wallet failed ({resp.status_code}): {msg}")
    return resp.json()


def register_external_key(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
    key_name: str,
    public_key: str,
    register_with_wallet: bool = False,
    expires_at: Optional[str] = None,
) -> dict[str, Any]:
    """
    Register an external key with the auth service (POST /keys/external).

    Args:
        auth_service_url: Base URL of the auth service (e.g. http://localhost:3000).
        jwt_token: Bearer token for the user registering the key.
        user_id: UUID of the user who owns the key.
        key_name: Display name for the key.
        public_key: Ethereum address (0x...) or public key string.
        register_with_wallet: If True, also register this key as an owner of the user's wallet.
        expires_at: Optional ISO8601 expiry.

    Returns:
        Key pair response dict (id, entity_type, entity_id, key_name, public_key, etc.).
    """
    url = f"{auth_service_url.rstrip('/')}/keys/external"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    payload = {
        "user_id": user_id,
        "key_name": key_name,
        "public_key": public_key,
        "register_with_wallet": register_with_wallet,
    }
    if expires_at is not None:
        payload["expires_at"] = expires_at
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Register external key failed ({resp.status_code}): {msg}")
    return resp.json()


def generate_and_register_external_key(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
    key_name: str,
    register_with_wallet: bool = False,
    verify_ownership: bool = True,
) -> tuple[dict[str, Any], str, str]:
    """
    Generate a new Ethereum key, optionally verify ownership, and register it as an external key.

    Returns:
        (key_pair_response, private_key_hex, address)
        - key_pair_response: API response from POST /keys/external.
        - private_key_hex: Hex private key (store securely if you need to sign later).
        - address: 0x-prefixed address (same as public_key in the key pair).
    """
    private_key_hex, address = generate_ethereum_key()
    message, signature = sign_ownership_message(address, private_key_hex)

    if verify_ownership:
        try:
            result = verify_external_key_ownership(
                auth_service_url, jwt_token, address, message, signature
            )
            if not result.get("valid"):
                raise RuntimeError(
                    f"Ownership verification returned valid=False: {result.get('message', '')}"
                )
        except Exception as e:
            # Frontend continues registration even if verification fails
            raise RuntimeError(f"Ownership verification failed: {e}") from e

    key_pair = register_external_key(
        auth_service_url=auth_service_url,
        jwt_token=jwt_token,
        user_id=user_id,
        key_name=key_name,
        public_key=address,
        register_with_wallet=register_with_wallet,
    )
    return key_pair, private_key_hex, address


def ensure_issuer_external_key(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
    key_file_path: Union[str, Path],
    key_name: str = "Issuer script external key",
    register_with_wallet: bool = False,
    verify_ownership: bool = True,
) -> tuple[str, str, Optional[dict[str, Any]], Optional[str]]:
    """
    Ensure an external key exists for the issuer: create and register on first run, reuse otherwise.

    - If key_file_path does not exist: generate a new key, save it to key_file_path (one line, hex),
      register it to the issuer account, and return (address, private_key_hex, key_pair_response, key_id).
    - If key_file_path exists: read the private key, derive address, look up key_id by address, and return
      (address, private_key_hex, None, key_id). No registration is performed (key is assumed already registered).

    Returns:
        (address, private_key_hex, key_pair_or_none, key_id_or_none)
        - address: 0x-prefixed Ethereum address.
        - private_key_hex: Private key as hex (with or without 0x).
        - key_pair_or_none: Key pair response from registration when key was just created; None when key file existed.
        - key_id_or_none: Key UUID string for use with register_key_with_specific_wallet; None if key not found on server.
    """
    path = Path(key_file_path)
    if path.exists():
        private_key_hex = path.read_text().strip().removeprefix("0x").strip()
        if not private_key_hex or len(private_key_hex) < 32:
            raise ValueError(f"Invalid or empty key in {path}")
        address = address_from_private_key(private_key_hex)
        key_id = get_key_id_by_address(auth_service_url, jwt_token, user_id, address)
        return address, private_key_hex, None, key_id

    # First time: generate, save, register
    key_pair, private_key_hex, address = generate_and_register_external_key(
        auth_service_url=auth_service_url,
        jwt_token=jwt_token,
        user_id=user_id,
        key_name=key_name,
        register_with_wallet=register_with_wallet,
        verify_ownership=verify_ownership,
    )
    # Save private key to file (hex, one line)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(private_key_hex.strip() + "\n")
    key_id = str(key_pair.get("id", "")) if key_pair else None
    return address, private_key_hex, key_pair, key_id
