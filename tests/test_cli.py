"""End-to-end tests for the Typer CLI.

InquirerPy needs a real TTY, so the prompt helpers and clipboard are patched;
the vault location is redirected to a temp file.
"""

import pytest
from typer.testing import CliRunner

from passvault import cli, storage

runner = CliRunner()

MASTER = "correct horse battery staple"


@pytest.fixture()
def vault_file(tmp_path, monkeypatch):
    path = tmp_path / "vault.dat"
    monkeypatch.setattr(storage, "vault_path", lambda: path)
    return path


@pytest.fixture()
def prompts(monkeypatch):
    """Patch interactive prompts to return values from a fixed mapping."""
    secrets = {
        "Master password": MASTER,
        "Choose a master password": MASTER,
        "Confirm master password": MASTER,
    }
    state = {"confirm": True, "text": ""}

    def fake_secret(message, _secrets=secrets):
        return _secrets.get(message.rstrip(":"), _secrets.get(message, ""))

    monkeypatch.setattr(cli, "_prompt_secret", fake_secret)
    monkeypatch.setattr(cli, "_prompt_text", lambda message: state["text"])
    monkeypatch.setattr(cli, "_prompt_confirm", lambda message, default=False: state["confirm"])
    return state


def _set_secret(monkeypatch, message, value):
    """Queue a specific answer for one secret prompt."""
    original = cli._prompt_secret

    def fake(msg):
        return value if msg.rstrip(":") == message else original(msg)

    monkeypatch.setattr(cli, "_prompt_secret", fake)
    return fake


def test_init_creates_vault(vault_file, prompts):
    result = runner.invoke(cli.app, ["init"])
    assert result.exit_code == 0
    assert "Vault created" in result.output
    assert storage.vault_exists()


def test_init_refuses_when_vault_exists(vault_file, prompts):
    runner.invoke(cli.app, ["init"])
    result = runner.invoke(cli.app, ["init"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_get_fails_without_vault(vault_file, prompts):
    result = runner.invoke(cli.app, ["get", "github"])
    assert result.exit_code == 1
    assert "No vault found" in result.output


def test_add_list_get_delete_flow(vault_file, prompts, monkeypatch):
    runner.invoke(cli.app, ["init"])

    # add a generated entry
    result = runner.invoke(cli.app, ["add", "github", "--generate", "--length", "20"])
    assert result.exit_code == 0, result.output
    assert "Saved" in result.output

    # entry survives a reload
    assert "github" in storage.load_vault(MASTER)

    # list shows the name but never the password
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert "github" in result.output
    stored_password = storage.load_vault(MASTER)["github"]["password"]
    assert stored_password not in result.output

    # get prints the password to stdout
    result = runner.invoke(cli.app, ["get", "github"])
    assert result.exit_code == 0
    assert stored_password in result.output

    # get --clipboard copies and does not print the password
    copied = {}
    monkeypatch.setattr(cli.pyperclip, "copy", lambda value: copied.setdefault("v", value))
    result = runner.invoke(cli.app, ["get", "github", "--clipboard"])
    assert result.exit_code == 0
    assert copied["v"] == stored_password
    assert stored_password not in result.output
    assert "clipboard" in result.output

    # delete removes it
    result = runner.invoke(cli.app, ["delete", "github"])
    assert result.exit_code == 0
    assert "github" not in storage.load_vault(MASTER)


def test_add_with_prompted_password(vault_file, prompts, monkeypatch):
    runner.invoke(cli.app, ["init"])
    _set_secret(monkeypatch, "Password for 'email'", "hunter2")
    result = runner.invoke(cli.app, ["add", "email", "--username", "me"])
    assert result.exit_code == 0
    assert "hunter2" not in result.output  # never echo a password back
    assert storage.load_vault(MASTER)["email"] == {
        "password": "hunter2",
        "username": "me",
        "notes": None,
    }


def test_add_existing_entry_aborts_when_declined(vault_file, prompts):
    runner.invoke(cli.app, ["init"])
    runner.invoke(cli.app, ["add", "github", "--generate"])
    prompts["confirm"] = False
    result = runner.invoke(cli.app, ["add", "github", "--generate"])
    assert result.exit_code == 1
    assert "Aborted" in result.output


def test_get_missing_entry_errors(vault_file, prompts):
    runner.invoke(cli.app, ["init"])
    result = runner.invoke(cli.app, ["get", "nope"])
    assert result.exit_code == 1
    assert "No entry named" in result.output


def test_delete_declined_leaves_entry(vault_file, prompts):
    runner.invoke(cli.app, ["init"])
    runner.invoke(cli.app, ["add", "github", "--generate"])
    prompts["confirm"] = False
    result = runner.invoke(cli.app, ["delete", "github"])
    assert result.exit_code == 1
    assert "github" in storage.load_vault(MASTER)


def test_wrong_master_password_fails_loudly(vault_file, prompts, monkeypatch):
    runner.invoke(cli.app, ["init"])
    monkeypatch.setattr(cli, "_prompt_secret", lambda message: "wrong password")
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 1
    assert "Incorrect master password" in result.output


def test_generate_standalone_no_vault(vault_file, prompts):
    result = runner.invoke(cli.app, ["generate", "--length", "24", "--no-symbols"])
    assert result.exit_code == 0
    password = result.output.strip()
    assert len(password) == 24
    assert not any(c in cli.generator.SYMBOLS for c in password)
    assert not storage.vault_exists()


def test_generate_clipboard(vault_file, prompts, monkeypatch):
    copied = {}
    monkeypatch.setattr(cli.pyperclip, "copy", lambda value: copied.setdefault("v", value))
    result = runner.invoke(cli.app, ["generate", "--clipboard"])
    assert result.exit_code == 0
    assert "clipboard" in result.output
    assert copied["v"] not in result.output


def test_generate_invalid_length_errors(vault_file, prompts):
    result = runner.invoke(cli.app, ["generate", "--length", "1"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


def test_version(vault_file):
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.2" in result.output
