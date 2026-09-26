"""Password generation using the :mod:`secrets` module.

Everything here is cryptographically random. ``random`` is never used.
"""

from __future__ import annotations

import secrets
import string

__all__ = ["generate_password", "SYMBOLS"]

#: Symbols offered when ``use_symbols`` is enabled.
SYMBOLS = "!@#$%^&*()-_=+[]{}<>?,.:;/"

_LOWERCASE = string.ascii_lowercase
_UPPERCASE = string.ascii_uppercase
_DIGITS = string.digits


def generate_password(
    length: int = 16,
    use_symbols: bool = True,
    use_digits: bool = True,
) -> str:
    """Return a random password of ``length`` characters.

    At least one character from every enabled class is guaranteed to appear
    (lowercase and uppercase are always enabled).

    Raises :class:`ValueError` if ``length`` is too short to include one
    character from each requested class, or if it is not positive.
    """
    pools = [_LOWERCASE, _UPPERCASE]
    if use_digits:
        pools.append(_DIGITS)
    if use_symbols:
        pools.append(SYMBOLS)

    if length < len(pools):
        raise ValueError(
            f"length must be at least {len(pools)} to include one character "
            f"from each requested class (got {length})"
        )

    alphabet = "".join(pools)

    # Rejection-sample until every requested class is represented.
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(ch in pool for ch in password) for pool in pools):
            return password
