"""PostgreSQL account repository — bootstrap write operations.

Handles the idempotent admin account creation using INSERT ... ON CONFLICT
and recovery of inactive/inconsistent accounts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from adapters.persistence.account_repository import PostgresAccountRepository
from adapters.persistence.postgres_uow import PostgresUnitOfWork
from application.ports.auth_ports import UserAccountRepository
from domain.entities.account import Account, LoginAttempt


class PostgresBootstrapRepository(PostgresAccountRepository):
    """Extends the read repository with idempotent bootstrap write logic."""

    def bootstrap_admin(self, email: str, password_hash: str, role: str) -> str:
        """Idempotently provision the default admin account.

        Returns:
            'created'     — new account was inserted.
            'preserved'   — active account already existed, no change.
            'reactivated' — inactive/inconsistent account was recovered.
            'normalized'  — account was active but had inconsistent state fixed.
        """
        conn = self._uow.connection

        # Check if account already exists (case-insensitive)
        row = conn.execute(
            """
            SELECT account_id, active, must_change_password
            FROM accounts
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (email,),
        ).fetchone()

        if row is None:
            # ── Create new account using INSERT ON CONFLICT for idempotence ──
            conn.execute(
                """
                INSERT INTO accounts
                    (account_id, email, password_hash, role, active,
                     must_change_password, failed_login_attempts, token_version)
                VALUES (%s, %s, %s, %s, true, true, 0, 0)
                ON CONFLICT (email) DO NOTHING
                """,
                (str(uuid.uuid4()), email.strip().lower(), password_hash, role),
            )
            return "created"

        account_id_str, active, must_change_password = row
        active = bool(active)

        if active and must_change_password:
            # Already provisioned correctly
            return "preserved"

        if active and not must_change_password:
            # Active but initial password was already changed — preserve as-is
            return "preserved"

        # ── Inactive or inconsistent account — reactivate ────────────────────
        conn.execute(
            """
            UPDATE accounts
            SET
                active               = true,
                must_change_password = true,
                password_hash        = %s,
                failed_login_attempts= 0,
                locked_until         = NULL,
                updated_at           = NOW()
            WHERE account_id = %s
            """,
            (password_hash, str(account_id_str)),
        )
        return "reactivated"
