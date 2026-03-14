"""Startup hook: bootstrap default admin account on application start.

Wired into FastAPI lifespan in app_factory.py.
Full BootstrapDefaultAdmin use case is implemented in T031.
"""

from __future__ import annotations

import logging

import psycopg
import psycopg_pool

from adapters.security.argon2_password_hasher import Argon2PasswordHasher
from bootstrap.config import Settings

logger = logging.getLogger(__name__)


async def bootstrap_admin_on_startup(
    pool: psycopg_pool.ConnectionPool[psycopg.Connection[psycopg.rows.TupleRow]],
    hasher: Argon2PasswordHasher,
    settings: Settings,
) -> None:
    """Run the idempotent admin bootstrap during application startup."""
    try:
        from adapters.persistence.account_repository_bootstrap import (
            PostgresBootstrapRepository,
        )
        from application.use_cases.bootstrap_default_admin import BootstrapDefaultAdmin
        from adapters.persistence.postgres_uow import PostgresUnitOfWork

        uow = PostgresUnitOfWork(pool)
        repo = PostgresBootstrapRepository(uow)
        use_case = BootstrapDefaultAdmin(repo, hasher)
        event = use_case.execute(
            email=settings.bootstrap_admin_email,
            initial_password=settings.bootstrap_admin_initial_password,
        )
        logger.info(
            "Admin bootstrap completed",
            extra={"action": event.action, "email": event.target_email},
        )
    except Exception as exc:  # pragma: no cover
        logger.error("Admin bootstrap failed: %s", exc)
        raise
