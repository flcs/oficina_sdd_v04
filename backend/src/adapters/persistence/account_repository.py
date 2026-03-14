"""PostgreSQL account repository — read methods for the login flow.

Implements UserAccountRepository read operations:
  - find_by_email (case-insensitive, normalised)
  - find_by_id
  - record_login_attempt
  - increment_failed_attempts
  - reset_failed_attempts

Write/bootstrap operations are in account_repository_bootstrap.py (T030).
Lockout extensions are in account_repository_lockout.py (T044).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import psycopg

from adapters.persistence.postgres_uow import PostgresUnitOfWork
from application.ports.auth_ports import UserAccountRepository
from domain.entities.account import (
    Account,
    AccountOutcome,
    AccountRole,
    Email,
    LoginAttempt,
)


class PostgresAccountRepository(UserAccountRepository):
    """psycopg3-backed account repository (read/attempt paths)."""

    def __init__(self, uow: PostgresUnitOfWork) -> None:
        self._uow = uow

    # ── Read ──────────────────────────────────────────────────────────────────

    def find_by_email(self, email: str) -> Optional[Account]:
        row = self._uow.connection.execute(
            """
            SELECT
                account_id, email, password_hash, role, active,
                must_change_password, failed_login_attempts, locked_until,
                token_version, created_at, updated_at, last_login_at
            FROM accounts
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (email,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    def find_by_id(self, account_id: uuid.UUID) -> Optional[Account]:
        row = self._uow.connection.execute(
            """
            SELECT
                account_id, email, password_hash, role, active,
                must_change_password, failed_login_attempts, locked_until,
                token_version, created_at, updated_at, last_login_at
            FROM accounts
            WHERE account_id = %s
            LIMIT 1
            """,
            (str(account_id),),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_account(row)

    # ── Write (attempt tracking) ──────────────────────────────────────────────

    def save(self, account: Account) -> None:
        self._uow.connection.execute(
            """
            UPDATE accounts
            SET
                password_hash        = %s,
                role                 = %s,
                active               = %s,
                must_change_password = %s,
                failed_login_attempts= %s,
                locked_until         = %s,
                token_version        = %s,
                updated_at           = NOW(),
                last_login_at        = %s
            WHERE account_id = %s
            """,
            (
                account.password_hash,
                account.role.value,
                account.active,
                account.must_change_password,
                account.failed_login_attempts,
                account.locked_until,
                account.token_version,
                account.last_login_at,
                str(account.account_id),
            ),
        )

    def increment_failed_attempts(
        self, account_id: uuid.UUID, locked_until: Optional[datetime]
    ) -> None:
        self._uow.connection.execute(
            """
            UPDATE accounts
            SET
                failed_login_attempts = failed_login_attempts + 1,
                locked_until          = %s,
                updated_at            = NOW()
            WHERE account_id = %s
            """,
            (locked_until, str(account_id)),
        )

    def reset_failed_attempts(self, account_id: uuid.UUID) -> None:
        self._uow.connection.execute(
            """
            UPDATE accounts
            SET
                failed_login_attempts = 0,
                locked_until          = NULL,
                updated_at            = NOW()
            WHERE account_id = %s
            """,
            (str(account_id),),
        )

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        """Delegated to PostgresBootstrapRepository (T030)."""
        raise NotImplementedError(  # pragma: no cover
            "Use PostgresBootstrapRepository.bootstrap_admin instead."
        )

    def record_login_attempt(self, attempt: LoginAttempt) -> None:
        self._uow.connection.execute(
            """
            INSERT INTO login_attempts
                (attempt_id, email_submitted, account_id, outcome, occurred_at,
                 source_ip, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(attempt.attempt_id),
                attempt.email_submitted,
                str(attempt.account_id) if attempt.account_id else None,
                attempt.outcome.value,
                attempt.occurred_at,
                attempt.source_ip,
                attempt.user_agent,
            ),
        )

    # ── Mapping ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_account(row: tuple[object, ...]) -> Account:  # type: ignore[type-arg]
        (
            account_id,
            email,
            password_hash,
            role,
            active,
            must_change_password,
            failed_login_attempts,
            locked_until,
            token_version,
            created_at,
            updated_at,
            last_login_at,
        ) = row
        return Account(
            account_id=uuid.UUID(str(account_id)),
            email=Email(str(email)),
            password_hash=str(password_hash),
            role=AccountRole(str(role)),
            active=bool(active),
            must_change_password=bool(must_change_password),
            failed_login_attempts=int(str(failed_login_attempts)),
            locked_until=locked_until if locked_until is None else datetime.fromisoformat(str(locked_until)) if isinstance(locked_until, str) else locked_until,  # type: ignore[arg-type]
            token_version=int(str(token_version)),
            created_at=created_at,  # type: ignore[arg-type]
            updated_at=updated_at,  # type: ignore[arg-type]
            last_login_at=last_login_at,  # type: ignore[arg-type]
        )
