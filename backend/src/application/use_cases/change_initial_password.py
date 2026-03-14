"""ChangeInitialPassword use case.

Allows an authenticated user to change their initial password during the
mandatory first-login flow.

Business rules:
  - The account must have must_change_password=True.
  - The current_password must verify against the stored hash.
  - The new password is hashed and stored; token_version is incremented.
  - must_change_password is cleared (set to False).
  - FR-009A: No password history restriction — the admin may reuse
    the initial 'admin' password after the mandatory change.
"""

from __future__ import annotations

import uuid

from adapters.http.error_handlers import AuthenticationError
from application.ports.auth_ports import PasswordHasher, UserAccountRepository
from domain.entities.account import Account


class _PasswordChangeForbiddenError(Exception):
    """Raised when the account does not require a password change (HTTP 409)."""

    # Encode a 409-specific message so the controller can detect it.
    HTTP_STATUS = 409


class ChangeInitialPassword:
    """Change the initial password for a provisioned account."""

    def __init__(
        self,
        repo: UserAccountRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(
        self,
        account_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """Apply the password change. Raises on invalid state or credentials."""
        account = self._repo.find_by_id(account_id)
        if account is None:
            raise AuthenticationError("Account not found")

        # ── Guard: only accounts requiring a change may use this endpoint ────
        if not account.must_change_password:
            raise _PasswordChangeForbiddenError(
                "409: Account does not require an initial password change."
            )

        # ── Verify current password ───────────────────────────────────────────
        if not self._hasher.verify(current_password, account.password_hash):
            raise AuthenticationError("Current password is incorrect")

        # ── Apply the change (FR-009A: no history check) ─────────────────────
        updated = Account(
            account_id=account.account_id,
            email=account.email,
            password_hash=self._hasher.hash(new_password),
            role=account.role,
            active=account.active,
            must_change_password=False,   # ← cleared
            failed_login_attempts=0,
            locked_until=None,
            token_version=account.token_version + 1,  # ← invalidate old tokens
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
        self._repo.save(updated)


# Export so controllers can catch it
PasswordChangeForbiddenError = _PasswordChangeForbiddenError
