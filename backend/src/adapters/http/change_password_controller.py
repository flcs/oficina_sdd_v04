"""POST /auth/change-initial-password controller.

HTTP contract:
  200 — password changed successfully
  400 — invalid payload
  401 — missing/invalid token OR wrong current password
  409 — account does not require initial password change
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from adapters.http.error_handlers import AuthenticationError, InvalidPayloadError
from application.dto.auth_dto import ChangeInitialPasswordRequest
from application.use_cases.change_initial_password import (
    ChangeInitialPassword,
    PasswordChangeForbiddenError,
)

router = APIRouter()


@router.post("/change-initial-password")
async def change_initial_password(
    request: Request, body: dict[str, object]
) -> JSONResponse:
    """Change the initial password for a provisioned account.

    Requires ``Authorization: Bearer <token>`` header.
    The token must correspond to an account with must_change_password=True.
    """
    # ── Token validation ──────────────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")
    token = auth_header[len("Bearer "):]

    from application.ports.auth_ports import TokenService

    token_svc: TokenService = request.app.state.token_svc
    try:
        claims = token_svc.decode_access_token(token)
    except ValueError as exc:
        raise AuthenticationError("Token validation failed") from exc

    try:
        account_id = uuid.UUID(str(claims.get("sub", "")))
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc

    # ── Payload validation ────────────────────────────────────────────────────
    try:
        payload = ChangeInitialPasswordRequest.model_validate(body)
    except (ValidationError, ValueError) as exc:
        raise InvalidPayloadError(str(exc)) from exc

    # ── Delegate to use case ──────────────────────────────────────────────────
    use_case: ChangeInitialPassword = request.app.state.change_initial_password
    try:
        use_case.execute(
            account_id=account_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except PasswordChangeForbiddenError as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": "Account does not require an initial password change."},
        )

    return JSONResponse(
        status_code=200,
        content={"detail": "Password changed successfully."},
    )
