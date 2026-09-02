# ULPF — Universal Log Pre-processing Framework

**Smart India Hackathon** · Problem Statement **SIH26156 — Universal Log Pre-processing Framework**
· Organisation: **National Technical Research Organisation (NTRO)** · Category: Software

---

## What is ULPF?

ULPF is a web platform that turns **raw, heterogeneous log data** from many different
sources into a **single clean, privacy-protected, normalized event stream** that a
security analyst can search, correlate and reason about.

It is **not** a generic SIEM. The product is the **pre-processing pipeline**:

```
RAW HETEROGENEOUS LOGS
      → SECURITY SHIELD (treat every log as untrusted)
      → FORMAT DETECTION
      → PARSING (pluggable parsers)
      → CLEANING & VALIDATION
      → FIELD EXTRACTION
      → PII OBFUSCATION (deterministic pseudonymization)
      → NORMALIZATION → UNIVERSAL SCHEMA
      → STORAGE
      → SEARCH · CROSS-SOURCE CORRELATION · ANALYTICS
      → DETERMINISTIC SECURITY RULES → TRANSPARENT RISK SCORE → ALERTS
```

## Problem

Security teams receive logs in dozens of incompatible formats (syslog, Apache, Nginx,
firewall, Windows events, JSON apps, ad-hoc text). Before any analysis is possible
someone has to identify the format, parse it, clean malformed/weaponized entries,
strip or pseudonymize sensitive identifiers, and map every vendor's field names onto
a common vocabulary. This is slow, error-prone and usually re-implemented per project.

## Solution

A modular, extensible framework that does all of that automatically, explains every
transformation in a **live visual pipeline debugger**, and preserves the original raw
log for auditability.

## Key differentiators

1. **Universal normalization** — every format collapses to one canonical schema.
2. **Privacy-preserving correlation** — deterministic pseudonyms let you correlate an
   IP/user across sources without exposing the raw identifier.
3. **Secure pre-processing** — a "security shield" screens every log for injection /
   control-character / weaponization indicators before parsing.
4. **Live pipeline debugger** — a Regex101-style view of raw → universal event.
5. **Cross-source correlation** — link Linux + firewall + application events.
6. **Transparent risk scoring** — every score comes with its breakdown.
7. **Extensible parser architecture** — declarative parser packs + a WASM sandbox.
8. **Offline-first AI assistance** — optional local log explanation, no cloud required.

## Technology

| Layer      | Stack |
|------------|-------|
| Frontend   | React 18, TypeScript, Vite, Tailwind, Recharts, React Router, TanStack Query, Monaco |
| Backend    | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database   | PostgreSQL (prod) · SQLite (zero-infra dev) — repository layer keeps OpenSearch pluggable |
| Auth       | JWT, bcrypt, 3-role RBAC (ADMIN / ANALYST / VIEWER), audit log |
| Infra      | Docker + Docker Compose |
| Testing    | Pytest, HTTPX, Vitest, Playwright |

## Installation

### Option A — Docker (recommended for the demo)

```bash
cp .env.example .env          # then edit secrets
docker compose up --build
# frontend  → http://localhost:8080
# backend   → http://localhost:8000  (docs at /docs)
```

### Option B — Local, no Docker

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/activate           # Windows;  source .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
alembic upgrade head             # or just run the app (auto-creates on first boot)
uvicorn app.main:app --reload    # http://localhost:8000

# frontend (second terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173  (proxies /api to :8000)
```

Default seeded admin (from `.env`): `admin@ulpf.io` / `ChangeMe!123` — **change it**.

## Testing

```bash
cd backend  && .venv/Scripts/python -m pytest        # API + processing unit/integration tests
cd frontend && npm test                              # component tests
cd frontend && npm run test:e2e                       # Playwright end-to-end
```

After every development phase the test suite is run and must pass before the next phase.

## Demo instructions

See [docs/demo.md](docs/demo.md). A one-click **Demo Mode** loads synthetic datasets and
walks through the full workflow including the brute-force attack scenario (attacker
`192.168.1.50`, risk 91/100).

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/api.md](docs/api.md)
- [docs/universal-schema.md](docs/universal-schema.md)
- [docs/parser-development.md](docs/parser-development.md)
- [docs/deployment.md](docs/deployment.md)
- [docs/security-model.md](docs/security-model.md)
- [docs/demo.md](docs/demo.md)

## Build status (phase-by-phase)

| Phase | Scope | Status |
|------:|-------|--------|
| 1–2 | Architecture, repo, Docker, FastAPI + React + DB, auth, RBAC, audit log | ✅ done |
| 3–5 | Universal schema, pipeline context, ingestion + jobs, format detection, 7 parsers | ✅ done |
| 6–8 | Cleaning + validation, field extraction, normalization, deterministic PII, security shield | ✅ done |
| 9–10 | Log Explorer + search, cross-source correlation, detection rules, risk scoring, alerts, timeline | ⏳ next |
| 11–13 | Dashboard, Live Pipeline Debugger, parser packs + versioning, WASM PoC | ⏳ planned |
| 14–24 | Templates/compression, offline AI, response simulator, tests, perf, polish, demo mode | ⏳ planned |

## Future scope

Real-time enterprise streaming, Kafka, distributed processing, OpenSearch scaling,
additional enterprise connectors, threat-intel feeds, SIEM/SOAR integration, real
firewall/IAM/EDR response, ML anomaly detection, larger local LLMs, cloud deployment,
multi-tenancy. **None of these are implemented** — see
[docs/architecture.md](docs/architecture.md#future-scope).

## License

MIT — see [LICENSE](LICENSE). All bundled datasets are **synthetic / demo data**.
