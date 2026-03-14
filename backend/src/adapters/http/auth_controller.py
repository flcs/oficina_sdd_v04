"""POST /auth/login controller.

Implemented in T022 (US1) and extended in T046 (US3).

HTTP contract:
  200 — valid credentials, returns bearer token
  400 — invalid payload (missing/empty/malformed fields)
  401 — invalid credentials or locked account (neutral, no enumeration)
  503 — transient dependency unavailability (+ Retry-After header)
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from adapters.http.error_handlers import (
    AuthenticationError,
    InvalidPayloadError,
    ServiceUnavailableError,
)
from application.dto.auth_dto import LoginRequest, LoginSuccessResponse
from application.use_cases.authenticate_user import AuthenticateUser

router = APIRouter()


@router.post("/login", response_model=LoginSuccessResponse)
async def login(request: Request, body: dict[str, object]) -> JSONResponse:
    """Authenticate a user and return a signed JWT in the response body.

    The token MUST be sent in the ``Authorization: Bearer <token>`` header
    for all subsequent requests.
    """
    # ── Input validation (400) ────────────────────────────────────────────────
    try:
        payload = LoginRequest.model_validate(body)
    except (ValidationError, ValueError) as exc:
        raise InvalidPayloadError(str(exc)) from exc

    # ── Delegate to use case (401 propagated via error handlers) ─────────────
    use_case: AuthenticateUser = request.app.state.authenticate_user
    try:
        session = use_case.execute(email=payload.email, password=payload.password)
    except AuthenticationError:
        raise
    except (psycopg.OperationalError, psycopg.DatabaseError) as exc:
        raise ServiceUnavailableError() from exc

    return JSONResponse(
        status_code=200,
        content=LoginSuccessResponse(
            access_token=session.access_token,
            token_type="bearer",
            must_change_password=session.must_change_password,
        ).model_dump(),
    )
