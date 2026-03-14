"""JWT token service adapter using PyJWT.

Creates short-lived access tokens and validates them.  Tokens carry:
  sub, iss, aud, exp, iat, jti, role, must_change_password, token_version
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from application.ports.auth_ports import Clock, TokenService
from domain.entities.account import AuthSession


class JwtTokenService(TokenService):
    """PyJWT-backed token service."""

    _ALGORITHM = "HS256"
    _ACCESS_TOKEN_MINUTES = 30

    def __init__(
        self,
        secret_key: str,
        issuer: str,
        audience: str,
        clock: Clock,
    ) -> None:
        if not secret_key:
            raise ValueError("secret_key must not be empty")
        self._secret = secret_key
        self._issuer = issuer
        self._audience = audience
        self._clock = clock

    # ── TokenService ──────────────────────────────────────────────────────────

    def create_access_token(
        self,
        account_id: uuid.UUID,
        role: str,
        must_change_password: bool,
        token_version: int,
    ) -> AuthSession:
        now = self._clock.utc_now()
        expires_at = now + timedelta(minutes=self._ACCESS_TOKEN_MINUTES)
        payload: dict[str, Any] = {
            "sub": str(account_id),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": str(uuid.uuid4()),
            "role": role,
            "must_change_password": must_change_password,
            "token_version": token_version,
        }
        token = jwt.encode(payload, self._secret, algorithm=self._ALGORITHM)
        return AuthSession(
            account_id=account_id,
            access_token=token,
            issued_at=now,
            expires_at=expires_at,
            must_change_password=must_change_password,
        )

    def decode_access_token(self, token: str) -> dict[str, object]:
        try:
            decoded: dict[str, object] = jwt.decode(
                token,
                self._secret,
                algorithms=[self._ALGORITHM],
                audience=self._audience,
                issuer=self._issuer,
            )
            return decoded
        except jwt.PyJWTError as exc:
            raise ValueError(f"Invalid token: {exc}") from exc
