"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All required configuration, sourced from environment variables.

    Required in production:
      DATABASE_URL, JWT_SECRET_KEY, JWT_ISSUER, JWT_AUDIENCE
    """

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_issuer: str = Field(default="login-admin-backend", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="login-admin-frontend", alias="JWT_AUDIENCE")
    db_pool_min_size: int = Field(default=2, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=10, alias="DB_POOL_MAX_SIZE")
    bootstrap_admin_email: str = Field(
        default="admin@empresa.com", alias="BOOTSTRAP_ADMIN_EMAIL"
    )
    bootstrap_admin_initial_password: str = Field(
        default="admin", alias="BOOTSTRAP_ADMIN_INITIAL_PASSWORD"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        case_sensitive=True,
    )
