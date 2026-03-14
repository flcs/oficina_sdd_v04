"""DTOs for the authentication endpoints.

Strict Pydantic v2 models used as request/response bodies.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("email must not be empty or whitespace-only")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", stripped.lower()):
            raise ValueError("email is not a valid e-mail address")
        return stripped.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("password must not be empty or whitespace-only")
        return value


class LoginSuccessResponse(BaseModel):
    """Response body for a successful POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class IdentityResponse(BaseModel):
    """Response body for GET /auth/me."""

    account_id: str
    email: str
    role: str
    must_change_password: bool


class ChangeInitialPasswordRequest(BaseModel):
    """Payload for POST /auth/change-initial-password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("new_password must not be empty")
        if len(value) < 8:
            raise ValueError("new_password must be at least 8 characters")
        return value
