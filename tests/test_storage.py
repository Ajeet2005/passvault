"""Tests for :mod:`passvault.storage`."""

import json

import pytest

from passvault import crypto, storage


@pytest.fixture()
def vault_file(tmp_path, monkeypatch):
    path = tmp_path / "vault.dat"
    monkeypatch.setattr(storage, "vault_path", lambda: path)
    return path


def test_vault_does_not_exist_initially(vault_file):
    assert storage.vault_exists() is False


def test_create_empty_vault(vault_file):
    storage.create_empty_vault("master")
    assert storage.vault_exists() is True
    assert storage.load_vault("master") == {}


def test_created_file_layout(vault_file):
    storage.create_empty_vault("master")
    raw = vault_file.read_bytes()
    assert len(raw) > crypto.SALT_SIZE
    # The plaintext must not appear anywhere in the file.
    assert b"{" not in raw or not raw.startswith(b"{")


def test_load_with_wrong_password_raises(vault_file):
    storage.create_empty_vault("master")
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.load_vault("not-the-password")


def test_load_missing_vault_raises(vault_file):
    with pytest.raises(FileNotFoundError):
        storage.load_vault("master")


def test_save_and_load_round_trip(vault_file):
    storage.create_empty_vault("master")
    entries = {
        "github": {"password": "s3cret", "username": "me", "notes": None},
        "email": {"password": "hunter2", "username": None, "notes": "work"},
    }
    storage.save_vault(entries, "master")
    assert storage.load_vault("master") == entries


def test_salt_persists_across_saves(vault_file):
    storage.create_empty_vault("master")
    salt_before = vault_file.read_bytes()[: crypto.SALT_SIZE]
    storage.save_vault({"a": {"password": "x"}}, "master")
    storage.save_vault({"a": {"password": "x"}, "b": {"password": "y"}}, "master")
    salt_after = vault_file.read_bytes()[: crypto.SALT_SIZE]
    assert salt_before == salt_after


def test_save_with_wrong_password_does_not_corrupt(vault_file):
    storage.create_empty_vault("master")
    storage.save_vault({"a": {"password": "x"}}, "master")
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.save_vault({"a": {"password": "y"}}, "wrong")
    # Original contents must survive the rejected write.
    assert storage.load_vault("master") == {"a": {"password": "x"}}


def test_truncated_vault_is_rejected(vault_file):
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_bytes(b"short")
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.load_vault("master")


def test_garbage_blob_is_rejected(vault_file):
    salt = crypto.generate_salt()
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_bytes(salt + b"this is not a fernet token")
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.load_vault("master")


def test_invalid_utf8_contents_are_rejected(vault_file):
    salt = crypto.generate_salt()
    key = crypto.derive_key("master", salt)
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_bytes(salt + crypto.encrypt(b"\xff\xfe not utf-8", key))
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.load_vault("master")


def test_non_dict_contents_are_rejected(vault_file):
    salt = crypto.generate_salt()
    key = crypto.derive_key("master", salt)
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_bytes(salt + crypto.encrypt(b"[1, 2, 3]", key))
    with pytest.raises(crypto.InvalidVaultPassword):
        storage.load_vault("master")


def test_entries_are_stored_as_json_object(vault_file):
    storage.create_empty_vault("master")
    entries = {"a": {"password": "x", "username": "u", "notes": "n"}}
    storage.save_vault(entries, "master")
    salt, blob = vault_file.read_bytes()[:16], vault_file.read_bytes()[16:]
    key = crypto.derive_key("master", salt)
    assert json.loads(crypto.decrypt(blob, key)) == entries
