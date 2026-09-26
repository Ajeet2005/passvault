"""Tests for :mod:`passvault.generator`."""

import string

import pytest

from passvault import generator


def test_length_is_respected():
    for length in (8, 16, 32, 64):
        assert len(generator.generate_password(length=length)) == length


def test_default_includes_all_classes():
    password = generator.generate_password(length=32)
    assert any(c in string.ascii_lowercase for c in password)
    assert any(c in string.ascii_uppercase for c in password)
    assert any(c in string.digits for c in password)
    assert any(c in generator.SYMBOLS for c in password)


def test_digits_can_be_excluded():
    for _ in range(20):
        password = generator.generate_password(length=24, use_digits=False)
        assert not any(c in string.digits for c in password)


def test_symbols_can_be_excluded():
    for _ in range(20):
        password = generator.generate_password(length=24, use_symbols=False)
        assert not any(c in generator.SYMBOLS for c in password)


def test_only_letters_when_both_disabled():
    password = generator.generate_password(
        length=24, use_symbols=False, use_digits=False
    )
    assert all(c in string.ascii_letters for c in password)


def test_too_short_length_raises():
    # 4 classes requested -> minimum length is 4.
    with pytest.raises(ValueError):
        generator.generate_password(length=3)
    with pytest.raises(ValueError):
        generator.generate_password(length=2, use_symbols=False)


def test_minimum_length_is_allowed():
    password = generator.generate_password(length=2, use_symbols=False, use_digits=False)
    assert len(password) == 2
    assert any(c in string.ascii_lowercase for c in password)
    assert any(c in string.ascii_uppercase for c in password)


def test_passwords_are_not_repeated():
    passwords = {generator.generate_password(length=24) for _ in range(50)}
    assert len(passwords) == 50
