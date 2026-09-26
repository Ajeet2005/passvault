"""passvault command line interface.

Every command that touches the vault prompts for the master password (there is
deliberately no session caching and no OS keychain). Decrypted material lives
only in local variables for the duration of a command.
"""

from __future__ import annotations

from typing import NoReturn, Optional

import pyperclip
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import __version__, crypto, generator, storage

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A local, encrypted, offline password manager.",
)

console = Console()
error_console = Console(stderr=True)


def _fail(message: str, code: int = 1) -> NoReturn:
    """Print an error to stderr and exit non-zero."""
    error_console.print(f"[bold red]error:[/bold red] {message}")
    raise typer.Exit(code=code)


# --- interactive prompt helpers -------------------------------------------------
# These are thin wrappers so they can be monkeypatched in tests (InquirerPy needs
# a real TTY, which Typer's CliRunner does not provide).


def _prompt_secret(message: str) -> str:
    return inquirer.secret(message=f"{message}:", qmark="").execute()


def _prompt_text(message: str) -> str:
    return inquirer.text(message=f"{message}:", qmark="").execute()


def _prompt_confirm(message: str, default: bool = False) -> bool:
    return inquirer.confirm(message=message, default=default, qmark="").execute()


# --- shared vault unlock --------------------------------------------------------


def _unlock_vault() -> tuple[dict, str]:
    """Prompt for the master password and return ``(entries, password)``.

    The password is returned so a command can hand it straight to
    :func:`storage.save_vault`. It is never stored globally.
    """
    if not storage.vault_exists():
        _fail("No vault found. Run 'passvault init' first.")

    password = _prompt_secret("Master password")
    if not password:
        _fail("Master password cannot be empty.")

    try:
        entries = storage.load_vault(password)
    except crypto.InvalidVaultPassword as exc:
        _fail(str(exc))
    except FileNotFoundError as exc:
        _fail(str(exc))
    return entries, password


def _output_secret(value: str, clipboard: bool, label: str = "Generated password") -> None:
    """Emit a secret to stdout or the clipboard, never silently."""
    if clipboard:
        try:
            pyperclip.copy(value)
        except pyperclip.PyperclipException as exc:  # pragma: no cover - env dependent
            _fail(f"Could not copy to clipboard: {exc}")
        console.print(f"[green]{label} copied to clipboard[/green] (not shown).")
    else:
        # Only reached on an explicit request to display the secret. Markup is
        # disabled so characters like '[' in a password are printed verbatim.
        console.print(value, markup=False, highlight=False)


# --- commands -------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def _main(
    version: bool = typer.Option(
        False, "--version", help="Show the version and exit.", is_eager=True
    ),
) -> None:
    if version:
        console.print(f"passvault {__version__}")
        raise typer.Exit()


@app.command()
def init() -> None:
    """Create a new, empty vault protected by a master password."""
    if storage.vault_exists():
        _fail(f"A vault already exists at {storage.vault_path()}.")

    password = _prompt_secret("Choose a master password")
    if not password:
        _fail("Master password cannot be empty.")

    confirmation = _prompt_secret("Confirm master password")
    if password != confirmation:
        _fail("Passwords do not match.")

    storage.create_empty_vault(password)
    console.print(f"[green]Vault created[/green] at {storage.vault_path()}")


@app.command()
def add(
    name: str = typer.Argument(..., help="Name of the entry to add."),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate a password instead of prompting."
    ),
    length: int = typer.Option(
        16, "--length", "-l", help="Length used with --generate."
    ),
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Username to store (skips the prompt)."
    ),
    notes: Optional[str] = typer.Option(
        None, "--notes", help="Notes to store (skips the prompt)."
    ),
) -> None:
    """Add or overwrite an entry."""
    entries, password = _unlock_vault()

    if name in entries:
        if not _prompt_confirm(f"'{name}' already exists. Overwrite?", default=False):
            _fail("Aborted; the existing entry was left unchanged.")

    if generate:
        try:
            secret = generator.generate_password(length=length)
        except ValueError as exc:
            _fail(str(exc))
    else:
        secret = _prompt_secret(f"Password for '{name}'")
        if not secret:
            _fail("Password cannot be empty.")

    if username is None:
        username = _prompt_text("Username (optional)") or None
    if notes is None:
        notes = _prompt_text("Notes (optional)") or None

    entries[name] = {"password": secret, "username": username, "notes": notes}
    storage.save_vault(entries, password)
    console.print(f"[green]Saved[/green] '{escape(name)}'.")


@app.command("list")
def list_entries() -> None:
    """List entry names. Stored passwords are never shown."""
    entries, _ = _unlock_vault()

    if not entries:
        console.print("Vault is empty.")
        return

    table = Table(title="passvault entries", show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Username")
    table.add_column("Notes")

    for entry_name in sorted(entries):
        record = entries[entry_name]
        has_notes = bool(record.get("notes"))
        table.add_row(
            escape(entry_name),
            escape(record.get("username") or "-"),
            "(set)" if has_notes else "-",
        )

    console.print(table)


@app.command()
def get(
    name: str = typer.Argument(..., help="Entry to retrieve."),
    clipboard: bool = typer.Option(
        False, "--clipboard", "-c", help="Copy to the clipboard instead of printing."
    ),
) -> None:
    """Retrieve a stored password."""
    entries, _ = _unlock_vault()

    record = entries.get(name)
    if record is None:
        _fail(f"No entry named '{escape(name)}'.")

    secret = record.get("password", "")
    if clipboard:
        _output_secret(secret, clipboard=True, label=f"Password for '{escape(name)}'")
    else:
        console.print(secret, markup=False, highlight=False)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Entry to delete."),
) -> None:
    """Delete an entry after confirmation."""
    entries, password = _unlock_vault()

    if name not in entries:
        _fail(f"No entry named '{escape(name)}'.")

    if not _prompt_confirm(f"Delete '{name}'?", default=False):
        _fail("Aborted; nothing was deleted.")

    del entries[name]
    storage.save_vault(entries, password)
    console.print(f"[green]Deleted[/green] '{escape(name)}'.")


@app.command()
def generate(
    length: int = typer.Option(16, "--length", "-l", help="Password length."),
    no_symbols: bool = typer.Option(
        False, "--no-symbols", help="Exclude symbols."
    ),
    no_digits: bool = typer.Option(False, "--no-digits", help="Exclude digits."),
    clipboard: bool = typer.Option(
        False, "--clipboard", "-c", help="Copy to the clipboard instead of printing."
    ),
) -> None:
    """Generate a password without touching the vault."""
    try:
        secret = generator.generate_password(
            length=length,
            use_symbols=not no_symbols,
            use_digits=not no_digits,
        )
    except ValueError as exc:
        _fail(str(exc))

    _output_secret(secret, clipboard=clipboard)


if __name__ == "__main__":  # pragma: no cover
    app()
