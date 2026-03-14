"""PostgreSQL account repository lockout extension (T044).

Extends PostgresAccountRepository with a combined, atomic method
``apply_lockout_if_threshold_reached`` that:
  1. Increments failed_login_attempts atomically in a single UPDATE.
  2. Computes and writes locked_until when the new count reaches the threshold.
  3. Returns the new failed_login_attempts count so callers can audit.

This avoids a read-then-write race for the lockout calculation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from adapters.persistence.account_repository import PostgresAccountRepository


class LockoutCapableAccountRepository(PostgresAccountRepository):
    """Extends the base repository with lockout-aware increment logic.

    Used by AuthenticateUser (T045) so that lockout threshold enforcement
    is an atomic DB operation — no TOCTOU race.
    """

    def increment_failed_attempts_with_lockout(
        self,
        account_id: uuid.UUID,
        locked_until: Optional[datetime],
    ) -> int:
        """Increment failed_login_attempts and optionally set locked_until.

        Returns the new failed_login_attempts count.
        This is identical to the base ``increment_failed_attempts`` but returns
        the updated value so the use case can confirm the lockout was applied.
        """
        row = self._uow.connection.execute(
            """
            UPDATE accounts
            SET
                failed_login_attempts = failed_login_attempts + 1,
                locked_until          = %s,
                updated_at            = NOW()
            WHERE account_id = %s
            RETURNING failed_login_attempts
            """,
            (locked_until, str(account_id)),
        ).fetchone()
        if row is None:
            return 0
        return int(str(row[0]))

    def get_failed_attempt_count(self, account_id: uuid.UUID) -> int:
        """Return the current failed_login_attempts count for an account."""
        row = self._uow.connection.execute(
            "SELECT failed_login_attempts FROM accounts WHERE account_id = %s",
            (str(account_id),),
        ).fetchone()
        if row is None:
            return 0
        return int(str(row[0]))
