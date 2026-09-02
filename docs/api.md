# ULPF API

Base path: `/api`. Auth: `Authorization: Bearer <jwt>` on every route except
`/api/auth/login` and `/health`. Interactive docs: `GET /docs` (Swagger), `GET /redoc`.

RBAC: `VIEWER < ANALYST < ADMIN`. "Requires ANALYST" means analyst **or** admin.

## Implemented (Phase 1–2)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/health` | public | liveness + DB status |
| POST | `/api/auth/login` | public | email+password → JWT |
| POST | `/api/auth/logout` | any | audited client-side logout |
| GET | `/api/auth/me` | any | current user |
| GET | `/api/users` | ADMIN | list users |
| POST | `/api/users` | ADMIN | create user |
| PUT | `/api/users/{id}` | ADMIN | update user (name/password/role/active) |
| DELETE | `/api/users/{id}` | ADMIN | delete user |
| GET | `/api/users/audit-logs` | ADMIN | paged audit log, filter by `action` |

## Planned (later phases — not yet available)

`/api/sources*`, `/api/ingestion/*`, `/api/logs*`, `/api/pipeline/{test,debug}`,
`/api/parsers*`, `/api/alerts*`, `/api/analytics/*`, `/api/privacy/settings`,
`/api/ai/explain`, `/api/compression/stats`, `/api/response/simulate`.

Each returns `422` with a Pydantic error list on invalid input, `401` when
unauthenticated, `403` when the role is insufficient.
