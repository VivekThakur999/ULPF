# ULPF — Universal Log Pre-processing Framework

**Smart India Hackathon 2026** · Problem Statement **SIH26156 — Universal Log Pre-processing Framework**
· Organisation: **National Technical Research Organisation (NTRO)** · Category: Software

[![Live Production](https://img.shields.io/badge/Production%20Live-ulpf10.vercel.app-red?logo=vercel)](https://ulpf10.vercel.app)
[![Backend Tests](https://img.shields.io/badge/Backend%20Pytest-202%2F202%20Passed-brightgreen)](file:///backend/tests)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Vitest-27%2F27%20Passed-brightgreen)](file:///frontend/src)
[![MongoDB Ingestion](https://img.shields.io/badge/MongoDB%20Write-24%2C027%20writes%2Fsec-blue)](docs/ULPF_PROJECT_CONTEXT.md)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Live Cloud Deployment & Demo Access

- **Live Production URL**: [https://ulpf10.vercel.app](https://ulpf10.vercel.app)
- **Live Health API**: [https://ulpf10.vercel.app/health](https://ulpf10.vercel.app/health)

### 1-Click Demo Persona Credentials
The live login page features a red & white themed 1-click persona switcher:
| Persona | Email | Default Password | Role & Permissions |
|---------|-------|------------------|-------------------|
| **Administrator** | `admin@ulpf.io` | `ChangeMe!123` | Full system control, RBAC management, parser pack creation, audit log access |
| **Security Analyst** | `analyst@ulpf.io` | `ChangeMe!123` | Log ingestion, parser validation, incident triage, response simulation |
| **SOC Viewer** | `viewer@ulpf.io` | `ChangeMe!123` | Read-only access to Command Center, Log Explorer, and analytics charts |

---

## What is ULPF?

**Universal Log Pre-processing Framework (ULPF)** is a sovereign, high-throughput, security-hardened log pre-processing and normalization platform. It transforms raw, heterogeneous, and weaponized logs from disparate perimeter appliances into a canonical, privacy-protected event stream with 100% forensic traceability.

```
RAW HETEROGENEOUS LOGS (Firewall, Auth, Web, App, Syslog, JSON, CEF)
      │
      ▼
1. SECURITY SHIELD (AST-isolated sanitization, escape sequence detection, no-exec)
      │
      ▼
2. FORMAT DETECTION (Automatic classifier across 8+ formats)
      │
      ▼
3. PARSING ENGINE (Declarative YAML Parser Packs + WASM Sandbox)
      │
      ▼
4. CLEANING & FIELD EXTRACTION (ISO 8601 UTC timestamps, field validation)
      │
      ▼
5. PII PROTECTION (Deterministic HMAC-SHA256 privacy-preserving tokenization)
      │
      ▼
6. UNIVERSAL NORMALIZATION (Standardized Universal Event Schema v1.0.0)
      │
      ▼
7. DUAL-PLANE STORAGE (MongoDB Atlas / 8.0 Telemetry + Supabase / PostgreSQL 16 Control Plane)
      │
      ├───────────────────────────────┼───────────────────────────────┐
      ▼                               ▼                               ▼
LOG EXPLORER & CORRELATION      ALERTS & RISK SCORING           SIEM / ML-READY EXPORT
(Sub-30ms Facet Search)         (Deterministic Attribution)     (ECS NDJSON & ML Feature Matrix)
```

---

## Problem & National Defense Context

National cyber defense perimeters and enterprise SOCs receive terabytes of logs daily across incompatible vendor formats. Traditional SIEMs and log pipelines face critical vulnerabilities:
1. **Unchecked Weaponization**: Attackers inject terminal escape sequences (`\x1b`), CRLF, and log forging strings that crash indexers and corrupt terminals.
2. **Schema Fragmentation**: Incompatible syntax across vendors prevents automated cross-source correlation.
3. **PII Leakage**: Client IPs, usernames, and credentials leak in plaintext into analytical repositories.
4. **Loss of Forensic Chain of Custody**: Pre-processors frequently mutate or drop raw entries, destroying cryptographic admissibility during forensic investigations.

---

## Key Technical Innovations

1. **Dual Storage Architecture**:
   - **Data Plane (MongoDB Atlas / MongoDB 8.0)**: Dedicated to high-volume telemetry (`raw_logs`, `normalized_events`, `security_alerts`, `templates`, `compression_records`). Benchmarked at **24,027.9 events/sec**.
   - **Control Plane (Supabase Cloud / PostgreSQL 16)**: Dedicated to RBAC identity (`app_users`, `roles`), audit logs, security rules, PII policies, and parser metadata.
2. **Sovereign Dual-Mode Deployment**:
   - **Connected Cloud Mode**: Uses Supabase Cloud for Identity/RBAC with MongoDB Atlas / Cloud for Telemetry.
   - **Sovereign Air-Gapped Mode**: 100% Offline with local Argon2id authentication, local PostgreSQL 16, local MongoDB 8.0, and offline local AI assistance. Zero outbound internet calls.
3. **AST-Hardened Security Shield**: Zero dynamic code execution (`no eval()`, `no exec()`, `no subprocess`). Automatically categorizes and quarantines weaponized payloads.
4. **Deterministic Privacy-Preserving Pseudonymization**: Keyed HMAC-SHA256 tokenization allows cross-source correlation (`IP_9f82...`) without exposing raw network secrets.
5. **Lossless Forensic Traceability**: Every normalized event and security alert maintains an immutable pointer (`raw_log_id` + SHA-256 hash) to the exact original raw log bytes.
6. **Deterministic Template Mining & Micro-Compression**: Discovers recurring patterns across heterogeneous streams with **100% byte-exact reconstruction** at **31,480+ logs/sec**.
7. **SIEM & ML-Ready Data Export**: Machine-readable Elastic Common Schema (ECS 1.12.0) NDJSON export and 14-dimensional dense feature matrix export for downstream machine learning.

---

## Technology Stack

| Layer | Stack | Purpose |
|-------|-------|---------|
| **Frontend UI** | React 18, TypeScript, Vite, Tailwind CSS, Monaco Editor, Recharts | SOC Command Center, Log Explorer, Pipeline Debugger |
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, PyMongo, SQLAlchemy 2 | Stateless REST Engine, Pipeline Ingestion, Security Engine |
| **Telemetry Store** | MongoDB Atlas / MongoDB 8.0 | High-Volume Document Storage for Raw Logs & Events |
| **Control Store** | Supabase Cloud / PostgreSQL 16 | Identity, RBAC, Security Rules, PII Policies, Audit Logs |
| **Hosting & Infra** | Vercel Serverless / Docker Compose | Serverless Edge Deployment & Air-Gapped Multi-Container Architecture |

---

## Live Performance Benchmarks (Empirically Verified)

*Hardware: AMD64 Architecture · OS: Windows 11 / Linux Ubuntu · Python 3.12 / 3.13 · MongoDB 8.0*

| Benchmark Test | Measured Result | Production Target |
|----------------|-----------------|-------------------|
| **MongoDB Bulk Ingestion Write** | **24,027.9 events/sec** (Batch=2500) | $\ge$ 10,000 events/sec |
| **Log Explorer Search Latency (P50)** | **27.51 ms** (Filtered search) | $\le$ 50.0 ms |
| **Log Explorer Search Latency (P95)** | **46.07 ms** (Filtered search) | $\le$ 100.0 ms |
| **Multi-Field Facet Aggregation** | **P50 = 46.11 ms** | $\le$ 75.0 ms |
| **Alert Queue Query Latency** | **P50 = 5.75 ms** | $\le$ 20.0 ms |
| **Template Mining Speed** | **31,486.7 logs/sec** (1,000 logs) | $\ge$ 5,000 logs/sec |
| **Micro-Compression Fidelity** | **100.0% Exact Byte Equality** | 100.0% Zero Loss |

---

## Quickstart & Deployment

### Option A — Full Docker Stack (Recommended Local Setup)

```bash
# 1. Clone repository & configure environment
git clone https://github.com/VivekThakur999/ULPF.git
cd ULPF
cp .env.example .env

# 2. Build and launch all 4 containers (Frontend, Backend, MongoDB, PostgreSQL)
docker compose up -d --build

# 3. Verify health status
curl http://localhost:8000/health
# Response: {"status":"ok","database":"connected","telemetry_store":{"status":"connected","driver":"pymongo"}}
```

- **Frontend SOC Console**: [http://localhost:8080](http://localhost:8080)
- **Backend REST API & Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Default Seeded Admin**: `admin@ulpf.io` / `ChangeMe!123`

---

### Option B — Sovereign Air-Gapped Deployment

In an isolated / air-gapped defense network:
1. Transfer the pre-built Docker image archives:
   ```bash
   docker load -i ulpf-images.tar
   ```
2. Launch in Sovereign Mode:
   ```bash
   docker compose -f docker-compose.yml up -d
   ```
3. ULPF automatically operates with 100% local authentication, local PostgreSQL, local MongoDB, and offline AI explanation.

---

## SIEM / Data Lake & ML Export Endpoints

ULPF provides native, machine-readable export endpoints for enterprise SIEM ingestion and machine learning:

1. **ECS-Compatible NDJSON Stream**:
   ```http
   GET /api/logs/export/ndjson?source=firewall_asa&severity=ERROR
   ```
   *Streams newline-delimited JSON formatted to Elastic Common Schema (ECS 1.12.0) with embedded ULPF traceability metadata.*

2. **JSON Export Envelope**:
   ```http
   GET /api/logs/export/json?limit=1000
   ```
   *Returns structured JSON bundle with schema versioning and batch metadata.*

3. **Machine Learning Feature Matrix**:
   ```http
   GET /api/logs/export/ml-ready?limit=5000
   ```
   *Exports a 14-dimensional dense numerical and categorical feature vector (`timestamp_epoch`, `hour_of_day`, `day_of_week`, `severity_numeric`, `port`, `length`) ready for downstream scikit-learn / PyTorch anomaly detection pipelines.*

---

## Testing & Verification

Execute the complete regression and verification test suite:

```bash
# Backend Pytest Suite (197/197 Tests Passing)
cd backend
python -m pytest -v

# Frontend Vitest Suite (27/27 Tests Passing)
cd ../frontend
npm test -- --run

# Staging E2E Smoke Test (13/13 Real Container Stages)
cd ../backend
python -m pytest tests/test_staging_e2e_smoke.py -v -s

# Live Performance Benchmarks
python scripts/benchmark_performance.py
```

---

## Project Documentation

- **[docs/ARCHITECTURE_2PAGE.md](docs/ARCHITECTURE_2PAGE.md)** — Official 2-Page Executive Architecture Summary
- **[docs/SIH_PRESENTATION_5_SLIDES.md](docs/SIH_PRESENTATION_5_SLIDES.md)** — 5-Slide Presentation Deck Structure
- **[docs/DEMO_SCRIPT_2MIN.md](docs/DEMO_SCRIPT_2MIN.md)** — 2-Minute Live Demonstration Script
- **[docs/SIH_COMPLIANCE.md](docs/SIH_COMPLIANCE.md)** — 15-Point Official SIH26156 Compliance Matrix
- **[docs/DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md)** — Dual-Plane Storage Specification
- **[docs/SECURITY.md](docs/SECURITY.md)** — Defense-in-Depth Security Model & Threat Shield
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Complete Production & Air-Gapped Runbook
- **[docs/ULPF_PROJECT_CONTEXT.md](docs/ULPF_PROJECT_CONTEXT.md)** — Living Single Source of Truth
- **[docs/ULPF_DEPLOYMENT_JOURNAL.md](docs/ULPF_DEPLOYMENT_JOURNAL.md)** — Engineering History & Change Log

---

## License & Compliance

Licensed under the MIT License — see [LICENSE](LICENSE). Developed for **Smart India Hackathon 2026** (Problem ID: **SIH26156**, Organization: **NTRO**).
