"""Domain entities and value objects for the authentication feature."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AccountRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class AccountOutcome(str, Enum):
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    LOCKED = "locked"
    UNAVAILABLE = "unavailable"
    MUST_CHANGE_PASSWORD = "must_change_password"


@dataclass(frozen=True)
class Email:
    """Normalized, validated e-mail value object."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError(f"Invalid e-mail address: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass
class Account:
    """Represents an authenticatable user identity.

    State transitions:
    - Provisioned  → active=True, must_change_password=True
    - Active       → active=True, must_change_password=False
    - Locked       → active=True, locked_until set
    - Inactive     → active=False
    - Recovered    → active=True, must_change_password=True (from Inactive/inconsistent)
    """

    account_id: uuid.UUID
    email: Email
    password_hash: str
    role: AccountRole
    active: bool
    must_change_password: bool
    failed_login_attempts: int
    locked_until: Optional[datetime]
    token_version: int
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = field(default=None)

    def is_locked(self, now: datetime) -> bool:
        """Return True if the account is still within its lockout window."""
        if self.locked_until is None:
            return False
        return now < self.locked_until

    def is_active(self) -> bool:
        return self.active

    def requires_password_change(self) -> bool:
        return self.must_change_password


@dataclass
class AuthSession:
    """Result of a successful authentication."""

    account_id: uuid.UUID
    access_token: str
    issued_at: datetime
    expires_at: datetime
    must_change_password: bool

    def __post_init__(self) -> None:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")


@dataclass
class LoginAttempt:
    """A single login submission event."""

    attempt_id: uuid.UUID
    email_submitted: str
    account_id: Optional[uuid.UUID]
    outcome: AccountOutcome
    occurred_at: datetime
    source_ip: Optional[str] = field(default=None)
    user_agent: Optional[str] = field(default=None)


@dataclass
class AdminBootstrapEvent:
    """Records the initial admin account provisioning action."""

    target_email: str
    action: str  # "created" | "preserved" | "reactivated" | "normalized"
    performed_at: datetime
    requires_password_reset: bool


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def new_account_id() -> uuid.UUID:
    return uuid.uuid4()
