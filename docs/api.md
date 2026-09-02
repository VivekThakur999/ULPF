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

### Log Explorer (Modules 13, 8-11)
| GET | `/api/logs` (alias `/api/logs/search`) | any | filtered event search; raw IP/username terms auto-pseudonymized under DETERMINISTIC_HASH (response `note` says so) |
| GET | `/api/logs/stats` | any | totals + facets (source/event_type/severity/parser/host) + hourly time series |
| GET | `/api/logs/facets` | any | facet counts for `?fields=` |
| GET | `/api/logs/pseudonymize` | any | `?value=&kind=` → pseudonym under current mode |
| GET | `/api/logs/{id}` | any | universal event + raw + re-run pipeline stages + PII transforms + related events + shield events |

### Correlation & detection (Modules 14-17)
| POST | `/api/detection/run` | ANALYST | evaluate RULE_1..8 over the last N hours → create/update alerts (deduped by entity) |
| POST | `/api/detection/correlate` | any | `{source_ip\|username\|host, center_time?, window_seconds}` → cross-source timeline |
| GET | `/api/detection/rules` | any | list the 8 rules (id/threshold/window/enabled) |
| PUT | `/api/detection/rules/{key}` | ADMIN | tune / enable / disable a rule (audited) |

### Alerts (Modules 17-18, 27)
| GET | `/api/alerts` | any | list, ordered by risk; filter `status` / `severity` |
| GET | `/api/alerts/{id}` | any | alert + transparent risk breakdown + incident timeline + related events |
| PUT | `/api/alerts/{id}` | ANALYST | status workflow (NEW/ACKNOWLEDGED/INVESTIGATING/RESOLVED/FALSE_POSITIVE) + note (audited) |

### Dashboard analytics (Module 25)
| GET | `/api/analytics/overview` | any | top cards + 9 chart datasets + source status — all from live DB counts |
| GET | `/api/analytics/timeline` | any | bucketed event-count series (`?bucket=hour&hours=`) |

### Parsers & packs (Module 20)
| GET | `/api/parsers` | any | every registered parser (builtin + declarative pack + WASM) |
| GET | `/api/parsers/{name}` | any | metadata + definition (packs) + embedded-test report |
| GET | `/api/parsers/{name}/versions` | any | version history (packs only) |
| POST | `/api/parsers/validate` | any | dry-run validate a YAML pack (regex compile + run its tests) |
| POST | `/api/parsers` | ADMIN | create/version a pack — validates, runs embedded tests, hot-registers (audited); rejects shadowing a built-in |
| POST | `/api/parsers/{name}/test` | any | run a parser against a sample line |

### WASM sandbox (Module 21)
| GET | `/api/wasm/status` | any | runtime availability + isolation summary + limits |
| POST | `/api/wasm/validate` | ADMIN | static-check a `wat`/`wasm_base64` module |
| POST | `/api/wasm/run` | ADMIN | run a module against one line, sandboxed + fuel/timeout/memory limited |

## Planned (later checkpoints)

`/api/ai/explain` (offline log explanation), `/api/compression/stats`,
`/api/response/simulate`, `/api/templates*`, `/api/demo/load`.

Each returns `422` with a Pydantic error list on invalid input, `401` when
unauthenticated, `403` when the role is insufficient.
