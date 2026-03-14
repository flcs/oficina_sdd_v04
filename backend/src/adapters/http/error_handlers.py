"""Shared exception types and neutral HTTP error handlers.

HTTP semantics (per spec):
  400 — invalid payload (missing/empty/malformed fields)
  401 — invalid credentials OR locked account (neutral, no enumeration)
  503 — transient auth dependency unavailability (+ Retry-After header)
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


# ── Domain exceptions ─────────────────────────────────────────────────────────

class AuthenticationError(Exception):
    """Raised when credentials are invalid or the account is locked.

    Always maps to 401 with a neutral message to prevent account enumeration.
    """


class InvalidPayloadError(Exception):
    """Raised when the request payload fails structural validation.

    Maps to 400.
    """


class ServiceUnavailableError(Exception):
    """Raised when a transient dependency (e.g., DB) prevents authentication.

    Maps to 503 with a Retry-After header.
    """

    def __init__(self, message: str = "Service temporarily unavailable", retry_after: int = 30) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class AccountMustChangePasswordError(Exception):
    """Raised when an authenticated account must change its password first."""


# ── Neutral error response body ───────────────────────────────────────────────

_NEUTRAL_AUTH_MSG = "Invalid credentials or account unavailable."
_PAYLOAD_INVALID_MSG = "Request payload is invalid or missing required fields."
_UNAVAILABLE_MSG = "Authentication service temporarily unavailable. Please retry later."


# ── FastAPI exception handlers ────────────────────────────────────────────────

async def authentication_error_handler(
    _request: Request, exc: AuthenticationError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": _NEUTRAL_AUTH_MSG},
    )


async def invalid_payload_error_handler(
    _request: Request, exc: InvalidPayloadError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": _PAYLOAD_INVALID_MSG},
    )


async def service_unavailable_error_handler(
    _request: Request, exc: ServiceUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": _UNAVAILABLE_MSG},
        headers={"Retry-After": str(exc.retry_after)},
    )


def register_error_handlers(app: object) -> None:
    """Register all domain exception handlers on a FastAPI app instance."""
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidPayloadError, invalid_payload_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_error_handler)  # type: ignore[arg-type]
