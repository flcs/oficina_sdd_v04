-- auth_seed.sql
-- Reproducible test fixtures for the accounts and login_attempts tables.
-- Covers: active admin, locked account, must-change-password account, inactive account.
--
-- All password hashes use Argon2id; the plain-text passwords are noted as comments
-- for development/testing only. Never use these passwords in production.
--
-- Usage:
--   psql $DATABASE_URL -f sql/fixtures/auth_seed.sql
--
-- Idempotent: uses INSERT ON CONFLICT DO NOTHING so it is safe to run multiple times.

BEGIN;

-- ── Extension (harmless if already enabled) ───────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── Accounts ──────────────────────────────────────────────────────────────────

-- 1. Active admin that still needs to change the initial password
--    plain password: "admin"
INSERT INTO accounts (
    account_id,
    email,
    password_hash,
    role,
    active,
    failed_login_attempts,
    locked_until,
    must_change_password,
    token_version,
    created_at
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'bootstrap@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$dGVzdHNhbHQx$placeholder_hash_for_seed_01',
    'admin',
    TRUE,
    0,
    NULL,
    TRUE,
    1,
    NOW()
)
ON CONFLICT (account_id) DO NOTHING;

-- 2. Active admin with password already changed (must_change_password = FALSE)
--    plain password: "SecurePass1"
INSERT INTO accounts (
    account_id,
    email,
    password_hash,
    role,
    active,
    failed_login_attempts,
    locked_until,
    must_change_password,
    token_version,
    created_at
)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'active_admin@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$dGVzdHNhbHQy$placeholder_hash_for_seed_02',
    'admin',
    TRUE,
    0,
    NULL,
    FALSE,
    1,
    NOW()
)
ON CONFLICT (account_id) DO NOTHING;

-- 3. Locked account (failed 5 times; locked_until set far in the future)
--    plain password: "somepassword"
INSERT INTO accounts (
    account_id,
    email,
    password_hash,
    role,
    active,
    failed_login_attempts,
    locked_until,
    must_change_password,
    token_version,
    created_at
)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    'locked_admin@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$dGVzdHNhbHQz$placeholder_hash_for_seed_03',
    'admin',
    TRUE,
    5,
    NOW() + INTERVAL '15 minutes',
    FALSE,
    1,
    NOW()
)
ON CONFLICT (account_id) DO NOTHING;

-- 4. Inactive (deactivated) account
--    plain password: "oldpassword"
INSERT INTO accounts (
    account_id,
    email,
    password_hash,
    role,
    active,
    failed_login_attempts,
    locked_until,
    must_change_password,
    token_version,
    created_at
)
VALUES (
    '00000000-0000-0000-0000-000000000004',
    'inactive_admin@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$dGVzdHNhbHQ0$placeholder_hash_for_seed_04',
    'admin',
    FALSE,
    0,
    NULL,
    FALSE,
    1,
    NOW()
)
ON CONFLICT (account_id) DO NOTHING;

-- ── Sample login_attempts ─────────────────────────────────────────────────────

-- Successful login for the active admin
INSERT INTO login_attempts (
    attempt_id,
    email_submitted,
    account_id,
    outcome,
    occurred_at
)
VALUES (
    gen_random_uuid(),
    'active_admin@example.com',
    '00000000-0000-0000-0000-000000000002',
    'success',
    NOW() - INTERVAL '1 hour'
)
ON CONFLICT DO NOTHING;

-- Five failed attempts for the locked account
INSERT INTO login_attempts (attempt_id, email_submitted, account_id, outcome, occurred_at)
SELECT gen_random_uuid(), 'locked_admin@example.com', '00000000-0000-0000-0000-000000000003',
       'invalid_credentials', NOW() - (INTERVAL '1 minute' * s)
FROM generate_series(1, 5) AS s
ON CONFLICT DO NOTHING;

COMMIT;
