# ULPF Deployment Journal (Append-Only Engineering Log)

This document is the permanent, append-only engineering record for the Universal Log Pre-processing Framework (ULPF).
**RULE**: NEVER delete previous entries. NEVER rewrite historical logs. Always append new phases and engineering actions below.

---

## Phase 0 — Comprehensive Repository Audit & Persistent Context Scaffolding

**Date**: 2026-10-05  
**Agent**: Senior Architect / SIH Lead  
**Objective**: Execute exhaustive repository audit, establish long-term source-of-truth documentation, and create persistent context memory files.  

- **Files Inspected**:
  - `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/mongodb.py`
  - `backend/app/models/` (`user.py`, `event.py`, `security.py`, `response.py`)
  - `backend/app/repositories/` (`events.py`, `mongodb/` [all 10 repos])
  - `backend/app/services/` (`ingestion/`, `normalization/`, `security/`, `privacy/`, `correlation/`, `analytics/`, `templates/`, `compression/`, `response/`, `ai/`)
  - `docker-compose.yml`, `frontend/Dockerfile`, `frontend/nginx.conf`
  - `backend/tests/` [all 26 test files], `frontend/src/` [all pages & tests]
- **Files Created**:
  - `docs/ULPF_PROJECT_CONTEXT.md`
  - `docs/ULPF_DEPLOYMENT_JOURNAL.md`
  - `docs/SIH_COMPLIANCE.md`
  - `docs/DEPLOYMENT.md`
  - `docs/DATABASE_ARCHITECTURE.md`
  - `docs/SECURITY.md`
- **Database Status**:
  - MongoDB 8.0: Active in container `ulpf-mongo` (:27017), database `ulpf_telemetry`, 10 collections indexed.
  - PostgreSQL 16: Active in container `ulpf-postgres` (:5433->5432), database `ulpf`, control plane tables initialized.
- **Docker Status**:
  - 4 containers active and healthy (`ulpf-frontend` :8080, `ulpf-backend` :8000, `ulpf-postgres` :5433, `ulpf-mongo` :27017).
- **Test Results**:
  - Backend: 196 passed in 74.28s (100%).
  - Frontend: 27 passed in 81.87s (100%).
  - Staging Smoke Test: PASS (13/13 stages via port 8080).
- **Decisions Made**:
  - Decoupled `ResponseSimulation.alert_id` relational foreign key in SQLAlchemy model to enable cross-storage-plane simulation of MongoDB alerts.
  - Mapped PostgreSQL host port to `5433` to prevent Windows host port 5432 collision while keeping internal container networking on `db:5432`.
  - Configured `MongoTemplateRepository.upsert_template` to resolve template unique constraints on `$or: [_id, token_signature, template_key]` without duplicate key collisions.
- **Next Step**: Phase 0 Audit approval and proceeding with any specified hardening or jury demo asset preparation.

---

## Phase 1 — Real MongoDB 8.0 Telemetry Plane Migration & Index Verification

**Date**: 2026-10-04  
**Agent**: Database & Backend Engineer  
**Objective**: Transition ULPF telemetry plane to live MongoDB Community Server 8.0 container without mock fallback.  

- **Files Inspected**:
  - `backend/app/core/mongodb.py`
  - `backend/app/repositories/mongodb/*.py`
  - `backend/tests/test_mongo_live.py`, `backend/tests/test_mongo_persistence.py`, `backend/tests/test_mongo_traceability.py`
- **Files Modified**:
  - `backend/app/core/mongodb.py`
  - `backend/app/repositories/mongodb/events.py`
  - `backend/app/repositories/mongodb/templates.py`
- **Files Created**:
  - `backend/tests/test_mongo_live.py`
  - `backend/tests/test_mongo_persistence.py`
  - `backend/tests/test_mongo_traceability.py`
- **Database Changes**:
  - Pinned MongoDB image `mongodb/mongodb-community-server:8.0-ubuntu2204`.
  - Created indexes across 10 collections: `raw_logs`, `normalized_events`, `processing_jobs`, `security_events`, `security_alerts`, `templates`, `template_matches`, `compression_records`, `pipeline_runs`, `response_simulations`.
- **Environment Changes**:
  - Added `MONGODB_URI=mongodb://127.0.0.1:27017/ulpf_telemetry`, `USE_MONGODB=true`, `MONGODB_ALLOW_MOCK=false`, `MONGODB_REQUIRE_LIVE=true`.
- **Tests Executed**:
  - `python -m pytest tests/test_mongo_live.py tests/test_mongo_persistence.py tests/test_mongo_traceability.py`
- **Test Results**:
  - 19 passed (100%).
  - Real MongoDB Integration Verdict: **PASS**.
- **Benchmark Results**:
  - Bulk Event Ingestion: 24,278.4 events/sec (1,000 events in 41.19 ms).
  - P50 Paginated Query Latency: 9.16 ms.
  - P50 Facet Aggregation Latency: 9.03 ms.
- **Next Step**: Supabase control-plane integration & RBAC hardening.

---

## Phase 2 — Supabase / PostgreSQL Control Plane & RBAC Integration

**Date**: 2026-10-04  
**Agent**: Supabase & Security Engineer  
**Objective**: Implement dual-auth control plane supporting Connected Supabase Cloud mode and Sovereign Air-Gapped local PostgreSQL mode.  

- **Files Inspected**:
  - `backend/app/auth/deps.py`, `backend/app/auth/security.py`, `backend/app/models/user.py`
  - `docs/supabase_schema.sql`
- **Files Modified**:
  - `backend/app/auth/deps.py`
  - `backend/app/auth/security.py`
  - `backend/app/core/config.py`
  - `backend/app/models/user.py`
- **Files Created**:
  - `docs/supabase_schema.sql`
  - `backend/migrations/supabase_schema.sql`
  - `backend/tests/test_postgres_live.py`
  - `backend/tests/test_airgap_mode.py`
- **Database Changes**:
  - Authored comprehensive Supabase DDL with RLS policies for `app_users`, `api_keys`, `log_sources`, `pii_settings`, `security_rules`, `parser_packs`, `parser_versions`, `audit_logs`.
  - Added `supabase_user_id` foreign identity column in `app_users`.
- **Security Changes**:
  - Configured strict backend-only consumption of `SUPABASE_SERVICE_ROLE_KEY`.
  - Implemented Argon2id password hashing for air-gapped local authentication fallback.
- **Tests Executed**:
  - `python -m pytest tests/test_postgres_live.py tests/test_airgap_mode.py tests/test_auth.py`
- **Test Results**:
  - 18 passed (100%).
  - Real PostgreSQL / Supabase RBAC Verdict: **PASS**.
- **Next Step**: Docker Compose container stack staging and E2E smoke tests.

---

## Phase 3 — Docker Compose Staging Deployment & NGINX Reverse Proxy

**Date**: 2026-10-04  
**Agent**: DevOps & Deployment Engineer  
**Objective**: Build and orchestrate complete 4-container stack with healthchecks, persistent volumes, and NGINX reverse proxy.  

- **Files Modified**:
  - `docker-compose.yml`
  - `frontend/nginx.conf`
  - `frontend/Dockerfile`
  - `backend/Dockerfile`
- **Files Created**:
  - `backend/tests/test_staging_e2e_smoke.py`
  - `backend/scripts/benchmark_performance.py`
- **Docker Changes**:
  - Created 4 services: `mongo`, `db` (postgres), `backend`, `frontend`.
  - Added healthcheck loops for MongoDB `mongosh` ping and PostgreSQL `pg_isready`.
  - Mapped host ports `8080` (NGINX), `8000` (FastAPI), `5433` (PostgreSQL), `27017` (MongoDB).
- **Tests Executed**:
  - `python -m pytest tests/test_staging_e2e_smoke.py`
- **Test Results**:
  - 13/13 E2E stages passed through port 8080 (Health $\rightarrow$ Login $\rightarrow$ Ingest $\rightarrow$ Normalize $\rightarrow$ Search $\rightarrow$ Correlate $\rightarrow$ Risk $\rightarrow$ Alert $\rightarrow$ Timeline $\rightarrow$ AI $\rightarrow$ Simulate $\rightarrow$ Mine $\rightarrow$ Compress).
  - Restart persistence verified (zero data loss across container restarts).
  - Docker Staging E2E Verdict: **PASS**.
- **Next Step**: Staging E2E smoke tests, performance benchmarking, and compliance audit.

---

## Phase 4 — Staging E2E Smoke Testing & Performance Benchmarking

**Date**: 2026-10-04  
**Agent**: QA & Performance Engineer  
**Objective**: Validate end-to-end integration workflows through NGINX port 8080 and execute live performance benchmarks.

- **Files Modified**:
  - `backend/app/models/response.py` (decoupled foreign key constraint to permit MongoDB alert references)
  - `backend/app/repositories/mongodb/templates.py` (improved template deduplication)
  - `backend/app/api/routes/analytics.py` (wired MongoDB event counts to analytics dashboard)
- **Tests Executed**:
  - `python -m pytest tests/test_staging_e2e_smoke.py -v -s`
  - `python scripts/benchmark_performance.py`
  - `npm test -- --run` in frontend
- **Test Results**:
  - 13/13 E2E stages passed through NGINX reverse proxy (`http://localhost:8080`).
  - Container persistence and restart behavior verified without data loss.
  - Live write benchmark: 24,027+ events/sec bulk ingestion into MongoDB 8.0.
  - Query latency: P50 = 27.5 ms, P95 = 46.1 ms for Log Explorer multi-attribute queries.
  - 27/27 Vitest frontend component tests passed.
- **Verdict**: **PASS**.

---

## Phase 5 — Final Hardening, SIEM/ML Exports & Final Release Gate

**Date**: 2026-10-05  
**Agent**: Lead Architect & Release Engineer  
**Objective**: Deliver final SIH-compliant, production-hardened release with machine-readable SIEM / ML-ready exports, full documentation, and 100% regression pass rate.

- **Files Modified**:
  - `backend/app/api/routes/logs.py` (added `/api/logs/export/ndjson`, `/api/logs/export/json`, `/api/logs/export/ml-ready`)
  - `backend/app/repositories/events.py` & `backend/app/repositories/mongodb/events.py` (expanded query limits to 10,000 for bulk exports)
  - `backend/app/repositories/mongodb/templates.py` (strengthened signature & ID resolution)
  - `backend/tests/conftest.py` (registered all 10 MongoDB collections in test cleanup fixture)
  - `docs/SIH_COMPLIANCE.md` (updated SIH matrix with verified export and benchmark evidence)
  - `README.md` (comprehensive architecture, quickstart, docker commands, and export API documentation)
- **Files Created**:
  - `backend/tests/test_export.py` (NDJSON, JSON, and ML feature matrix test suite)
  - `docs/ARCHITECTURE_2PAGE.md` (Executive 2-page architecture summary for SIH evaluation)
  - `docs/SIH_PRESENTATION_5_SLIDES.md` (5-slide presentation deck structure)
  - `docs/DEMO_SCRIPT_2MIN.md` (2-minute live demo script)
- **Tests Executed**:
  - `python -m pytest -v` (197/197 backend tests passed)
  - `npm test -- --run` (27/27 frontend tests passed)
  - `python scripts/benchmark_performance.py` (measured 24,027.9 writes/sec, 31,486.7 templates/sec, 100% reconstruction fidelity)
  - `python -m pytest tests/test_staging_e2e_smoke.py -v -s` (13/13 container stages passed)
- **Final Release Gate Status**: **ALL 45 CHECKS PASSED (100%)**.
- **Final Release Recommendation**: **APPROVED FOR PRODUCTION & SIH 2026 EVALUATION**.

---

## Phase 6 — Production Deployment, Secret Audit & GitHub Publication

**Date**: 2026-10-06  
**Agent**: Lead DevOps & Security Engineer  
**Objective**: Prepare, verify, and publish the final frozen ULPF release to GitHub with zero secret leakage and complete deployment readiness.

- **Files Modified**:
  - `.env.example` (sanitized all secret keys into empty safe placeholders; added security classification tags)
  - `docs/DEPLOYMENT.md` (expanded to comprehensive 25-section production operations runbook)
  - `docs/ULPF_PROJECT_CONTEXT.md` (synchronized latest production topology and release baseline)
- **Repository Actions**:
  - Performed full repository secret scan for `SUPABASE_SERVICE_ROLE_KEY`, `SECRET_KEY`, `PII_HMAC_KEY`.
  - Created and pushed release branch `deployment/final-release`.
  - Pushed release baseline to `main` at `https://github.com/VivekThakur999/ULPF.git` (Commit: `0d3d4ad`).
- **Tests & Health Verification**:
  - `197/197` Backend Pytest tests passed (100%).
  - `27/27` Frontend Vitest tests passed (100%).
  - Production frontend build `npm run build` completed cleanly (0 errors).
  - Live Docker stack (`ulpf-frontend`, `ulpf-backend`, `ulpf-postgres`, `ulpf-mongo`) verified healthy.
  - Reverse proxy `/health` and direct backend `/health` verified `status: ok`, `telemetry_store.mode: live`, `telemetry_store.status: connected`.
- **Deployment Status**: **READY FOR SIH 2026 DEMONSTRATION AND SUBMISSION**.


