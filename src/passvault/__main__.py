"""Allow running the CLI as ``python -m passvault``.

Handy when the ``passvault`` console script is not on your PATH — a common
situation with a plain ``pip install`` on Windows, where the launcher lands in
the Python ``Scripts\\`` directory. This module makes the invocation work
regardless of how the package was installed.
"""

from __future__ import annotations

from .cli import app

if __name__ == "__main__":
    app()
