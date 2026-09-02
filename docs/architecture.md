# ULPF Architecture

## 1. Goals & non-goals

**Goal:** a reliable, extensible **log pre-processing pipeline** with a professional
analyst UI, runnable entirely locally.

**Non-goals (MVP):** being a full SIEM, real enterprise connectors, real automated
response, distributed processing, ML anomaly detection. These are documented as
[future scope](#future-scope).

## 2. High-level components

```
┌──────────────┐      HTTP/JSON       ┌───────────────────────────────┐
│  React SPA   │  ───────────────▶    │  FastAPI backend              │
│ (Vite/TS)    │  ◀───────────────    │                               │
└──────────────┘                      │  api/      auth + routers     │
                                      │  services/ pipeline stages    │
                                      │  repositories/ data access    │
                                      │  models/   SQLAlchemy ORM     │
                                      └──────────────┬────────────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │ PostgreSQL / SQLite  │
                                          └──────────────────────┘
```

Optional side-cars: a **WASM runtime** for sandboxed custom parsers, and a **local LLM**
(Ollama) for offline log explanation. Both are optional and behind interfaces.

## 3. The pipeline

Each stage is a **pure-ish service** that receives a `PipelineContext` and returns it
enriched. The same chain powers:

- **batch ingestion** (`services/ingestion`), and
- the **live pipeline debugger** (`/api/pipeline/debug`), which records every stage's
  input, output, extracted fields, transformations, warnings and errors.

| # | Stage | Service package | Output added to context |
|--:|-------|-----------------|--------------------------|
| 1 | Security Shield | `services/security` | verdict SAFE/SUSPICIOUS/WEAPONIZED_LOG + indicators |
| 2 | Format Detection | `services/detection` | `{format, confidence}` |
| 3 | Parsing | `services/parsing` | parser name/version + raw field dict |
| 4 | Cleaning | `services/cleaning` | normalized types, dedup flag, per-record errors |
| 5 | Field Extraction | `services/parsing` (extractors) | typed fields + confidence |
| 6 | PII Obfuscation | `services/privacy` | pseudonymized identifiers + `pii_mode` |
| 7 | Normalization | `services/normalization` | universal field names |
| 8 | Validation | `services/normalization` | schema-validated `UniversalLogEvent` |

Downstream (post-store): `services/correlation`, `services/analytics`,
`services/security` (rules), risk scoring, alerting.

## 4. Data model

See [universal-schema.md](universal-schema.md). Core tables:

`users, roles, audit_logs, log_sources, processing_jobs, raw_logs, normalized_events,
security_alerts, security_rules, security_events, parser_packs, parser_versions,
pipeline_runs, pii_settings, templates, compression_records`.

`raw_logs.content` is the **verbatim original** and is never mutated. Normalized events
reference their raw log for full-provenance investigation.

## 5. Repository layer & search

All event queries go through `repositories/events.py`. `EventRepository` exposes
`search(EventQuery) -> EventPage`, `facets`, `timeseries` (dialect-aware) and
`get`, backed by SQL today; an `OpenSearchEventRepository` can be dropped in
later without touching services or the API.

## 5a. Parsers: three tiers

1. **Built-in** (`services/parsing/parsers/`) — Python, in code, for the common
   formats; provide match spans for the debugger.
2. **Declarative packs** (`services/parsing/declarative.py` + `parser_packs/*.yaml`
   + DB `parser_packs`/`parser_versions`) — pure data: hints, named-group
   regexes, field mappings, a fixed transform whitelist, `kv_expand`, embedded
   self-tests. No pack code runs.
3. **WASM** (`services/wasm/`) — a compiled module runs the extraction under
   `wasmtime` with no WASI and fuel/timeout/memory limits. See
   [wasm-sandbox.md](wasm-sandbox.md).

All three implement the same `BaseParser` interface and emit the same
`UniversalLogEvent`. The registry picks the best parser by `can_parse` score,
breaking ties by `specificity`.

## 5b. Dashboard

`GET /api/analytics/overview` aggregates **only** real rows: `raw_logs` status
counts, `normalized_events` facets, `processing_jobs.processing_rate`,
`security_alerts` by band, `security_events`. No metric is hard-coded.

## 6. Security model

Summarized here, full detail in [security-model.md](security-model.md):

- JWT access tokens (HS256), bcrypt password hashing (cost 12).
- RBAC: `VIEWER < ANALYST < ADMIN` (rank-based; a single required role means "or higher").
- Every log line is untrusted input — screened by the Security Shield, rendered safely,
  never executed.
- Custom parser code runs only inside the WASM sandbox with CPU/memory/time limits and
  no filesystem or network access.
- Audit log for auth events, user/role/config changes, alert actions, shield detections.
- Secrets only via environment variables.

## 7. Deployment

`docker compose up` builds three services: `db` (Postgres 16), `backend` (uvicorn,
runs `alembic upgrade head` on start), `frontend` (nginx serving the built SPA and
proxying `/api`). See [deployment.md](deployment.md).

## 8. Technology decisions & trade-offs

| Decision | Why | Trade-off |
|----------|-----|-----------|
| SQLite default for dev | zero-infra, students can run instantly | Postgres-only features avoided in ORM; JSON columns used generically |
| JWT (not server sessions) | stateless, simple for SPA + API | logout is client-side token disposal (audited) |
| Declarative parser packs | no arbitrary code in the API process | very unusual formats need a WASM parser |
| Synchronous pipeline | understandable to student devs, easy to debug | throughput bounded by one process (documented in perf benchmarks) |
| Rule-based detection first | deterministic, explainable, demo-safe | no novel-threat detection (future: ML) |

## Future scope

Real-time streaming · Kafka · distributed workers · OpenSearch/Elasticsearch scaling ·
enterprise connectors (real syslog relays, Windows Event Forwarding, vendor firewall
APIs) · threat-intel enrichment · SIEM & SOAR integration · real firewall/IAM/EDR
response with SOC approval workflow · automated account isolation · ML anomaly
detection · larger local LLMs · cloud deployment · enterprise multi-tenancy.

**These are not implemented.** The MVP simulates/recommends response actions only.
