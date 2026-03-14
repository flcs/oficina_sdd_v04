"""psycopg3 connection pool and unit-of-work adapter.

Wraps psycopg_pool.ConnectionPool and exposes a UnitOfWork that manages a
single transactional connection for each use-case invocation.
"""

from __future__ import annotations

from types import TracebackType
from typing import Optional

import psycopg
import psycopg_pool

from application.ports.auth_ports import UnitOfWork


class PostgresUnitOfWork(UnitOfWork):
    """Transactional boundary backed by a psycopg3 connection from a pool."""

    def __init__(self, pool: psycopg_pool.ConnectionPool[psycopg.Connection[psycopg.rows.TupleRow]]) -> None:
        self._pool = pool
        self._conn: Optional[psycopg.Connection[psycopg.rows.TupleRow]] = None

    # ── UnitOfWork protocol ────────────────────────────────────────────────────

    def __enter__(self) -> "PostgresUnitOfWork":
        self._conn = self._pool.getconn()
        self._conn.autocommit = False
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            if self._conn is not None:
                self._pool.putconn(self._conn)
                self._conn = None
        return False

    def commit(self) -> None:
        self._require_connection().commit()

    def rollback(self) -> None:
        self._require_connection().rollback()

    # ── Internal helpers ───────────────────────────────────────────────────────

    @property
    def connection(self) -> psycopg.Connection[psycopg.rows.TupleRow]:
        return self._require_connection()

    def _require_connection(self) -> psycopg.Connection[psycopg.rows.TupleRow]:
        if self._conn is None:
            raise RuntimeError(
                "PostgresUnitOfWork must be used as a context manager."
            )
        return self._conn


def build_connection_pool(dsn: str, min_size: int = 2, max_size: int = 10) -> psycopg_pool.ConnectionPool[psycopg.Connection[psycopg.rows.TupleRow]]:
    """Create and open a psycopg3 connection pool."""
    pool: psycopg_pool.ConnectionPool[psycopg.Connection[psycopg.rows.TupleRow]] = psycopg_pool.ConnectionPool(
        conninfo=dsn,
        min_size=min_size,
        max_size=max_size,
        open=True,
    )
    return pool
