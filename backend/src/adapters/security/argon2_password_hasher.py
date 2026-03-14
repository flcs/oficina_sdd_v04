"""Argon2id password hasher adapter using argon2-cffi."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from application.ports.auth_ports import PasswordHasher as PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    """Argon2id-backed password hasher.

    Uses argon2-cffi with conservative defaults suitable for an authentication
    service.  The same instance is safe to reuse across requests.
    """

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, plain_password: str) -> str:
        """Return an Argon2id PHC-encoded hash."""
        return self._hasher.hash(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return True if plain_password matches; False on mismatch."""
        try:
            return self._hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
