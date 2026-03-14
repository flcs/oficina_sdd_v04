"""Login metrics adapter (SC-001A).

Records timing metrics for the login journey so the platform observability
layer can track request-to-response latency (SC-001: p95 < 300 ms).

This adapter uses the standard ``logging`` module so it can be consumed by
any log aggregation pipeline (Datadog, Grafana Loki, CloudWatch Insights, etc.)
without introducing an additional runtime dependency.

Structured metric events are emitted to the ``metrics`` logger as JSON.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("metrics")


@dataclass
class LoginMetricsEvent:
    """Describes the timing of a single login request."""

    operation: str
    duration_ms: float
    outcome: str  # "success" | "invalid_credentials" | "locked" | "unavailable"
    account_id: Optional[str] = None
    source_ip: Optional[str] = None


class LoginMetricsAdapter:
    """Emits structured timing metrics for the login endpoint.

    Usage example::

        adapter = LoginMetricsAdapter()
        with adapter.measure_login(source_ip="1.2.3.4") as ctx:
            result = authenticate_user.execute(email, password)
            ctx.outcome = "success"
            ctx.account_id = str(result.account_id)
    """

    def emit(self, event: LoginMetricsEvent) -> None:
        entry = {
            "metric": "login_latency_ms",
            "operation": event.operation,
            "duration_ms": round(event.duration_ms, 3),
            "outcome": event.outcome,
            "account_id": event.account_id,
            "source_ip": event.source_ip,
        }
        logger.info(json.dumps(entry))

    @contextmanager
    def measure_login(
        self, *, source_ip: Optional[str] = None
    ) -> Generator["_MeasureContext", None, None]:
        """Context manager that records login request duration in milliseconds."""
        ctx = _MeasureContext(source_ip=source_ip)
        start = time.perf_counter()
        try:
            yield ctx
        finally:
            duration_ms = (time.perf_counter() - start) * 1_000
            self.emit(
                LoginMetricsEvent(
                    operation="login",
                    duration_ms=duration_ms,
                    outcome=ctx.outcome,
                    account_id=ctx.account_id,
                    source_ip=source_ip,
                )
            )


@dataclass
class _MeasureContext:
    """Mutable context updated by the caller to record outcome and account."""

    source_ip: Optional[str] = None
    outcome: str = "unknown"
    account_id: Optional[str] = None
