# ULPF Deployment & Operations Runbook

This document provides tested, step-by-step instructions for deploying, verifying, restarting, and troubleshooting the Universal Log Pre-processing Framework (ULPF).

---

## 1. Prerequisites
- **Docker Engine**: Version 24.0 or newer
- **Docker Compose**: Version 2.20 or newer
- **Python**: Version 3.11 or 3.12 (for host test/benchmark tooling)
- **Node.js**: Version 18 or 20 (for local frontend dev tooling)
- **Ports Available on Host**:
  - `8080`: ULPF Frontend (NGINX Reverse Proxy)
  - `8000`: ULPF FastAPI Backend
  - `5433`: PostgreSQL 16 Control Plane
  - `27017`: MongoDB 8.0 Telemetry Store

---

## 2. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

### Key Environment Variables (`.env`)
```env
# Mode & Environment
ENVIRONMENT=development
DEBUG=true

# Control Plane Database (PostgreSQL)
DATABASE_URL=postgresql+psycopg2://ulpf:ulpf@127.0.0.1:5433/ulpf
POSTGRES_USER=ulpf
POSTGRES_PASSWORD=ulpf
POSTGRES_DB=ulpf

# Telemetry Store (MongoDB 8.0)
MONGODB_URI=mongodb://127.0.0.1:27017/ulpf_telemetry
MONGODB_DB_NAME=ulpf_telemetry
USE_MONGODB=true
MONGODB_ALLOW_MOCK=false
MONGODB_REQUIRE_LIVE=true

# Security Secrets
SECRET_KEY=dev-secret-key-for-testing-1234567890
PII_HMAC_KEY=dev-pii-hmac-key-for-testing-123456
PII_DEFAULT_MODE=DETERMINISTIC_HASH

# Bootstrap Admin
FIRST_ADMIN_EMAIL=admin@ulpf.io
FIRST_ADMIN_PASSWORD=ChangeMe!123

# Connected Mode Supabase Settings (Mode A Only - leave empty for Air-Gapped)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
AUTH_MODE=auto

# Offline AI
AI_PROVIDER=local_template
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## 3. Docker Compose Stack Deployment

### Build and Start Containers
```bash
docker compose up -d --build
```

### Check Running Container Health
```bash
docker compose ps
```

Expected Output:
```
NAME            IMAGE                                               STATUS                    PORTS
ulpf-frontend   ulpf-frontend:latest                                Up (healthy)              0.0.0.0:8080->80/tcp
ulpf-backend    ulpf-backend:latest                                 Up (healthy)              0.0.0.0:8000->8000/tcp
ulpf-postgres   postgres:16-alpine                                  Up (healthy)              0.0.0.0:5433->5432/tcp
ulpf-mongo      mongodb/mongodb-community-server:8.0-ubuntu2204     Up (healthy)              0.0.0.0:27017->27017/tcp
```

---

## 4. Health & Smoke Test Verification

### Check Health Endpoints
```bash
# Through NGINX Reverse Proxy (Port 8080)
curl http://localhost:8080/health

# Direct FastAPI Backend (Port 8000)
curl http://localhost:8000/health
```

Expected JSON Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected",
  "control_database": "connected",
  "telemetry_store": {
    "status": "connected",
    "driver": "pymongo",
    "mode": "live",
    "database": "ulpf_telemetry"
  },
  "mode": "air-gapped"
}
```

---

## 5. Running Automated Integration & Regression Tests

### Backend Unit & Integration Tests (196 Tests)
```bash
cd backend
python -m pytest
```

### Frontend UI Tests (27 Tests)
```bash
cd frontend
npm test -- --run
```

### Staging E2E Smoke Test (Through NGINX Port 8080)
```bash
cd backend
python -m pytest tests/test_staging_e2e_smoke.py -v
```

### Live Performance Benchmark
```bash
cd backend
python scripts/benchmark_performance.py
```

---

## 6. Persistence & Container Restart Verification

To verify that telemetry in MongoDB and control data in PostgreSQL persist across container restarts:

```bash
# 1. Ingest sample logs or run smoke test
cd backend
python -m pytest tests/test_staging_e2e_smoke.py

# 2. Restart all containers
docker compose restart

# 3. Check health and verify existing data
curl http://localhost:8080/health
cd backend
python -m pytest tests/test_mongo_persistence.py
```

---

## 7. Mode A: Connected Deployment (Supabase Cloud)

1. Open your Supabase Cloud project dashboard.
2. In the Supabase SQL Editor, execute the DDL script located at [`docs/supabase_schema.sql`](file:///e:/ULPF/docs/supabase_schema.sql).
3. In `.env`, populate:
   - `SUPABASE_URL=https://<your-project-id>.supabase.co`
   - `SUPABASE_ANON_KEY=<your-anon-key>`
   - `SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>`
   - `SUPABASE_JWT_SECRET=<your-jwt-secret>`
   - `AUTH_MODE=supabase`
4. Restart backend container:
   ```bash
   docker compose restart backend
   ```

---

## 8. Mode B: Sovereign Air-Gapped Deployment

1. Ensure `.env` has no `SUPABASE_URL` or `AUTH_MODE=local` (or `AUTH_MODE=auto` with empty Supabase URL).
2. Start the local Docker Compose stack:
   ```bash
   docker compose up -d
   ```
3. The system automatically initializes local PostgreSQL tables, local Argon2id authentication, local MongoDB telemetry storage, and local deterministic AI explanations.
4. Verify air-gapped isolation:
   ```bash
   cd backend
   python -m pytest tests/test_airgap_mode.py -v
   ```

---

## 9. Troubleshooting Guide

| Problem | Cause | Resolution |
| :--- | :--- | :--- |
| Port collision on 5432 | Local host service (e.g. Postgres) using port 5432 | `docker-compose.yml` maps Postgres to host port `5433:5432`. Ensure host tools connect to `127.0.0.1:5433`. |
| Connection refused to `mongo:27017` on host | Host tests resolving Docker internal hostname | Use `127.0.0.1:27017` in `.env` for host scripts; `docker-compose.yml` passes `mongo:27017` to containers. |
| 401 Unauthorized on API | Missing or expired JWT bearer token | Authenticate at `POST /api/auth/login` with `admin@ulpf.io` / `ChangeMe!123` to obtain an access token. |
| 500 on `/api/response/simulate` | Decoupled alert ID constraint | Verify that `response_simulations.alert_id` in PostgreSQL is `VARCHAR(64)` without rigid relational FK. |
