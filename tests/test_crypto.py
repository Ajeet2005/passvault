"""Tests for :mod:`passvault.crypto`."""

import pytest

from passvault import crypto


def test_generate_salt_length_and_randomness():
    salts = {crypto.generate_salt() for _ in range(20)}
    assert all(len(s) == crypto.SALT_SIZE for s in salts)
    assert len(salts) == 20  # practically certain to be unique


def test_derive_key_is_deterministic():
    salt = crypto.generate_salt()
    assert crypto.derive_key("hunter2", salt) == crypto.derive_key("hunter2", salt)


def test_derive_key_differs_by_password():
    salt = crypto.generate_salt()
    assert crypto.derive_key("hunter2", salt) != crypto.derive_key("hunter3", salt)


def test_derive_key_differs_by_salt():
    assert crypto.derive_key("hunter2", crypto.generate_salt()) != crypto.derive_key(
        "hunter2", crypto.generate_salt()
    )


def test_derive_key_rejects_bad_salt():
    with pytest.raises(ValueError):
        crypto.derive_key("hunter2", b"")


def test_encrypt_decrypt_round_trip():
    salt = crypto.generate_salt()
    key = crypto.derive_key("correct horse", salt)
    payload = "secret grenade".encode("utf-8")
    token = crypto.encrypt(payload, key)
    assert token != payload
    assert crypto.decrypt(token, key) == payload


def test_decrypt_wrong_key_raises():
    salt = crypto.generate_salt()
    token = crypto.encrypt(b"data", crypto.derive_key("right", salt))
    with pytest.raises(crypto.InvalidVaultPassword):
        crypto.decrypt(token, crypto.derive_key("wrong", salt))


def test_decrypt_tampered_token_raises():
    salt = crypto.generate_salt()
    key = crypto.derive_key("hunter2", salt)
    token = bytearray(crypto.encrypt(b"data", key))
    token[-1] ^= 0x01
    with pytest.raises(crypto.InvalidVaultPassword):
        crypto.decrypt(bytes(token), key)
