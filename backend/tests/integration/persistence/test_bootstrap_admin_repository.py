"""Integration tests for idempotent bootstrap and inactive-account recovery.

Requires a live PostgreSQL database.
Set DATABASE_URL before running:

  pytest tests/integration/persistence/test_bootstrap_admin_repository.py -m integration

TDD: written before T030 (bootstrap repository implementation).
"""

from __future__ import annotations

import os
import uuid

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


def _unique_email() -> str:
    return f"bootstrap-{uuid.uuid4().hex[:8]}@empresa.com"


class TestBootstrapIdempotence:
    def test_creates_account_on_first_call(self, uow: object) -> None:
        from adapters.persistence.account_repository_bootstrap import PostgresBootstrapRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        email = _unique_email()

        try:
            with uow:
                repo = PostgresBootstrapRepository(uow)
                action = repo.bootstrap_admin(email, "hashed:admin", "admin")
                uow.commit()
            assert action == "created"
        finally:
            with uow:
                uow.connection.execute(
                    "DELETE FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email,)
                )
                uow.commit()

    def test_preserves_existing_admin_on_second_call(self, uow: object) -> None:
        from adapters.persistence.account_repository_bootstrap import PostgresBootstrapRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        email = _unique_email()

        try:
            with uow:
                repo = PostgresBootstrapRepository(uow)
                repo.bootstrap_admin(email, "hashed:admin", "admin")
                uow.commit()

            with uow:
                repo = PostgresBootstrapRepository(uow)
                action = repo.bootstrap_admin(email, "hashed:admin", "admin")
                uow.commit()
            assert action == "preserved"
        finally:
            with uow:
                uow.connection.execute(
                    "DELETE FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email,)
                )
                uow.commit()

    def test_no_duplicate_created_under_concurrent_bootstrap(self, uow: object) -> None:
        """INSERT ON CONFLICT ensures exactly one account regardless of race."""
        from adapters.persistence.account_repository_bootstrap import PostgresBootstrapRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        email = _unique_email()

        try:
            with uow:
                repo = PostgresBootstrapRepository(uow)
                for _ in range(3):
                    repo.bootstrap_admin(email, "hashed:admin", "admin")
                uow.commit()

            with uow:
                count = uow.connection.execute(
                    "SELECT COUNT(*) FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))",
                    (email,),
                ).fetchone()
            assert count is not None
            assert int(count[0]) == 1
        finally:
            with uow:
                uow.connection.execute(
                    "DELETE FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email,)
                )
                uow.commit()


class TestBootstrapInactiveRecovery:
    def test_reactivates_inactive_account(self, uow: object) -> None:
        from adapters.persistence.account_repository_bootstrap import PostgresBootstrapRepository
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        assert isinstance(uow, PostgresUnitOfWork)
        email = _unique_email()

        try:
            # Create then deactivate
            with uow:
                uow.connection.execute(
                    """
                    INSERT INTO accounts (account_id, email, password_hash, role, active)
                    VALUES (%s, %s, 'hashed:admin', 'admin', false)
                    """,
                    (str(uuid.uuid4()), email),
                )
                uow.commit()

            with uow:
                repo = PostgresBootstrapRepository(uow)
                action = repo.bootstrap_admin(email, "hashed:new", "admin")
                uow.commit()

            assert action == "reactivated"

            with uow:
                row = uow.connection.execute(
                    "SELECT active, must_change_password FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))",
                    (email,),
                ).fetchone()
            assert row is not None
            assert bool(row[0]) is True
            assert bool(row[1]) is True
        finally:
            with uow:
                uow.connection.execute(
                    "DELETE FROM accounts WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email,)
                )
                uow.commit()
