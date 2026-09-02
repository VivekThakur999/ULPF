# ULPF API

Base path: `/api`. Auth: `Authorization: Bearer <jwt>` on every route except
`/api/auth/login` and `/health`. Interactive docs: `GET /docs` (Swagger), `GET /redoc`.

RBAC: `VIEWER < ANALYST < ADMIN`. "Requires ANALYST" means analyst **or** admin.

## Implemented

### Auth & users (Phase 1–2)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/health` | public | liveness + DB status |
| POST | `/api/auth/login` | public | email+password → JWT |
| POST | `/api/auth/logout` | any | audited client-side logout |
| GET | `/api/auth/me` | any | current user |
| GET/POST/PUT/DELETE | `/api/users[/{id}]` | ADMIN | user management |
| GET | `/api/users/audit-logs` | ADMIN | paged audit log, filter by `action` |

### Sources (Module 2)
| GET | `/api/sources` | any | list configured sources |
| GET | `/api/sources/adapters` | any | adapter capability catalog (MVP-ready vs interface-only) |
| POST/PUT/DELETE | `/api/sources[/{id}]` | ADMIN | source CRUD |

### Ingestion (Module 3)
| POST | `/api/ingestion/upload` | ANALYST | multipart file → job (202) |
| GET | `/api/ingestion/samples` | any | list bundled synthetic samples |
| POST | `/api/ingestion/import-sample` | ANALYST | ingest a bundled sample |
| POST | `/api/ingestion/simulate` | ANALYST | generate + ingest a simulated stream |
| GET | `/api/ingestion/jobs[/{id}]` | any | job list / detail (real counters + progress) |
| GET | `/api/ingestion/jobs/{id}/records` | any | raw records, filter by `status` |

### Pipeline (Modules 5, 19)
| POST | `/api/pipeline/detect` | any | `{sample}` → `{format, confidence, candidates}` |
| POST | `/api/pipeline/test` | ANALYST | run the full pipeline on one line, return every stage's I/O (no persistence) |

### Privacy (Module 9)
| GET | `/api/privacy/settings` | any | current PII configuration |
| PUT | `/api/privacy/settings` | ADMIN | update mode / protected kinds / scope (audited) |
| POST | `/api/privacy/preview` | any | `{value, kind}` → pseudonym under current mode |

### Security shield (Module 4)
| POST | `/api/security/shield/check` | any | screen one line, return verdict + indicators |
| GET | `/api/security/events` | any | shield detections, filter by `verdict` / `job_id` |

## Planned (later checkpoints)

`/api/logs*` (explorer/search), `/api/correlation/*`, `/api/alerts*`,
`/api/analytics/*`, `/api/parsers*`, `/api/ai/explain`, `/api/compression/stats`,
`/api/response/simulate`.

Each returns `422` with a Pydantic error list on invalid input, `401` when
unauthenticated, `403` when the role is insufficient.
