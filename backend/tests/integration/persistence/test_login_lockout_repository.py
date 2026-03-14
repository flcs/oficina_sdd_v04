"""Integration tests for failed_login_attempts increment and lockout in PostgreSQL.

Validates against a real database that:
  - increment_failed_attempts increases the counter
  - increment_failed_attempts writes locked_until when provided
  - reset_failed_attempts clears counter and locked_until
  - find_by_email returns the account with updated counter/locked_until

Requires DATABASE_URL environment variable. Skipped if not set.

TDD: written before T044 (account_repository_lockout.py extension).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.fixture
def db_pool() -> object:
    """Build a psycopg connection pool configured from DATABASE_URL."""
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping PostgreSQL integration tests")
    from adapters.persistence.postgres_uow import build_connection_pool
    pool = build_connection_pool(DATABASE_URL)
    yield pool
    pool.closeall()


@pytest.fixture
def clean_account(db_pool: object) -> object:
    """Insert a fresh test account and clean up after test."""
    account_id = uuid.uuid4()
    email = f"lockout_test_{account_id.hex[:8]}@example.com"
    password_hash = "hashed:testpassword"

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (
                    account_id, email, password_hash, role,
                    active, failed_login_attempts, must_change_password,
                    token_version, created_at
                ) VALUES (
                    %s, %s, %s, 'admin',
                    TRUE, 0, TRUE, 1, NOW()
                )
                """,
                (str(account_id), email.lower(), password_hash),
            )
        conn.commit()
    finally:
        db_pool.putconn(conn)

    yield (account_id, email)

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE account_id = %s", (str(account_id),))
        conn.commit()
    finally:
        db_pool.putconn(conn)


class TestIncrementFailedAttempts:
    """increment_failed_attempts correctly updates counter in DB."""

    def test_increments_counter(self, db_pool: object, clean_account: tuple) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        account_id, email = clean_account
        uow = PostgresUnitOfWork(db_pool)

        with uow:
            repo = PostgresAccountRepository(uow)
            repo.increment_failed_attempts(account_id=account_id, locked_until=None)
            uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email)
            assert account is not None
            assert account.failed_login_attempts == 1

    def test_increments_counter_multiple_times(
        self, db_pool: object, clean_account: tuple
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        account_id, email = clean_account
        uow = PostgresUnitOfWork(db_pool)

        for _ in range(4):
            with uow:
                repo = PostgresAccountRepository(uow)
                repo.increment_failed_attempts(account_id=account_id, locked_until=None)
                uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email)
            assert account is not None
            assert account.failed_login_attempts == 4

    def test_sets_locked_until_when_provided(
        self, db_pool: object, clean_account: tuple
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        account_id, email = clean_account
        uow = PostgresUnitOfWork(db_pool)
        locked_until = datetime(2099, 6, 1, tzinfo=timezone.utc)

        with uow:
            repo = PostgresAccountRepository(uow)
            repo.increment_failed_attempts(
                account_id=account_id, locked_until=locked_until
            )
            uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email)
            assert account is not None
            assert account.locked_until is not None
            assert account.locked_until >= locked_until - timedelta(seconds=1)

    def test_locked_until_none_does_not_set_lockout(
        self, db_pool: object, clean_account: tuple
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        account_id, email = clean_account
        uow = PostgresUnitOfWork(db_pool)

        with uow:
            repo = PostgresAccountRepository(uow)
            repo.increment_failed_attempts(account_id=account_id, locked_until=None)
            uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email)
            assert account is not None
            assert account.locked_until is None


class TestResetFailedAttempts:
    """reset_failed_attempts clears counter and locked_until."""

    def test_resets_after_increment(
        self, db_pool: object, clean_account: tuple
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        account_id, email = clean_account
        uow = PostgresUnitOfWork(db_pool)
        locked_until = datetime(2099, 6, 1, tzinfo=timezone.utc)

        with uow:
            repo = PostgresAccountRepository(uow)
            repo.increment_failed_attempts(
                account_id=account_id, locked_until=locked_until
            )
            uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            repo.reset_failed_attempts(account_id=account_id)
            uow.commit()

        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email)
            assert account is not None
            assert account.failed_login_attempts == 0
            assert account.locked_until is None
