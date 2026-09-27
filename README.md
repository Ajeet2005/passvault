# passvault

**PassVault** is a local, encrypted, offline password manager that lives entirely in your
terminal. Every vault is a single file on your machine — entries are sealed with
authenticated encryption (AES-128-CBC + HMAC-SHA256) and the key is derived from your
master password with Argon2id, so nothing readable ever touches the disk and the master
password itself is never stored. Add entries with your own passwords, or let the built-in
generator roll cryptographically secure random ones — any length, symbols and digits
optional — then fetch them later printed to stdout or copied straight to your clipboard.

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

### Option 1 — pipx (recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments and
puts their commands on your PATH. This is the best way to install `passvault`,
and it avoids the Windows "`passvault` is not recognized" problem entirely:

```bash
# install pipx if you don't have it
python -m pip install --user pipx
python -m pipx ensurepath   # adds pipx's bin dir to PATH; restart your terminal after

# then install passvault
pipx install passvault-cli
passvault init
```

### Option 2 — pip

```bash
pip install passvault-cli
```

> **Windows note:** with a plain `pip install`, the `passvault.exe` launcher
> lands in your Python `Scripts\` directory (e.g.
> `...\Python313\Scripts\`), which is often **not** on your PATH — so running
> `passvault` gives "command not found" / "is not recognized". Either:
>
> 1. add that `Scripts\` directory to your PATH, or
> 2. skip PATH entirely and run the CLI as a module:
>
>    ```bash
>    python -m passvault init
>    ```
>
>    The `-m` form works with every install method, on every OS.

### Option 3 — from source

```bash
git clone https://github.com/Ajeet2005/passvault.git
cd passvault
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e .
```

Requires Python 3.10+.

### `py` vs `python` — which one do I type?

Both commands run Python; which one you have depends on your OS and how Python
was installed:

- **`py` — Windows only.** The Python Launcher that ships with the official
  [python.org](https://www.python.org/downloads/) installer. It always finds
  your newest Python, even when `python` itself is not on your PATH — so if
  `python` gives "not recognized" but `py` works, use `py`.
- **`python`** — Windows, when "Add Python to PATH" was ticked during install;
  also the usual alias on Linux.
- **`python3`** — macOS and most Linux distros. There is no `py` launcher
  outside Windows.

Same command, three dialects:

```bash
py -m pip install --user pipx        # Windows (python not on PATH)
python -m pip install --user pipx    # Windows (on PATH) or Linux
python3 -m pip install --user pipx   # macOS / most Linux
```

And everywhere this README says `python -m passvault <command>`, Windows users
can equivalently type `py -m passvault <command>`.

### Uninstalling

Two commands, depending on how you installed it:

```bash
# installed with pipx
pipx uninstall passvault-cli

# installed with pip
pip uninstall passvault-cli
```

Uninstalling removes the program only — your vault file is left untouched, so
you can reinstall any time and pick up right where you left off.

## Usage

All commands below also work as `python -m passvault <command>` (or
`py -m passvault ...` on Windows) if the `passvault` command itself is not on
your PATH.

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

## 🧑‍💻 Contributing

Contributions are very welcome — a bug fix in the vault, a tougher test for the
generator, or a clearer sentence in this README all count.

1. Fork this repository.
2. Create your feature branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m 'Add feature'`.
4. Push the branch: `git push origin feature-name`.
5. Open a pull request and tell us what changed and why.

Please keep the code clean and readable, and run the test suite before
submitting — the same way PassVault refuses a wrong master password, we'd
rather catch a breaking change before it lands. 🔐

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
