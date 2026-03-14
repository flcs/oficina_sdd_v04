"""GET /auth/me identity controller.

Validates the bearer token, re-checks account state (active, locked,
must_change_password) and returns the current identity.

HTTP contract:
  200 — token valid, account active
  401 — missing/invalid token or account no longer active/locked
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adapters.http.error_handlers import AuthenticationError
from application.dto.auth_dto import IdentityResponse

router = APIRouter()


@router.get("/me", response_model=IdentityResponse)
async def get_identity(request: Request) -> JSONResponse:
    """Return the current authenticated user's identity.

    Requires ``Authorization: Bearer <token>`` header.
    """
    # ── Extract token ─────────────────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")
    token = auth_header[len("Bearer "):]

    # ── Decode and validate JWT ───────────────────────────────────────────────
    from application.ports.auth_ports import TokenService

    token_svc: TokenService = request.app.state.token_svc
    try:
        claims = token_svc.decode_access_token(token)
    except ValueError as exc:
        raise AuthenticationError("Token validation failed") from exc

    account_id_str = str(claims.get("sub", ""))
    token_version = int(str(claims.get("token_version", -1)))

    # ── Re-check account state ────────────────────────────────────────────────
    from application.ports.auth_ports import Clock, UserAccountRepository

    repo: UserAccountRepository = request.app.state.account_repo
    clock: Clock = request.app.state.clock
    now = clock.utc_now()

    try:
        account_id = uuid.UUID(account_id_str)
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc

    account = repo.find_by_id(account_id)
    if account is None or not account.is_active():
        raise AuthenticationError("Account not found or inactive")

    if account.is_locked(now):
        raise AuthenticationError("Account temporarily locked")

    if account.token_version != token_version:
        raise AuthenticationError("Token has been revoked")

    return JSONResponse(
        status_code=200,
        content=IdentityResponse(
            account_id=str(account.account_id),
            email=str(account.email),
            role=account.role.value,
            must_change_password=account.must_change_password,
        ).model_dump(),
    )
