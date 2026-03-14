"""System clock implementation (production)."""

from __future__ import annotations

from datetime import datetime, timezone

from application.ports.auth_ports import Clock


class SystemClock(Clock):
    """Returns the real UTC time."""

    def utc_now(self) -> datetime:
        return datetime.now(tz=timezone.utc)
