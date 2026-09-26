# passvault

A local, encrypted, offline password manager CLI.

> **PyPI note:** the distribution is published as
> [`passvault-cli`](https://pypi.org/project/passvault-cli/) because the name
> `passvault` was already taken. The installed command and import name are
> still `passvault`.

- No network calls, no accounts, no telemetry.
- Everything lives in a single encrypted file on your machine.
- Your master password is required on **every** command. There is no session
  caching and no OS keychain integration — by design.

## How it works

Entries are stored as a JSON object and encrypted with
[Fernet](https://cryptography.io/en/latest/fernet/) (AES-128-CBC + HMAC-SHA256,
authenticated encryption).

The encryption key is derived from your master password with **Argon2id**
(memory-hard, 64 MiB, 3 passes) using a random 16-byte salt.

The vault file is laid out as:

```
salt (16 bytes) || Fernet token
```

The salt is generated once at vault creation and never rotated. Deriving the
key requires the master password, which is never stored, logged, or written
anywhere. A wrong master password fails loudly — authenticated decryption means
we never return garbage plaintext.

## Install

From PyPI:

```bash
pip install passvault-cli
```

Or from source:

```bash
git clone https://github.com/Ajeet2005/passvault.git
cd passvault
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e .
```

Requires Python 3.10+.

## Usage

### Create a vault

```bash
passvault init
```

Refuses to run if a vault already exists. You'll be asked for your master
password twice.

### Add an entry

```bash
passvault add github --generate --length 24 --username me@example.com
passvault add email                 # prompt for the password (hidden input)
```

Existing entries are only overwritten after a confirmation prompt. Passwords
are never echoed back to the terminal.

### List entries

```bash
passvault list
```

Shows names, usernames, and whether notes are set. **Never** prints stored
passwords.

### Retrieve a password

```bash
passvault get github               # print the password to stdout
passvault get github --clipboard   # copy to the clipboard, don't print it
```

The behavior is always explicit: you choose whether the secret is printed or
copied. There is no silent default.

### Delete an entry

```bash
passvault delete github
```

Asks for confirmation first.

### Generate a password without a vault

```bash
passvault generate --length 32
passvault generate --no-symbols
passvault generate --no-digits --clipboard
```

## Vault location

The vault lives in your OS's user data directory:

| OS      | Path                                              |
| ------- | ------------------------------------------------- |
| Windows | `%LOCALAPPDATA%\passvault\vault.dat`              |
| macOS   | `~/Library/Application Support/passvault/vault.dat` |
| Linux   | `~/.local/share/passvault/vault.dat`              |

## Development

```bash
pip install -e ".[dev]"
pytest --cov=passvault
```

Test layout:

- `tests/test_crypto.py` — key derivation determinism, round trips, wrong-password
  failure.
- `tests/test_storage.py` — create/load/save round trips, salt persistence,
  refusing writes on a wrong password.
- `tests/test_generator.py` — length and character-class guarantees.
- `tests/test_cli.py` — end-to-end command tests via Typer's `CliRunner`.

## Security notes

- The master password is never stored, in any form.
- Decrypted passwords are only printed when you explicitly run `get` without
  `--clipboard`.
- All randomness uses Python's `secrets` module, never `random`.
- A wrong master password always fails loudly.
- No session caching and no OS keychain support in this version.

## Disclaimer

This is a learning project. It has **not** been audited. For real secrets, use a
battle-tested password manager.

## License

MIT — see [LICENSE](https://github.com/Ajeet2005/passvault/blob/main/LICENSE).
