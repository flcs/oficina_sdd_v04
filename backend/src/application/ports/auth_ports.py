"""Application-layer ports (abstractions) for the authentication feature.

All business rules depend on these interfaces — never on concrete adapters.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from domain.entities.account import Account, AuthSession, LoginAttempt


class UserAccountRepository(ABC):
    """Read/write access to user account persistence."""

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[Account]:
        """Return the account matching the normalised email, or None."""

    @abstractmethod
    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        """Return the account with the given id, or None."""

    @abstractmethod
    def save(self, account: Account) -> None:
        """Persist a new or updated account."""

    @abstractmethod
    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        """Atomically increment failed_login_attempts and optionally set locked_until."""

    @abstractmethod
    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        """Zero out failed_login_attempts and clear locked_until."""

    @abstractmethod
    def bootstrap_admin(
        self, email: str, password_hash: str, role: str
    ) -> str:
        """Idempotent admin bootstrap. Returns the action taken: 'created',
        'preserved', 'reactivated', or 'normalized'."""

    @abstractmethod
    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        """Persist a login attempt event for audit purposes."""


class PasswordHasher(ABC):
    """Abstraction over password hashing and verification."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Return an Argon2id hash of the plain password."""

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return True if the plain password matches the hash."""


class TokenService(ABC):
    """Abstraction over JWT creation and validation."""

    @abstractmethod
    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        """Create and return a signed JWT wrapped in an AuthSession."""

    @abstractmethod
    def decode_access_token(self, token: str) -> dict[str, object]:
        """Decode and validate the JWT; raise ValueError on failure."""


class Clock(ABC):
    """Abstraction over time to allow deterministic testing."""

    @abstractmethod
    def utc_now(self) -> datetime:
        """Return the current UTC time as a timezone-aware datetime."""


class AuditLogPort(ABC):
    """Abstraction over operational audit logging."""

    @abstractmethod
    def log_login_attempt(self, attempt: LoginAttempt) -> None:
        """Emit a structured audit log entry for a login attempt."""


class UnitOfWork(ABC):
    """Transactional boundary abstraction."""

    @abstractmethod
    def __enter__(self) -> "UnitOfWork":
        ...

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: object,
    ) -> bool:
        ...

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back the current transaction."""
