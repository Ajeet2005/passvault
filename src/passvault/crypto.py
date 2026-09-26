"""Cryptographic primitives for passvault.

Key derivation uses Argon2id (via ``argon2-cffi``) and encryption uses
``cryptography``'s Fernet (AES-128-CBC + HMAC-SHA256, authenticated).

Design notes
------------
* The master password is never stored. Only a salt is persisted alongside the
  encrypted blob; the key is re-derived on every command.
* ``derive_key`` returns a URL-safe base64 encoded 32-byte key, which is the
  exact format Fernet expects.
* ``decrypt`` never returns partial or garbage plaintext: any authentication
  failure is surfaced as :class:`InvalidVaultPassword`.
"""

from __future__ import annotations

import base64
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken

__all__ = [
    "InvalidVaultPassword",
    "SALT_SIZE",
    "generate_salt",
    "derive_key",
    "encrypt",
    "decrypt",
]

#: Length of the random salt, in bytes.
SALT_SIZE = 16

#: Length of the raw derived key, in bytes (before base64 encoding for Fernet).
KEY_SIZE = 32

# Argon2id parameters. Chosen to be conservative but usable for an interactive
# CLI on a laptop; raise these if you have cycles to spare.
_TIME_COST = 3
_MEMORY_COST_KIB = 64 * 1024  # 64 MiB
_PARALLELISM = 4


class InvalidVaultPassword(Exception):
    """Raised when decryption fails, i.e. the master password is wrong.

    Also raised when the vault file is corrupted or was encrypted with a
    different key, because Fernet cannot distinguish those cases.
    """


def generate_salt() -> bytes:
    """Return ``SALT_SIZE`` cryptographically secure random bytes."""
    return os.urandom(SALT_SIZE)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from ``password`` and ``salt``.

    The derivation is deterministic: the same password and salt always produce
    the same key. The result is a URL-safe base64 encoded 32-byte string, ready
    to hand to :class:`cryptography.fernet.Fernet`.
    """
    if not isinstance(salt, (bytes, bytearray)) or len(salt) == 0:
        raise ValueError("salt must be a non-empty bytes value")
    raw = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=bytes(salt),
        time_cost=_TIME_COST,
        memory_cost=_MEMORY_COST_KIB,
        parallelism=_PARALLELISM,
        hash_len=KEY_SIZE,
        type=Type.ID,
    )
    return base64.urlsafe_b64encode(raw)


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt ``data`` with ``key``, returning a Fernet token."""
    return Fernet(key).encrypt(data)


def decrypt(token: bytes, key: bytes) -> bytes:
    """Decrypt a Fernet ``token`` with ``key``.

    Raises :class:`InvalidVaultPassword` if the key is wrong or the token was
    tampered with. This never silently returns garbage.
    """
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise InvalidVaultPassword(
            "Incorrect master password, or the vault is corrupted."
        ) from exc
