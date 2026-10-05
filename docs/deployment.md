# ULPF Production Deployment & Operations Runbook
**Smart India Hackathon 2026** · **Problem ID:** SIH26156 · **Organization:** National Technical Research Organisation (NTRO)

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [GitHub Repository Setup](#3-github-repository-setup)
4. [Supabase Control Plane Setup (Mode A)](#4-supabase-control-plane-setup-mode-a)
5. [MongoDB Telemetry Plane Setup](#5-mongodb-telemetry-plane-setup)
6. [PostgreSQL Local Control Plane Setup (Mode B)](#6-postgresql-local-control-plane-setup-mode-b)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [Secret Management & Isolation](#8-secret-management--isolation)
9. [Docker Multi-Container Architecture](#9-docker-multi-container-architecture)
10. [Local Production Deployment](#10-local-production-deployment)
11. [Cloud / VPS Deployment](#11-cloud--vps-deployment)
12. [Supabase Authentication Setup](#12-supabase-authentication-setup)
13. [CORS Configuration](#13-cors-configuration)
14. [HTTPS & Domain Configuration](#14-https--domain-configuration)
15. [Health Checks & Readiness Monitoring](#15-health-checks--readiness-monitoring)
16. [Structured Logging & Observability](#16-structured-logging--observability)
17. [Database Persistence Verification](#17-database-persistence-verification)
18. [Database Backup Procedures](#18-database-backup-procedures)
19. [Database Restore Procedures](#19-database-restore-procedures)
20. [Container Restart & Reconnection](#20-container-restart--reconnection)
21. [Application Upgrade Procedures](#21-application-upgrade-procedures)
22. [Safe Rollback Procedures](#22-safe-rollback-procedures)
23. [Operational Troubleshooting](#23-operational-troubleshooting)
24. [Sovereign Air-Gapped Deployment Runbook](#24-sovereign-air-gapped-deployment-runbook)
25. [Security & Hardening Notes](#25-security--hardening-notes)

---

## 1. Architecture Overview
ULPF operates a decoupled dual-storage plane architecture:
- **Telemetry Data Plane (MongoDB 8.0)**: Ingests and indexes high-volume telemetry (`raw_logs`, `normalized_events`, `processing_jobs`, `security_events`, `security_alerts`, `templates`, `template_matches`, `compression_records`, `pipeline_runs`, `response_simulations`).
- **Control Plane (PostgreSQL 16 / Supabase Cloud)**: Manages RBAC identity (`app_users`, `roles`), audit logs, log source bindings, PII policies, security rules, and declarative parser packs.
- **Frontend / Reverse Proxy**: React 18 SPA built with Vite and served via NGINX (Port 8080) reverse-proxying `/api` and `/health` to FastAPI (Port 8000).

---

## 2. Prerequisites
- **Host OS**: Linux (Ubuntu 22.04/24.04 recommended) or Windows 11 with WSL2
- **Docker Engine**: Version 24.0 or newer
- **Docker Compose**: Version 2.20 or newer
- **Python**: Version 3.11, 3.12, or 3.13 (for running host test/benchmark scripts)
- **Node.js**: Version 18 or 20 (for frontend development tooling)
- **Required Host Ports**:
  - `8080`: Frontend NGINX Web Console
  - `8000`: FastAPI Backend REST API
  - `5433`: PostgreSQL 16 (mapped from container 5432)
  - `27017`: MongoDB 8.0 Telemetry Store

---

## 3. GitHub Repository Setup
The canonical release is maintained at:
- **Repository URL**: `https://github.com/VivekThakur999/ULPF.git`
- **Primary Branches**:
  - `main`: Release production branch
  - `deployment/final-release`: Frozen release tracking branch

To clone and inspect the release:
```bash
git clone https://github.com/VivekThakur999/ULPF.git
cd ULPF
git checkout main
```

---

## 4. Supabase Control Plane Setup (Mode A)
In Connected Cloud Mode, Supabase provides identity and control-plane persistence:
1. Log in to [Supabase Cloud](https://supabase.com/dashboard) and select your project.
2. Open the **SQL Editor**.
3. Paste and execute the DDL migration script from [`docs/supabase_schema.sql`](file:///e:/ULPF/docs/supabase_schema.sql).
4. Verify created tables: `app_users`, `roles`, `audit_logs`, `log_sources`, `pii_settings`, `security_rules`, `parser_packs`, `parser_versions`.
5. Under **Project Settings $\rightarrow$ API**, note your `Project URL`, `anon public key`, `service_role secret`, and `JWT Secret`.

---

## 5. MongoDB Telemetry Plane Setup
MongoDB Community Server 8.0 acts as the high-throughput telemetry engine:
- **Database Name**: `ulpf_telemetry`
- **Docker Container**: `ulpf-mongo`
- **Indexes**: Automatically initialized on startup via `init_mongo_indexes()` in `backend/app/core/mongodb.py`.
- **Forensic Guarantee**: `raw_logs.content_hash` uses a non-unique index (`ix_raw_content_hash`) to ensure duplicate log strings across distinct jobs/timestamps are never dropped.

---

## 6. PostgreSQL Local Control Plane Setup (Mode B)
In Sovereign Air-Gapped Mode, a local PostgreSQL 16 container (`ulpf-postgres`) manages control policies:
- **Default Database**: `ulpf`
- **Default User/Pass**: `ulpf / ulpf`
- **Container Host Port**: `5433` (maps internally to `db:5432`)
- **Alembic Migrations**: Automatically executed on backend startup via container entrypoint: `sh -c 'alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000'`.

---

## 7. Environment Variables Reference
Copy `.env.example` to `.env` and configure:

| Variable | Classification | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `[BACKEND ONLY]` | `production` | Runtime mode (`production` / `development`) |
| `DATABASE_URL` | `[BACKEND ONLY]` | `postgresql+psycopg2://...` | Connection URI for PostgreSQL / Supabase |
| `MONGODB_URI` | `[BACKEND ONLY]` | `mongodb://mongo:27017/ulpf_telemetry` | Connection URI for MongoDB telemetry store |
| `USE_MONGODB` | `[BACKEND ONLY]` | `true` | Enables MongoDB document repository plane |
| `MONGODB_REQUIRE_LIVE` | `[BACKEND ONLY]` | `true` | Disables mock fallback; requires live connection |
| `SUPABASE_URL` | `[BACKEND ONLY]` | `""` | Supabase Cloud API URL (Mode A only) |
| `SUPABASE_ANON_KEY` | `[BACKEND ONLY]` | `""` | Supabase client anon public key |
| `SUPABASE_SERVICE_ROLE_KEY` | `[SECRET]` | `""` | Backend-only Supabase service-role administrative key |
| `SUPABASE_JWT_SECRET` | `[SECRET]` | `""` | Secret used to verify Supabase JWT signatures |
| `AUTH_MODE` | `[BACKEND ONLY]` | `auto` | `auto`, `supabase`, or `local` |
| `SECRET_KEY` | `[SECRET]` | `...` | Key for signing local Argon2id JWT tokens |
| `PII_HMAC_KEY` | `[SECRET]` | `...` | Secret key for deterministic HMAC-SHA256 pseudonymization |
| `PII_DEFAULT_MODE` | `[BACKEND ONLY]` | `DETERMINISTIC_HASH` | Default privacy mode (`OFF`, `MASK`, `DETERMINISTIC_HASH`) |
| `CORS_ORIGINS` | `[BACKEND ONLY]` | `http://localhost:8080` | Comma-separated list of allowed frontend origins |
| `FIRST_ADMIN_EMAIL` | `[SECRET]` | `admin@ulpf.io` | Default bootstrap administrator email |
| `FIRST_ADMIN_PASSWORD` | `[SECRET]` | `AdminPass!123` | Default bootstrap administrator password |
| `AI_PROVIDER` | `[BACKEND ONLY]` | `local_template` | Offline AI mode (`local_template`, `ollama`, `disabled`) |

---

## 8. Secret Management & Isolation
- **Rule 1**: `SUPABASE_SERVICE_ROLE_KEY` must **never** be injected into frontend code or Vite builds.
- **Rule 2**: `.env` is strictly excluded from Git via `.gitignore:40:.env*`.
- **Rule 3**: All production passwords and HMAC keys must be generated via cryptographically secure random generators:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

---

## 9. Docker Multi-Container Architecture
The system is orchestrated via `docker-compose.yml`:
- **`mongo`**: `mongodb/mongodb-community-server:8.0-ubuntu2204` with persistent volume `mongodata`.
- **`db`**: `postgres:16-alpine` with persistent volume `pgdata`.
- **`backend`**: FastAPI application running Python 3.12 on port `8000`.
- **`frontend`**: NGINX Alpine container serving compiled React SPA on port `8080`.

---

## 10. Local Production Deployment
```bash
# 1. Clone repository
git clone https://github.com/VivekThakur999/ULPF.git
cd ULPF

# 2. Configure environment
cp .env.example .env

# 3. Build and launch containers
docker compose up -d --build

# 4. Verify container status
docker compose ps

# 5. Test health endpoint
curl http://localhost:8080/health
```

Access the UI at: `http://localhost:8080`  
Default Credentials: `admin@ulpf.io` / `AdminPass!123`

---

## 11. Cloud / VPS Deployment
For deploying to an Ubuntu VPS (e.g. AWS EC2, DigitalOcean Droplet, GCP Compute Engine):
1. Provision an Ubuntu 22.04+ instance with at least 4GB RAM and 2 vCPUs.
2. Install Docker and Docker Compose plugin:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   ```
3. Clone repository and launch stack:
   ```bash
   git clone https://github.com/VivekThakur999/ULPF.git /opt/ulpf
   cd /opt/ulpf
   cp .env.example .env
   docker compose up -d --build
   ```

---

## 12. Supabase Authentication Setup
To configure Supabase Auth for Connected Mode:
1. Under **Authentication $\rightarrow$ Providers** in the Supabase Dashboard, ensure **Email** is enabled.
2. Under **Authentication $\rightarrow$ URL Configuration**:
   - Set **Site URL**: `http://localhost:8080` (or your production domain `https://ulpf.yourdomain.com`).
   - Add **Redirect URLs**: `http://localhost:8080/**`, `http://localhost:8080/auth/callback`.
3. Set in `.env`:
   - `AUTH_MODE=supabase`
   - `SUPABASE_JWT_SECRET=<your-project-jwt-secret>`

---

## 13. CORS Configuration
In production, lock down CORS origins to only your authorized frontend domains:
```env
CORS_ORIGINS=https://ulpf.yourdomain.com,http://localhost:8080
```
FastAPI automatically parses comma-delimited origins into an allowed whitelist and enforces strict preflight validation.

---

## 14. HTTPS & Domain Configuration
To bind a production domain with automated Let's Encrypt SSL/TLS certificates using Certbot on the host:
1. Create a DNS `A` record pointing `ulpf.yourdomain.com` to your server IP.
2. Configure an NGINX reverse proxy on the host or use Certbot:
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d ulpf.yourdomain.com
   ```
3. Proxy traffic to container port `8080`:
   ```nginx
   server {
       server_name ulpf.yourdomain.com;
       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

---

## 15. Health Checks & Readiness Monitoring
- **Backend Health Check**: `GET http://localhost:8000/health`
- **Reverse Proxy Health Check**: `GET http://localhost:8080/health`
- **Expected Status Response**:
  ```json
  {
    "status": "ok",
    "version": "0.1.0",
    "environment": "production",
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

## 16. Structured Logging & Observability
- Backend logs are emitted in structured standard format: `YYYY-MM-DDTHH:MM:SS | LEVEL | module | message`.
- View live container logs:
  ```bash
  docker compose logs -f backend
  docker compose logs -f mongo
  docker compose logs -f db
  ```

---

## 17. Database Persistence Verification
All data is stored in named Docker volumes (`mongodata` and `pgdata`). To verify persistence:
```bash
# Ingest data, then restart containers
docker compose restart
# Data remains intact and available in Log Explorer
```

---

## 18. Database Backup Procedures
### MongoDB Backup
```bash
docker compose exec mongo mongodump --db=ulpf_telemetry --out=/data/db/backup_$(date +%Y%m%d)
```
### PostgreSQL Backup
```bash
docker compose exec db pg_dump -U ulpf ulpf > backup_pg_$(date +%Y%m%d).sql
```

---

## 19. Database Restore Procedures
### MongoDB Restore
```bash
docker compose exec mongo mongorestore --db=ulpf_telemetry /data/db/backup_YYYYMMDD/ulpf_telemetry
```
### PostgreSQL Restore
```bash
docker compose exec -T db psql -U ulpf ulpf < backup_pg_YYYYMMDD.sql
```

---

## 20. Container Restart & Reconnection
```bash
# Restart entire stack
docker compose restart

# Restart individual backend service
docker compose restart backend
```

---

## 21. Application Upgrade Procedures
```bash
# Pull latest release
git pull origin main

# Rebuild containers without downtime
docker compose up -d --build
```

---

## 22. Safe Rollback Procedures
If a release requires immediate rollback:
1. Roll back code to the known good release commit:
   ```bash
   git checkout 0d3d4ad
   ```
2. Re-deploy container images:
   ```bash
   docker compose up -d --build
   ```
3. **Important**: Named volumes (`mongodata`, `pgdata`) are preserved; zero telemetry or user data is lost during rollback.

---

## 23. Operational Troubleshooting

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| `502 Bad Gateway` on `:8080` | Backend container starting or unhealthy | Check `docker compose logs backend` and verify database readiness. |
| `401 Unauthorized` on API | Missing or expired JWT token | Re-authenticate at `POST /api/auth/login`. |
| `403 Forbidden` on action | User role lacks write privilege | Switch to an account with `ADMIN` or `ANALYST` role. |
| Host port conflict on `5432` | Local PostgreSQL running on host | ULPF maps PostgreSQL to host port `5433:5432`. Connect host tools to port `5433`. |

---

## 24. Sovereign Air-Gapped Deployment Runbook
In an isolated defense network with zero external internet access:
1. **Export Docker Images**:
   ```bash
   docker save -o ulpf-images.tar ulpf-frontend:latest ulpf-backend:latest mongodb/mongodb-community-server:8.0-ubuntu2204 postgres:16-alpine
   ```
2. **Transfer and Load on Air-Gapped Host**:
   ```bash
   docker load -i ulpf-images.tar
   ```
3. **Launch Stack**:
   ```bash
   docker compose up -d
   ```
4. **Air-Gapped Guarantee**: Operates 100% locally with local Argon2id auth, local PostgreSQL, local MongoDB, and local deterministic AI.

---

## 25. Security & Hardening Notes
- **AST Zero-Execution Guarantee**: Logs are parsed as pure data; `eval()`, `exec()`, and shell spawning are strictly prohibited.
- **Service Role Isolation**: `SUPABASE_SERVICE_ROLE_KEY` is isolated to backend containers and never exposed to the web client.
- **Privacy Assurance**: HMAC-SHA256 deterministic tokenization allows mathematical correlation of anonymized logs without plaintext identity leakage.
