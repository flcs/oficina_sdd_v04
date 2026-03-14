"""BootstrapDefaultAdmin use case.

Provisions the default admin account idempotently.  This use case is
invoked once during application startup and may be called multiple times
without causing duplicate accounts or data corruption.

Business rules:
  - If no admin account exists: create it.
  - If the account exists and is active: preserve it (no-op).
  - If the account exists but is inactive/inconsistent: reactivate it
    and force a password reset.
  - The initial password is always hashed before storage.
  - must_change_password is set to True on creation or reactivation.
"""

from __future__ import annotations

from application.ports.auth_ports import PasswordHasher, UserAccountRepository
from domain.entities.account import AdminBootstrapEvent
from domain.entities.account import utc_now


class BootstrapDefaultAdmin:
    """Idempotently provision the default admin account."""

    def __init__(
        self,
        repo: UserAccountRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(self, email: str, initial_password: str) -> AdminBootstrapEvent:
        """Run the bootstrap and return an event describing the action taken."""
        password_hash = self._hasher.hash(initial_password)
        action = self._repo.bootstrap_admin(
            email=email,
            password_hash=password_hash,
            role="admin",
        )
        return AdminBootstrapEvent(
            target_email=email,
            action=action,
            performed_at=utc_now(),
            requires_password_reset=action in ("created", "reactivated", "normalized"),
        )
