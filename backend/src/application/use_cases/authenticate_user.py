"""AuthenticateUser use case.

Authenticates a user by email and password against the port abstractions.
Enforces lockout policy via LoginAttemptPolicy (T045: US3).

Business rules:
  - Account must exist and be active.
  - Password must verify against Argon2id hash.
  - Successful login resets failed_login_attempts counter.
  - Failed login increments failed_login_attempts.
  - After 5 consecutive failures, locked_until is set to now + 15 min.
  - Returns AuthSession with JWT in bearer token.
  - Always raises AuthenticationError with neutral message on failure.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from adapters.http.error_handlers import AuthenticationError
from application.ports.auth_ports import (
    AuditLogPort,
    Clock,
    PasswordHasher,
    TokenService,
    UserAccountRepository,
)
from domain.entities.account import AccountOutcome, AuthSession, LoginAttempt
from domain.services.login_attempt_policy import LoginAttemptPolicy


class AuthenticateUser:
    """Authenticate a user by email and password.

    All collaboration is via ports; no concrete adapter is referenced.
    LoginAttemptPolicy is optional — when not provided a default instance is used.
    """

    def __init__(
        self,
        repo: UserAccountRepository,
        hasher: PasswordHasher,
        token_svc: TokenService,
        clock: Clock,
        audit_log: AuditLogPort,
        policy: Optional[LoginAttemptPolicy] = None,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_svc = token_svc
        self._clock = clock
        self._audit_log = audit_log
        self._policy = policy if policy is not None else LoginAttemptPolicy()

    def execute(self, email: str, password: str) -> AuthSession:
        """Return an AuthSession on success; raise AuthenticationError on failure."""
        now = self._clock.utc_now()
        normalised_email = email.strip().lower()

        account = self._repo.find_by_email(normalised_email)

        # ── Account not found: raise neutral error ────────────────────────────
        if account is None:
            self._audit_log.log_login_attempt(
                LoginAttempt(
                    attempt_id=uuid.uuid4(),
                    email_submitted=email,
                    account_id=None,
                    outcome=AccountOutcome.INVALID_CREDENTIALS,
                    occurred_at=now,
                )
            )
            raise AuthenticationError()

        # ── Inactive account: neutral error (no enumeration) ──────────────────
        if not account.is_active():
            self._audit_log.log_login_attempt(
                LoginAttempt(
                    attempt_id=uuid.uuid4(),
                    email_submitted=email,
                    account_id=account.account_id,
                    outcome=AccountOutcome.INVALID_CREDENTIALS,
                    occurred_at=now,
                )
            )
            raise AuthenticationError()

        # ── Lockout check (extended in T045 via LoginAttemptPolicy) ──────────
        if account.is_locked(now):
            self._audit_log.log_login_attempt(
                LoginAttempt(
                    attempt_id=uuid.uuid4(),
                    email_submitted=email,
                    account_id=account.account_id,
                    outcome=AccountOutcome.LOCKED,
                    occurred_at=now,
                )
            )
            raise AuthenticationError()

        # ── Password verification ─────────────────────────────────────────────
        if not self._hasher.verify(password, account.password_hash):
            # Compute new attempt count (current + 1) to decide lockout
            new_attempt_count = account.failed_login_attempts + 1
            locked_until: Optional[datetime] = None
            if self._policy.should_lock(new_attempt_count):
                locked_until = now + self._policy.lockout_duration()

            self._repo.increment_failed_attempts(
                account_id=account.account_id,
                locked_until=locked_until,
            )
            self._audit_log.log_login_attempt(
                LoginAttempt(
                    attempt_id=uuid.uuid4(),
                    email_submitted=email,
                    account_id=account.account_id,
                    outcome=AccountOutcome.INVALID_CREDENTIALS,
                    occurred_at=now,
                )
            )
            raise AuthenticationError()

        # ── Success ───────────────────────────────────────────────────────────
        self._repo.reset_failed_attempts(account.account_id)
        session = self._token_svc.create_access_token(
            account_id=account.account_id,
            role=account.role.value,
            must_change_password=account.must_change_password,
            token_version=account.token_version,
        )
        self._audit_log.log_login_attempt(
            LoginAttempt(
                attempt_id=uuid.uuid4(),
                email_submitted=email,
                account_id=account.account_id,
                outcome=AccountOutcome.SUCCESS,
                occurred_at=now,
            )
        )
        return session
