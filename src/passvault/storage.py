"""Vault persistence.

The vault is a single file containing::

    salt (16 raw bytes) || Fernet token (encrypted UTF-8 JSON object)

The entries themselves are a JSON object mapping entry name to a small record::

    {
        "github": {"password": "...", "username": "me", "notes": "..."},
        ...
    }

The salt is generated once at vault creation and never rotated, so the derived
key stays stable across saves.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from platformdirs import user_data_dir

from . import crypto

__all__ = [
    "VAULT_FILENAME",
    "vault_path",
    "vault_exists",
    "create_empty_vault",
    "load_vault",
    "save_vault",
]

VAULT_FILENAME = "vault.dat"

_APP_NAME = "passvault"


def vault_path() -> Path:
    """Return the location of the vault file.

    Overridden in tests via monkeypatch; kept as a function so no path is
    captured at import time.
    """
    return Path(user_data_dir(_APP_NAME)) / VAULT_FILENAME


def vault_exists() -> bool:
    """Return ``True`` if a vault file is present."""
    return vault_path().is_file()


def _read_raw(path: Path) -> tuple[bytes, bytes]:
    """Read the vault file and split it into ``(salt, encrypted_blob)``."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "No vault found. Run 'passvault init' first."
        ) from exc

    if len(raw) <= crypto.SALT_SIZE:
        raise crypto.InvalidVaultPassword(
            "Vault file is truncated or corrupted."
        )
    return raw[: crypto.SALT_SIZE], raw[crypto.SALT_SIZE :]


def _write_raw(path: Path, salt: bytes, blob: bytes) -> None:
    """Write ``salt || blob`` to ``path`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(salt + blob)
    os.replace(tmp, path)
    # Best-effort tightening of permissions on POSIX; a no-op on Windows.
    try:
        os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass


def create_empty_vault(password: str) -> None:
    """Create a new vault protected by ``password`` with no entries."""
    path = vault_path()
    salt = crypto.generate_salt()
    key = crypto.derive_key(password, salt)
    blob = crypto.encrypt(json.dumps({}).encode("utf-8"), key)
    _write_raw(path, salt, blob)


def load_vault(password: str) -> dict:
    """Decrypt and return the entries dict.

    Raises :class:`crypto.InvalidVaultPassword` on a wrong password or a
    corrupted vault.
    """
    salt, blob = _read_raw(vault_path())
    key = crypto.derive_key(password, salt)
    plaintext = crypto.decrypt(blob, key)
    try:
        entries = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise crypto.InvalidVaultPassword(
            "Vault contents are unreadable."
        ) from exc
    if not isinstance(entries, dict):
        raise crypto.InvalidVaultPassword("Vault contents are malformed.")
    return entries


def save_vault(entries: dict, password: str) -> None:
    """Persist ``entries``, reusing the existing salt.

    Deriving the key requires the salt, so the vault must already exist; the
    password must be correct or decryption/encryption would be inconsistent.
    """
    path = vault_path()
    salt, blob = _read_raw(path)
    key = crypto.derive_key(password, salt)
    # Verify the password against the current contents before overwriting.
    # Without this, a wrong password would re-encrypt with a bogus key and
    # silently destroy the vault.
    crypto.decrypt(blob, key)
    new_blob = crypto.encrypt(
        json.dumps(entries, sort_keys=True).encode("utf-8"), key
    )
    _write_raw(path, salt, new_blob)
