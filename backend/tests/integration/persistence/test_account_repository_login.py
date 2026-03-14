"""Integration tests for account repository — login path.

Requires a live PostgreSQL database.
Set DATABASE_URL environment variable before running:

  export DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
  pytest tests/integration/persistence/test_account_repository_login.py -m integration

TDD: written before the repository implementation (T020).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_pool() -> object:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set — skipping integration tests")

    from adapters.persistence.postgres_uow import build_connection_pool

    pool = build_connection_pool(database_url, min_size=1, max_size=3)
    yield pool
    pool.close()


@pytest.fixture()
def uow(db_pool: object) -> object:
    from adapters.persistence.postgres_uow import PostgresUnitOfWork
    return PostgresUnitOfWork(db_pool)  # type: ignore[arg-type]


@pytest.fixture()
def clean_account(uow: object) -> object:
    """Insert a test account and clean up after the test."""
    from adapters.persistence.postgres_uow import PostgresUnitOfWork
    from argon2 import PasswordHasher as ArgonHasher

    uow_ = uow
    assert isinstance(uow_, PostgresUnitOfWork)
    account_id = uuid.uuid4()
    email = f"test-{uuid.uuid4().hex[:8]}@empresa.com"
    hasher = ArgonHasher()
    password_hash = hasher.hash("test-password")

    with uow_:
        uow_.connection.execute(
            """
            INSERT INTO accounts (account_id, email, password_hash, role, active)
            VALUES (%s, %s, %s, 'user', true)
            """,
            (str(account_id), email, password_hash),
        )
        uow_.commit()

    yield {"account_id": account_id, "email": email, "password_hash": password_hash}

    with uow_:
        uow_.connection.execute(
            "DELETE FROM accounts WHERE account_id = %s", (str(account_id),)
        )
        uow_.commit()


class TestAccountRepositoryLoginRead:
    def test_find_by_email_returns_account(self, uow: object, clean_account: dict) -> None:  # type: ignore[type-arg]
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(clean_account["email"])

        assert account is not None
        assert account.account_id == clean_account["account_id"]
        assert account.active is True

    def test_find_by_email_normalises_case(self, uow: object, clean_account: dict) -> None:  # type: ignore[type-arg]
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        email_upper = clean_account["email"].upper()
        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(email_upper)

        assert account is not None

    def test_find_by_email_returns_none_for_unknown(self, uow: object) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        with uow:
            repo = PostgresAccountRepository(uow)
            result = repo.find_by_email("nobody@nowhere.com")

        assert result is None


class TestAccountRepositoryPasswordVerification:
    def test_stored_hash_validates_against_correct_password(
        self, uow: object, clean_account: dict  # type: ignore[type-arg]
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.security.argon2_password_hasher import Argon2PasswordHasher
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(clean_account["email"])

        assert account is not None
        hasher = Argon2PasswordHasher()
        assert hasher.verify("test-password", account.password_hash) is True

    def test_stored_hash_rejects_wrong_password(
        self, uow: object, clean_account: dict  # type: ignore[type-arg]
    ) -> None:
        from adapters.persistence.account_repository import PostgresAccountRepository
        from adapters.security.argon2_password_hasher import Argon2PasswordHasher
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        with uow:
            repo = PostgresAccountRepository(uow)
            account = repo.find_by_email(clean_account["email"])

        assert account is not None
        hasher = Argon2PasswordHasher()
        assert hasher.verify("wrong-password", account.password_hash) is False
