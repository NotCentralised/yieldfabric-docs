"""
External-key management — orchestration layer.

Stitches together:

  - `yieldfabric.utils.crypto` (pure crypto)
  - `AuthService` (REST endpoints /keys/external, /keys/...)
  - local filesystem (key file persistence)

Two primary entry points:

  * `KeyManager.ensure_external_key(...)` — idempotent "have a key,
    registered to this user, persisted to a file" operation. Port of
    `loan_management/modules/register_external_key.py::ensure_issuer_external_key`.
    First run generates + registers + saves. Subsequent runs load from
    file and resolve the key_id from the auth service.

  * `KeyManager.generate_and_register(...)` — one-shot generate +
    verify-ownership + register. Used when you want a fresh key
    without file persistence (rare; usually ensure_external_key is
    what you want).

Companion: `FileBackedSigner` — a callable compatible with
`MessageSignatureListener`'s `sign_callback` signature. Loads a
private key from a file and signs the `message_hash` field of
whatever unsigned-tx dict the backend returns.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from ..services import AuthService
from ..utils.crypto import (
    address_from_private_key,
    generate_ethereum_key,
    sign_message_hash,
    sign_ownership_message,
)
from ..utils.logger import get_logger


@dataclass
class EnsureKeyResult:
    """
    Outcome of `ensure_external_key`.

    - `address`: 0x-prefixed Ethereum address of the key.
    - `private_key_hex`: private key (hex, no 0x prefix) — KEEP SECRET.
    - `key_id`: backend's UUID for the key pair. None only if the
      key file pre-existed and the auth service doesn't know the
      address (shouldn't happen in practice).
    - `newly_created`: True if this run generated and registered a
      new key; False if we reused an existing file.
    """

    address: str
    private_key_hex: str
    key_id: Optional[str]
    newly_created: bool


class KeyManager:
    """
    Orchestrator for external-key registration + persistence.

    Instantiate with an AuthService and a logged-in user's JWT + id;
    call `ensure_external_key(path, key_name, ...)` to guarantee a
    registered key exists on disk.
    """

    def __init__(
        self,
        auth_service: AuthService,
        *,
        token: str,
        user_id: str,
        debug: bool = False,
    ):
        self.auth_service = auth_service
        self.token = token
        self.user_id = user_id
        self.logger = get_logger(debug=debug)

    # ------------------------------------------------------------------

    def ensure_external_key(
        self,
        key_file_path: Union[str, Path],
        *,
        key_name: str = "External key (Python CLI)",
        register_with_wallet: bool = False,
        verify_ownership: bool = True,
    ) -> EnsureKeyResult:
        """
        Idempotent key provisioning.

        If `key_file_path` exists:
            - Load the private key, derive the address.
            - Resolve key_id via auth service (may be None if backend
              doesn't have it — that's the caller's problem to surface).
            - Return with newly_created=False.

        If `key_file_path` does NOT exist:
            - Generate a new key.
            - If verify_ownership: POST /keys/external/verify-ownership
              to sanity-check the signature before registering.
            - POST /keys/external to register.
            - Write the private key to `key_file_path` (hex, one line,
              parent dir created if missing).
            - Return with newly_created=True.

        `register_with_wallet` passes through to the POST /keys/external
        payload; set True to also link this key as an owner of the
        user's default wallet on creation.
        """
        path = Path(key_file_path)

        if path.exists():
            private_key_hex = path.read_text().strip().removeprefix("0x").strip()
            if not private_key_hex or len(private_key_hex) < 32:
                raise ValueError(f"invalid or empty key file: {path}")

            address = address_from_private_key(private_key_hex)
            key_id = self.auth_service.get_key_id_by_address(
                self.token, self.user_id, address
            )
            self.logger.info(
                f"  🔑 reusing external key from {path} address={address}"
                + (f" key_id={key_id[:8]}..." if key_id else " (key_id unknown)")
            )
            return EnsureKeyResult(
                address=address,
                private_key_hex=private_key_hex,
                key_id=key_id,
                newly_created=False,
            )

        # Fresh key path.
        self.logger.info(f"  🔑 generating new external key for {path}")
        result = self.generate_and_register(
            key_name=key_name,
            register_with_wallet=register_with_wallet,
            verify_ownership=verify_ownership,
        )

        # Persist the private key to disk. Create parent dir if needed;
        # write as a single line of hex with trailing newline (matches
        # the shell-era issuer_external_key.txt format so cross-reading
        # works in both directions).
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.private_key_hex.strip() + "\n")

        # On POSIX, tighten permissions so the key file isn't readable
        # by other users. Best-effort — failure here is non-fatal.
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

        self.logger.success(
            f"  ✅ key registered: address={result.address} key_id={result.key_id} "
            f"saved to {path}"
        )
        return result

    def generate_and_register(
        self,
        *,
        key_name: str = "External key (Python CLI)",
        register_with_wallet: bool = False,
        verify_ownership: bool = True,
    ) -> EnsureKeyResult:
        """
        Generate a new key, optionally verify ownership, register.
        Does NOT persist to disk — use `ensure_external_key` for that.
        """
        private_key_hex, address = generate_ethereum_key()
        message, signature = sign_ownership_message(address, private_key_hex)

        if verify_ownership:
            verify = self.auth_service.verify_external_key_ownership(
                self.token,
                public_key=address,
                message=message,
                signature=signature,
            )
            if not verify.get("valid"):
                raise RuntimeError(
                    f"verify-ownership returned valid=false: {verify.get('message')}"
                )

        key_pair = self.auth_service.register_external_key(
            self.token,
            user_id=self.user_id,
            key_name=key_name,
            public_key=address,
            register_with_wallet=register_with_wallet,
        )
        key_id = key_pair.get("id")
        return EnsureKeyResult(
            address=address,
            private_key_hex=private_key_hex,
            key_id=str(key_id) if key_id else None,
            newly_created=True,
        )


# ----------------------------------------------------------------------
# Signer callback adapter for MessageSignatureListener.
# ----------------------------------------------------------------------

class FileBackedSigner:
    """
    Callable adapter that satisfies `MessageSignatureListener`'s
    `sign_callback` contract using a private key loaded from disk.

    Usage:
        signer = FileBackedSigner("./issuer_external_key.txt")
        with MessageSignatureListener(
            payments, user_id, token, sign_callback=signer
        ):
            ...run workflow...

    The backend's unsigned-transaction payload has a `message_hash`
    field (32-byte hex) that must be signed with personal_sign over
    the prefixed hash. That's what `sign_message_hash` does — same
    format the contract's ecrecover expects.
    """

    def __init__(self, key_file_path: Union[str, Path]):
        self.path = Path(key_file_path)
        if not self.path.exists():
            raise FileNotFoundError(f"signer key file not found: {self.path}")
        self._private_key_hex = (
            self.path.read_text().strip().removeprefix("0x").strip()
        )
        if not self._private_key_hex:
            raise ValueError(f"key file is empty: {self.path}")
        # Derive + cache address once; surfaces key-format errors eagerly.
        self.address = address_from_private_key(self._private_key_hex)

    def __call__(self, unsigned_tx: dict) -> str:
        """
        Sign the message_hash from `unsigned_tx`. Returns a 130-hex-char
        signature (no 0x prefix) — the shape the submit-signed-message
        endpoint expects.
        """
        if not isinstance(unsigned_tx, dict):
            raise ValueError(
                "unsigned_tx must be a dict (GET unsigned-transaction response)"
            )
        message_hash = unsigned_tx.get("message_hash") or unsigned_tx.get("messageHash")
        if not message_hash:
            raise ValueError(
                f"unsigned_tx is missing message_hash field; keys: {list(unsigned_tx.keys())}"
            )
        return sign_message_hash(self._private_key_hex, message_hash)

    def __repr__(self) -> str:  # pragma: no cover — debug aid
        return f"FileBackedSigner(path={self.path}, address={self.address})"
