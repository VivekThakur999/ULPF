# ULPF Security Model

## Authentication
- Email + password. Passwords hashed with **bcrypt** (cost 12), never stored or logged
  in plaintext.
- **JWT** access tokens (HS256), signed with `SECRET_KEY`, default lifetime 12h,
  carrying `sub` (user id) and `role`.
- Stateless: logout is client token disposal; the event is written to the audit log.

## Authorization (RBAC)
Ranks: `VIEWER=1 < ANALYST=2 < ADMIN=3`.
- `require_roles(ROLE)` → that role **or higher**.
- `require_roles(A, B)` → membership in an explicit set.
- ADMIN: users, sources, parser packs, privacy config, security rules, everything.
- ANALYST: view/process/search logs, investigate alerts, debugger, analytics.
- VIEWER: read-only.

## Untrusted input handling
- Every uploaded log line is untrusted. The **Security Shield** (Module 4) screens each
  line for terminal escape sequences, dangerous control characters, log-injection and
  known weaponization indicators → `SAFE | SUSPICIOUS | WEAPONIZED_LOG`.
- Suspicious/weaponized lines are **quarantined** (configurable) and never parsed
  normally; a `security_events` row preserves the evidence reference.
- Log content is **never executed**. The UI renders log text safely (no `dangerouslySetInnerHTML`).
- API inputs validated by Pydantic; DB access via SQLAlchemy (parameterized) only.
- File uploads: extension allow-list + size cap (`MAX_UPLOAD_BYTES`).

## Custom parser execution
- Declarative **parser packs** (YAML/JSON) — no code execution.
- **WASM sandbox** for custom modules: no filesystem, no network, CPU/memory/time
  limits, module validation, versioning, audit trail. Native code is never executed.

## Privacy
- Deterministic pseudonymization via **HMAC-SHA256** keyed with `PII_HMAC_KEY` and a
  configurable scope; same input → same pseudonym within a scope, enabling correlation
  without exposing the raw identifier.
- Modes: `OFF | MASK | DETERMINISTIC_HASH`. Plaintext PII is not stored when a
  protecting mode is active. We do **not** claim this alone makes the system
  "GDPR compliant".

## AI explanation layer

**AI explanations are advisory and do not determine security decisions.** ULPF's
deterministic engine is the sole authority for detection, severity, risk score,
correlation and alert generation. The AI layer only *describes* those results.

- **No cloud dependency.** Default provider is `LOCAL OFFLINE EXPLAINER`, a
  deterministic template — no model, no network. `OLLAMA LOCAL` is optional and
  only ever contacts `OLLAMA_BASE_URL`; it never downloads a model and falls
  back to the offline provider on any failure. No OpenAI/Anthropic/cloud code
  is imported (asserted by `tests/test_ai.py`).
- **Server-side evidence retrieval.** `/api/ai/explain` accepts only a record id
  or pasted text. Every security field (risk, rule, entity, correlation) is
  loaded from the DB here — a caller cannot inject fabricated evidence.
- **Evidence boundary.** The response separates authoritative `evidence` from
  advisory `explanation`; the UI renders them in distinct "ULPF EVIDENCE" and
  "AI EXPLANATION" sections and never merges them.
- **Untrusted input.** Pasted logs are labelled `UNTRUSTED LOG INPUT`, run
  through the normal pipeline (including the Security Shield), never persisted.
- **Prompt-injection handling.** The offline explainer is a fixed template and
  structurally immune - it emits no free-form text derived from the log. For
  Ollama, a strict system prompt instructs the model to treat all supplied
  content as data, the evidence is placed in a fenced block, control characters
  are stripped and the context is size-capped. `${jndi:…}`,
  `<system>ignore previous instructions</system>`, `DROP TABLE`, `<script>` and
  similar are treated as data (tested).
- **No actions.** AI output cannot trigger firewall / IAM / EDR / shell / DB
  operations. `explain()` is a read-only code path; `tests/test_ai.py` asserts
  repeated explanation calls leave alerts, rules, risk and severity unchanged.

## Auditing & observability
- `audit_logs`: auth (incl. failures), user/role changes, privacy & rule config
  changes, alert state changes, shield detections.
- Application logs never contain passwords, tokens or raw PII.

## Known limitations (MVP)
- No refresh-token rotation / token revocation list.
- Rate limiting is basic and applied only to auth + upload.
- The Security Shield is a heuristic screen, **not** a malware detector.
