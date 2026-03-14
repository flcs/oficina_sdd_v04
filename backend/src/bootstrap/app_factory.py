"""FastAPI application factory and dependency wiring.

Composition root: all concrete adapters are instantiated here and injected
into use cases via FastAPI's dependency-injection mechanism.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from adapters.http.error_handlers import register_error_handlers
from bootstrap.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the configured FastAPI application.

    Args:
        settings: Optional settings override (useful in tests).
    """
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    app = FastAPI(
        title="Login Admin Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Lifespan (startup / shutdown) ─────────────────────────────────────────
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        from adapters.persistence.postgres_uow import build_connection_pool
        from adapters.security.argon2_password_hasher import Argon2PasswordHasher
        from adapters.security.jwt_token_service import JwtTokenService
        from adapters.observability.audit_logger import StructuredAuditLogger
        from bootstrap.startup import bootstrap_admin_on_startup
        from infrastructure.clock import SystemClock

        pool = build_connection_pool(
            settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
        clock = SystemClock()
        hasher = Argon2PasswordHasher()
        token_svc = JwtTokenService(
            secret_key=settings.jwt_secret_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            clock=clock,
        )
        audit_logger = StructuredAuditLogger()

        # Store in app state for dependency injection
        _app.state.pool = pool
        _app.state.settings = settings
        _app.state.clock = clock
        _app.state.hasher = hasher
        _app.state.token_svc = token_svc
        _app.state.audit_logger = audit_logger

        # Bootstrap default admin account
        await bootstrap_admin_on_startup(pool, hasher, settings)

        yield

        pool.close()

    app.router.lifespan_context = lifespan

    # ── Exception handlers ────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    from adapters.http.auth_controller import router as auth_router
    from adapters.http.identity_controller import router as identity_router
    from adapters.http.change_password_controller import router as change_password_router

    app.include_router(auth_router, prefix="/auth")
    app.include_router(identity_router, prefix="/auth")
    app.include_router(change_password_router, prefix="/auth")

    return app
