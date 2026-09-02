# Deployment

## Docker Compose (reference deployment)

```bash
cp .env.example .env
#  → set SECRET_KEY, PII_HMAC_KEY, POSTGRES_PASSWORD, FIRST_ADMIN_PASSWORD
docker compose up --build -d
docker compose ps          # all healthy?
docker compose logs -f backend
```

| Service | Port | Notes |
|---------|------|-------|
| frontend (nginx) | 8080 | serves the built SPA, proxies `/api` and `/health` to backend |
| backend (uvicorn) | 8000 | runs `alembic upgrade head` on start, then serves the API |
| db (postgres 16) | 5432 | data in the `pgdata` named volume |

Uploads persist in the `uploads` volume. Reset everything: `docker compose down -v`.

## Local without Docker

See the README "Option B". The backend defaults to SQLite (`./ulpf.db`) and
auto-creates tables + seeds baseline data on first boot, so `alembic` is optional
for dev.

## Configuration

All configuration is environment variables (see `.env.example`). Nothing sensitive is
committed. Key ones:

- `DATABASE_URL` — `sqlite:///./ulpf.db` or `postgresql+psycopg2://user:pass@host/db`
- `SECRET_KEY` — JWT signing key (`python -c "import secrets;print(secrets.token_urlsafe(48))"`)
- `PII_HMAC_KEY` — keyed-hash secret for deterministic pseudonymization
- `CORS_ORIGINS` — comma-separated allowed origins

## Health & readiness

`GET /health` → `{"status":"ok","database":"connected",...}`. Compose healthchecks
gate `backend` on `db` and `frontend` on `backend`.

## Production hardening (not done in the MVP — future scope)

TLS termination, secret manager, read replicas, rate-limit tuning, log shipping,
container image scanning, non-root everywhere (backend already runs as `appuser`).
