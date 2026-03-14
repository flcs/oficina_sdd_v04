-- Migration: 001_auth_base
-- Creates the base accounts and login_attempts tables used by the
-- authentication feature (feature 001-login-admin).
--
-- Requirements covered: FR-001 to FR-010, SC-003A, SC-003C, SC-003D

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── accounts ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    account_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT        NOT NULL,
    password_hash       TEXT        NOT NULL,
    role                TEXT        NOT NULL DEFAULT 'user',
    active              BOOLEAN     NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN    NOT NULL DEFAULT FALSE,
    failed_login_attempts INT       NOT NULL DEFAULT 0 CHECK (failed_login_attempts >= 0),
    locked_until        TIMESTAMPTZ,
    token_version       INT         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ,
    -- Normalised e-mail uniqueness: LOWER(TRIM(email))
    CONSTRAINT accounts_email_ci_unique UNIQUE (email)
);

-- Case-insensitive lookup index
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_email_lower
    ON accounts (LOWER(TRIM(email)));

-- ── login_attempts ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email_submitted TEXT        NOT NULL,
    account_id      UUID        REFERENCES accounts(account_id) ON DELETE SET NULL,
    outcome         TEXT        NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ip       TEXT,
    user_agent      TEXT,
    CONSTRAINT login_attempts_outcome_check
        CHECK (outcome IN (
            'success',
            'invalid_credentials',
            'locked',
            'unavailable',
            'must_change_password'
        ))
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_account_id
    ON login_attempts (account_id, occurred_at DESC);

COMMIT;
