# oficina_sdd_v04 Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-13

## Active Technologies

- Python 3.12 + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings (001-login-admin)

## Project Structure

```text
backend/
frontend/
sql/
```

## Commands

- `cd backend && pytest tests/unit`
- `cd backend && pytest tests/contract`
- `cd backend && pytest tests/integration`

## Code Style

Python 3.12: use Object-Oriented Design, Hexagonal Architecture, Repository
pattern, strict typing, explicit SQL with psycopg 3, and TDD-first delivery.

## Recent Changes

- 001-login-admin: Added Python 3.12 + FastAPI, Uvicorn, psycopg 3, psycopg_pool, PyJWT, argon2-cffi, Pydantic v2, pydantic-settings

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
