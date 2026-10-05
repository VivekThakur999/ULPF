# Universal Log Pre-processing Framework: A Deterministic, Explainable Pipeline for Heterogeneous Security Log Normalization and Correlation

**SIH 2026 Problem Statement SIH26156 — Universal Log Pre-processing Framework (ULPF)**
**Organization: National Technical Research Organisation (NTRO)**

---

## Authors / Affiliation

*[Author names, student/team ID, institution name, department, and city to be inserted by the team — not fabricated here.]*

---

## Abstract

Security operations teams routinely ingest logs from heterogeneous sources — web servers, operating systems, firewalls, and applications — each with a different wire format, field vocabulary, and severity vocabulary. This heterogeneity fragments downstream security analysis: parsing, sanitization, privacy protection, schema normalization, and correlation are frequently implemented as separate, loosely-integrated tools. This paper presents the Universal Log Pre-processing Framework (ULPF), an implemented software system that combines a fixed eight-stage per-record processing pipeline — pre-parse security screening, format detection, pluggable parsing, field cleaning, field extraction, deterministic PII pseudonymization, field normalization, and validation — with a downstream deterministic, rule-based cross-source correlation and risk-scoring engine. ULPF outputs every event into a single canonical schema regardless of source format, screens every raw line for log-injection-class payloads before it is parsed, and applies keyed HMAC-based pseudonymization so that correlation across sources can operate on stable pseudonyms rather than raw identifiers. Detection is performed by eight hand-specified deterministic rules rather than a learned model, and each resulting alert carries a transparent, additive, named-factor risk score instead of an opaque numeric output. The system also includes an experimental sandboxed extension mechanism for third-party parser logic, a deterministic template-mining and lossless log-compression engine, an offline non-LLM alert explainer with a strict separation between server-computed evidence and advisory explanation, and a response-simulation module that produces only virtual recommended actions with no real system modification. We report two independently re-executed, single-run measurements obtained directly from the shipped implementation and its bundled sample data: a compression benchmark on a 600-line Apache access-log sample (6.2% size reduction, 600/600 byte-exact reconstructions) and a four-source synthetic brute-force detection scenario (one alert, risk score 93/100, critical severity, timeline spanning all four sources). All other performance, scalability, and accuracy claims — including a "risk 91/100" figure that appears in project documentation but does not match this independently re-executed run — are explicitly marked as not evaluated or as a documented discrepancy rather than asserted as validated results. This paper describes only what is implemented and verified in the current codebase, distinguishes it from optional/experimental and simulation-only components, and identifies the specific unevaluated claims that require further validation before publication or deployment.

---

## Keywords

Log preprocessing; heterogeneous log normalization; universal event schema; log injection; deterministic detection rules; explainable risk scoring; PII pseudonymization; template mining; lossless log compression; WebAssembly sandboxing; offline security AI; security information and event management (SIEM).

---

# 1. Introduction

Modern IT and OT environments generate log data from dozens of heterogeneous sources — web servers, operating system audit subsystems, firewalls, and custom applications — each emitting a different textual or structured format with inconsistent field names, timestamp conventions, and severity vocabularies. Before any meaningful security detection or correlation can occur, this raw data must be parsed, sanitized against log-injection attacks, screened for sensitive personal information, and mapped onto a common schema. In practice, these responsibilities are often distributed across separate ingestion agents, parsing rules, and privacy tooling that are integrated ad hoc around a downstream SIEM or log analytics platform [7], [9].

This paper documents the Universal Log Pre-processing Framework (ULPF), a system built for Smart India Hackathon 2026 problem statement SIH26156, sponsored by the National Technical Research Organisation (NTRO). ULPF is presented here strictly as implemented: every architectural claim in this paper is grounded in source code inspected as part of this work, and every quantitative result is either an independently re-executed measurement against the project's own bundled sample data, or explicitly marked as not evaluated. No academic novelty, superiority, or "first-of-its-kind" claim is made; the contribution is an integrated, auditable combination of established preprocessing techniques rather than a new detection algorithm.

# 2. Problem Statement and Motivation

SIH26156 calls for a framework that can take log data from arbitrary, heterogeneous sources and pre-process it into a form suitable for downstream security analysis, while protecting sensitive information and remaining resilient to log data that is itself adversarial (e.g., crafted to attack the logging pipeline). The practical motivation is threefold:

1. **Format heterogeneity.** Apache/Nginx access logs, Linux `auth.log`/syslog, Windows security events, application JSON logs, and firewall key-value logs each require different parsing logic, yet security analysis (e.g., "has this IP address touched multiple systems in the last ten minutes?") requires a single, queryable representation across all of them.
2. **Untrusted log content.** A raw log line is attacker-influenced input. Log-injection techniques — CRLF/log forging [15], [17] and message-content exploits such as the Log4Shell JNDI lookup vulnerability [18] — mean a preprocessing pipeline must treat every raw line as potentially hostile *before* any parser attempts to interpret it.
3. **Privacy exposure during correlation.** Cross-source correlation typically needs to link events by identifiers such as usernames, source IP addresses, or email addresses, which is in tension with minimizing the exposure of personal data in intermediate storage.

ULPF's stated scope is a pre-processing and downstream analysis pipeline, not a full SIEM platform: it does not attempt case management, long-term data-lake storage, dashboarding at scale, or compliance reporting.

# 3. Background and Related Work

**Log parsing and template mining.** Automated log parsing has been studied extensively; Drain [1] and Spell [2] are widely cited online/streaming parsers that separate a log message into constant template text and variable tokens, and a comprehensive benchmark [3] compares roughly a dozen such parsers on real-world datasets. ULPF's template-mining stage performs a conceptually similar template/variable separation, but does so via fixed, hand-specified token-type classification (IP address, UUID, MAC address, email, URL, timestamp, hash, number, quoted string) and position-wise anchor/variable decisions based on dominance and cardinality thresholds, rather than via a learned tree structure [1] or sequence-alignment algorithm [2].

**Universal/common log schemas.** The problem of normalizing heterogeneous log sources into one schema is addressed industrially by the Open Cybersecurity Schema Framework (OCSF) [4], the Elastic Common Schema (ECS) [5], and the long-standing Common Event Format (CEF) [6]. These are broad, externally governed, extensible taxonomies intended for cross-vendor interoperability. ULPF's Universal Event schema addresses the same normalization problem but is a single fixed, internal schema (approximately 28 fields) scoped to its own pipeline, not an externally versioned standard.

**SIEM architecture and log management.** NIST SP 800-92 [8] provides foundational guidance on log management infrastructure and analysis practice, and empirical work on real-world SIEM deployments [7] documents the practical difficulty of preprocessing large volumes of heterogeneous, unstructured log data — the exact problem ULPF's ingestion and normalization stages target. A recent survey [9] summarizes current SIEM feature sets and best practices at a platform level broader than ULPF's scope.

**Log-based anomaly detection and correlation.** The dominant academic line of work in log-based anomaly detection is statistical/machine-learning based, exemplified by the Loglizer evaluation of six ML detection methods [10] and surveyed broadly in [11]. Host-based intrusion detection research spans both rule/signature-based and ML-based approaches [12]. ULPF's detection engine is deliberately positioned at the rule-based end of this spectrum: eight hand-specified deterministic rules, explicitly documented in source as using "no ML, no randomness," trading potential generality for full explainability and reproducibility.

**Log compression.** Template-structure-aware log compression has prior academic treatment in LogZip [13], which discovers template/variable structure via iterative clustering, and Cowic [14], which compresses per-column rather than per-template. ULPF's compression engine performs the same template/variable separation as a compression pre-step, but derives templates from the same deterministic token-classification mining described above rather than corpus-wide clustering, and evaluates success only via exact byte-for-byte reconstruction of the original record.

**Log injection and standards.** OWASP documents log injection/forging as an attack class [15], [16], MITRE's CWE-117 formalizes it as a weakness category [17], and the Log4Shell vulnerability (CVE-2021-44228) [18] is a widely documented real-world incident of message-content exploitation. OWASP Top 10:2021 situates injection broadly as category A03 [30]. ULPF's security-shield stage screens for exactly this attack class before any parser interprets a line.

**Privacy-preserving log analysis.** Recent work examines which categories of log content actually warrant anonymization [19] and proposes salt/keyed-hash-based anonymization schemes that preserve correlation structure [20], which is architecturally close to ULPF's own keyed-HMAC pseudonymization design. Pseudonymization applied at ingestion time has also been described in a GDPR-focused survey context [21], [22]; these sources are cited here only for architectural placement of pseudonymization within a pipeline, not as evidence that ULPF makes or satisfies any legal compliance claim, which it does not.

**WebAssembly sandboxing.** ULPF's experimental parser-sandboxing path is built on wasmtime. Academic security analysis of WebAssembly notes that binary-level memory-safety guarantees do not automatically transfer from native code [23], and more recent work identifies resource-isolation weaknesses in WASM runtime deployments [24], which is the specific motivation for pairing wasmtime with explicit fuel metering, wall-clock epoch interrupts, and memory limits rather than relying on default sandboxing alone, per the runtime's own security documentation [25].

**Offline/explainable AI for security.** Explainable AI for cybersecurity is surveyed broadly in [26]. Empirical work on analyst trust in AI-driven SOC tooling [27] documents real risks of over-trusting AI explanations when they are not clearly subordinated to authoritative evidence. A very recent (2026, not yet peer-reviewed) preprint describing a rule-engine-plus-local-LLM incident-response architecture with the LLM restricted to advisory explanation only [28] is the closest architectural analogue found in the literature to ULPF's own hard separation between server-computed "evidence" and advisory "AI explanation."

# 4. Research Gap

The literature above addresses log parsing [1]–[3], schema normalization [4]–[6], SIEM-level architecture [7]–[9], detection/correlation [10]–[12], compression [13], [14], injection threats [15]–[18], [30], privacy [19]–[22], sandboxing [23]–[25], and AI explainability [26]–[28] largely as separate research and engineering concerns, each studied or productized independently. This is not a claim that any individual existing product or paper is incapable of solving its own sub-problem; it is an observation that pre-parse security screening, deterministic multi-format parsing, deterministic identifier pseudonymization for correlation, single-schema normalization, deterministic rule-based correlation with a transparent (non-black-box) risk score, and an advisory-only offline explanation layer are not commonly demonstrated together as one coherent, auditable pipeline in a single open implementation. ULPF's contribution, evaluated in this paper, is this specific architectural combination — not a new parsing algorithm, a new detection model, or a new cryptographic scheme.

# 5. System Requirements

Functional requirements realized in the implementation: (a) ingest heterogeneous log files via upload; (b) detect format and select an appropriate parser automatically; (c) screen raw content for log-injection-class payloads prior to parsing; (d) normalize parsed fields into one canonical event schema; (e) pseudonymize identifying fields; (f) correlate events across sources by shared entity; (g) generate alerts with an explainable risk score; (h) support role-based access control and audit logging; (i) support extensible parser definitions without arbitrary code execution. Non-functional requirements addressed by design (not independently load-tested in this work; see Section 20): determinism/reproducibility of detection and scoring, and non-execution of untrusted log content or untrusted parser code outside a sandboxed path.

# 6. Proposed ULPF Architecture

ULPF is organized into three layers. The **ingestion and pipeline layer** turns uploaded raw bytes into a stream of individual raw records (Section 7) and runs each record through a fixed eight-stage per-record pipeline ending in a `NormalizedEvent` row (Section 9). The **analysis layer** operates on already-normalized events in batch, after ingestion: cross-source correlation, deterministic rule evaluation, risk scoring, and alert generation (Sections 10–11) are explicitly *not* pipeline stages — they run as a separate step triggered after each ingestion job completes, over a rolling time window across all sources, which is what enables cross-job, cross-source correlation. The **extension and assistance layer** covers the pluggable/sandboxed parser architecture (Section 12), template mining and compression (Section 13), the offline AI explainer (Section 14), and the response simulator (Section 15). *(Figure 1)*

# 7. Log Processing Pipeline

**Ingestion.** The implemented ingestion path accepts an uploaded file and a declared/optional format hint. A reader module decodes bytes (trying UTF-8, UTF-8-with-BOM, then Latin-1 as a last resort) and splits the content into individual records depending on container type: newline-delimited for `.log`/`.txt`/`.jsonl`/`.ndjson`/`.syslog`, JSON array/object unwrapping for `.json` (including a search for a nested `events`/`records`/`logs`/`data` array), and row-to-logfmt conversion for `.csv`. Records longer than 64 KB are truncated. Content-hash-based duplicate detection is applied per job. Two log-source adapters are functional in the current implementation — `FILE` (upload) and `SIMULATED` (a synthetic demo-data generator used for demonstration, not a real source) — while `SYSLOG`, `HTTP`, `WINDOWS`, and `FIREWALL` adapters exist only as interface stubs that self-report a `NOT_CONFIGURED` status; the codebase itself documents that these describe the interface a production connector would implement without claiming a live enterprise connection works. This is a deliberate, honest design choice recorded in the adapter module's own docstring, not an oversight discovered during this review.

**Per-record pipeline (fixed order).** Every accepted record passes through exactly eight stages, in this fixed order, as enforced in `pipeline/service.py`:

1. `security_shield` — regex-based screening for log-injection-class content (Section 8).
2. `format_detection` — confidence-scored guess of the log's format (e.g., Apache combined, syslog, JSON), distinct from the parser-selection step that follows and distinct from the security-shield verdict.
3. `parsing` — a registry of parsers is scored against the record and the best match extracts fields (Section 12).
4. `cleaning` — field-level validation: IP addresses and ports are validated and canonicalized, timestamps are checked as parseable, HTTP/status codes are coerced to integers, control characters are stripped, and surrounding whitespace/quotes are normalized. Any field that fails validation is never silently dropped: it is preserved under a `<field>_raw` key alongside a warning, so information loss is auditable rather than implicit.
5. `field_extraction` — implicit in the parser's structured output; downstream stages consume the extracted field dictionary.
6. `pii_obfuscation` — deterministic pseudonymization of identifying fields (Section 8).
7. `normalization` — an alias table maps over 70 recognized raw field-name variants (e.g., `srcip`, `source_ip`, `sourceaddress`, `c_ip` all map to `source_ip`) onto the canonical schema, plus dedicated normalization of severity strings/syslog numeric levels and event-type strings via lookup tables; unrecognized fields are preserved in an `extra` JSON field rather than discarded.
8. `validation` — final construction and Pydantic validation of the canonical event object before it is persisted as a `NormalizedEvent` row.

A record can exit the pipeline early as `QUARANTINED` (security shield judged it too dangerous to continue) or `INVALID` (it could not be turned into a usable event); both outcomes and per-record processing errors are recorded on the job and on the raw-log row, and none of it is silently discarded. *(Figure 2)*

**Job orchestration.** Ingestion tracks real per-job counters — total, processed, invalid, duplicate, quarantined, and blank-line counts — plus a real `processing_rate` computed from wall-clock elapsed time, committed to the database in batches of 200 records. After a job completes, cross-source rule-based detection (Section 10) is triggered automatically over a rolling window across *all* recently ingested events, not just the current job, which is what allows a single alert to span multiple, separately uploaded log files; a failure in this post-ingestion detection step is caught and logged without failing the ingestion job itself.

# 8. Security and Privacy Design

**Security Shield.** Before any parser interprets a raw line's content, a dedicated pre-parser regex screen classifies it as `SAFE`, `SUSPICIOUS`, or `WEAPONIZED_LOG`. The shield distinguishes two categories of finding: an **injection** finding (content that threatens the log-processing pipeline itself — CRLF/log injection [15], [17], Log4Shell-style `${jndi:...}` template expressions [18], generic template-injection syntax, format-string specifiers, ANSI/OSC terminal escape sequences, and disallowed control characters) versus a **payload** finding (an attack recorded inside an otherwise well-formed log line, such as a SQL-injection string or path-traversal sequence appearing in a web-server access log, which is evidence of an attack against some *other* system, not a threat to ULPF itself). Lines classified `WEAPONIZED_LOG` are always quarantined; lines classified `SUSPICIOUS` are quarantined according to a configurable policy flag. The shield never executes or interprets log content as code; it only pattern-matches against it. This stage exists specifically to prevent the class of vulnerability exemplified by Log4Shell [18] and by log-forging attacks generally [15]–[17] from propagating past the point of ingestion.

**PII pseudonymization.** Identifying fields (source/destination IP, username, email) can be pseudonymized using a keyed HMAC-SHA256 construction, producing a deterministic, fixed-format pseudonym (a short prefix plus a truncated uppercase hex digest) so that the *same* raw identifier always maps to the *same* pseudonym within a given key/scope. Three modes are supported: `OFF` (no transformation), `MASK` (static redaction), and `DETERMINISTIC_HASH` (the pseudonymization described above). This design is architecturally consistent with recent proposals for salt/keyed-hash-based log anonymization that preserve correlation structure while removing raw identifiers from intermediate storage [20], and with the general principle that pseudonymization should be applied at or near ingestion time [21], [22]. **No claim of GDPR or other regulatory compliance is made anywhere in the codebase, and none is made in this paper** — pseudonymization here is a technical correlation-preserving privacy control, not a certified compliance mechanism, consistent with the observation that legal compliance and technical pseudonymization are distinct concerns [22].

**RBAC and audit.** Authentication uses JWT (HS256) with bcrypt-hashed passwords (12 rounds). A three-tier role model (`ADMIN` > `ANALYST` > `VIEWER`) gates sensitive endpoints — for example, running detection or modifying rules requires an analyst or admin role — and an `AuditLog` model records actor, action, and target for security-relevant operations (login, job creation, detection runs, and rule changes were all observed emitting audit entries during this review).

# 9. Universal Event Model

Every record that survives the pipeline is stored as a `NormalizedEvent` row conforming to a single schema (`schema_version = "1.0"`) of approximately 28 fields, grouped as: **provenance** (job ID, raw-log ID, ingestion timestamp), **core** (event timestamp, source, host, event type, severity), **identity** (username, email, source/destination IP, source/destination port, protocol), **action/outcome** (action, status, process, service, URL, HTTP method, response code), **content** (message, and an `extra` JSON catch-all for fields with no canonical home), **quality metadata** (per-field confidence scores, overall confidence, processing status), and **provenance/versioning** (verbatim raw log text, parser name and version, schema version, PII mode/protection flag, and an optional template ID linking to a mined template). Severity is constrained to a fixed vocabulary (`info`/`low`/`medium`/`high`/`critical`) via the normalization-stage alias table, which also maps syslog's numeric severity levels (0–7) onto this vocabulary. *(Figure 3, Table 2)*

# 10. Cross-Source Correlation and Threat Detection

Correlation and detection operate on already-normalized events, across all recently ingested sources, not as a pipeline stage. The correlation engine assembles a chronological timeline of events sharing an entity key (source IP, username, or host) within a time window, which is the mechanism that allows a single incident to be reconstructed from multiple, independently uploaded log files.

Detection itself is performed by eight deterministic rule functions (Table 4), each a pure function over the event set with no machine learning and no randomness, as stated directly in the module's own docstring. A shared helper computes, for a set of timestamps, the largest number of events falling inside any window of a configured length (a sliding-window maximum-count algorithm), which several rules reuse to detect bursts. Rule outcomes ("hits") that reference the same entity are merged into one alert when their underlying event-ID sets overlap by 60% or more, so that multiple rules firing on the same underlying incident (e.g., a brute-force pattern and a subsequent successful login for the same source IP) surface as a single, consolidated alert rather than duplicate noise.

This is a deliberate design choice positioned at the deterministic/rule-based end of the detection-methods spectrum documented in the literature [10]–[12], rather than the statistical/ML-based end that dominates recent academic log-anomaly-detection work [10], [11]. The trade-off is explicit: rule-based detection is fully explainable and reproducible but limited to the specific patterns its rules encode, whereas ML-based approaches can in principle generalize to unseen patterns at the cost of explainability.

# 11. Risk Scoring and Incident Investigation

Each alert carries a risk score in the range 0–100, computed as an explicit sum of named, human-readable factors (e.g., "12 failed authentication events observed" contributing 30 points, "the same entity appears across 4 independent log sources" contributing 20 points), with the raw sum compressed above a threshold of 60 (scores above 60 are mapped as `60 + 0.6 × (raw − 60)`, rounded) to keep the scale bounded while still differentiating high-severity incidents. Fixed bands (critical ≥ 85, high ≥ 65, medium ≥ 40, low ≥ 15, info otherwise) translate the numeric score into a severity label. Every factor, its point contribution, and a one-line human-readable justification are returned alongside the score — there is no opaque or black-box component in this calculation, and the paper's authors found no directly matching precedent for this exact scoring design in the reviewed literature; it is treated here as ULPF's own design choice rather than as validated against or derived from prior published work.

Incident investigation is supported via a per-alert detail view exposing the full contributing timeline (all related events, in order, with their source) and the alert's status workflow (e.g., transitioning from `NEW` to an analyst-assigned status, with invalid status values rejected). *(Figure 5, Table 5)*

# 12. Extensible Parser Architecture

Parsing uses a registry of parsers, each exposing a confidence-scoring method (`can_parse`) used to auto-select the best match for a given sample, with an optional format hint that wins if its own confidence exceeds a threshold. Three parser mechanisms are implemented:

1. **Built-in Python parsers** — eight hand-written parsers (Linux auth log, syslog, Apache, Nginx, firewall, generic JSON, generic key-value, and a raw fallback that never fails to "parse," preserving the line as a message field so no data is silently lost).
2. **Declarative YAML "parser packs"** — pure-data parser definitions consisting of named-group regular expressions (capped at 25 patterns per pack), field-name mappings, and a fixed, closed allow-list of value transformations (`int`, `float`, `lower`, `upper`, `strip`, `strptime`, `epoch`, `const`). No code from a pack is ever executed — only Python's `re` module and this fixed transform set — and each pack can embed self-test cases that are validated before the pack is trusted. Three such packs (CEF, HAProxy, PostgreSQL, all version 1.0.0) are shipped on disk and were confirmed loaded at startup during this review.
3. **An experimental WebAssembly-sandboxed parser path** — built on the `wasmtime` runtime (confirmed installed and importable), using an empty `Linker` with no WASI imports (so a sandboxed module has no filesystem, network, or OS access by construction), fuel metering (a default instruction budget of 5,000,000 units), a wall-clock watchdog implemented via epoch interrupts (default 250 ms), and a hard memory cap via `StoreLimits` (default 16 MiB), with a minimal three-export ABI (`memory`, `alloc`, `ulpf_parse`). This path is registered with one proof-of-concept parser and an (untested in this review) architecture for database-stored WASM packs; it is explicitly a secondary, experimental mechanism for higher-risk custom parser logic, not the primary parsing path used by any shipped sample dataset. Its design — pairing a WASM sandbox with explicit resource limits rather than relying on the runtime's default isolation alone — is consistent with published findings that WASM's memory-safety guarantees do not automatically transfer from native-code assumptions [23] and that WASM runtime resource isolation itself has documented weaknesses [24]; wasmtime's own security documentation [25] was used to describe the fuel/epoch mechanism accurately, since no separate peer-reviewed publication of that specific mechanism could be found. *(Table 3)*

# 13. Template Mining and Lossless Compression

Template mining tokenizes each log line by whitespace while capturing exact separators, classifies each token by type (IP address, UUID, MAC address, email address, URL, timestamp, hash, number, or quoted string), and then, position by position across a cluster of similarly-shaped lines, decides whether that position is an "anchor" (constant across the cluster) or a "variable" (masked out) using dominance and cardinality thresholds (a position is treated as variable if no single token value dominates at least half of observed occurrences, or if it has high cardinality). Each resulting template is assigned a stable ID derived from a SHA-256 signature of its token pattern. No machine-learning model and no code execution are involved, in contrast to clustering-based template discovery such as LogZip [13] or tree-based online parsing such as Drain [1].

Compression stores each matched record as a compact payload referencing its template key plus only its variable values, and — critically — every compressed record is reconstructed and byte-compared against the original before being counted as a successful compression; a record that cannot be reconstructed exactly is not included in the reported savings. This benchmark methodology was independently re-executed for this paper directly against the shipped implementation and its bundled sample dataset (`sample_logs/application/bulk_access.log`, 600 lines, Apache combined format), via the project's own REST API (`/api/templates/mine` then `/api/compression/benchmark`), producing:

| Metric | Value |
|---|---|
| Input lines | 600 |
| Templates mined | 1 (TPL-0001; 12 tokens, 6 variable positions) |
| Original size | 62,091 bytes |
| Compressed payload size | 57,891 bytes |
| Template/metadata overhead | 353 bytes |
| Total compressed size | 58,244 bytes |
| Size reduction | 6.2% |
| Byte-exact reconstructions | 600 / 600 (100%) |
| Measured throughput | ≈1,680 events/second |

This is a single run on a single, small, homogeneous dataset on one machine; it is reported as exactly that, not as a general compression-ratio claim across formats, dataset sizes, or hardware (see Section 20 and Section 22). No comparison against LogZip [13], Cowic [14], or generic compressors (e.g., gzip) was performed in this work.

# 14. Offline AI Log Intelligence

Alert and event explanations are generated by a **local, deterministic, template/dictionary-based explainer** that performs no machine-learning inference and makes zero network calls; it is explicitly not a large language model. An optional local LLM path exists via Ollama, which automatically falls back to the deterministic explainer if the Ollama service is unavailable — this fallback logic was verified in code, though no local Ollama server was confirmed running during this review, so the LLM path's own behavior was not independently re-executed. In both cases, the evidence given to the explanation layer is always retrieved server-side from the alert's own computed data; client-supplied "evidence" is never trusted or accepted. This produces a hard separation between **ULPF evidence** (the alert's rule hits, risk factors, and timeline — authoritative) and **AI explanation** (natural-language text describing that evidence — advisory only, never a substitute for the evidence itself). This separation is consistent with survey-level guidance on explainable AI for cybersecurity [26] and, more directly, with empirical findings that blurring the line between authoritative evidence and AI-generated explanation increases analyst over-trust and cognitive risk in SOC settings [27]. It is architecturally closest to a very recent (2026, preprint, not yet peer-reviewed) proposal for a rule-engine-plus-local-LLM design in which the LLM is restricted to advisory explanation while a deterministic rule engine retains all decision authority [28]; this comparison is noted for architectural similarity only, not as evidence that ULPF's design was derived from or validated against that specific work.

# 15. Safe Response Simulation

The response-simulation module produces only **virtual, simulated** recommended actions across four kinds — `virtual_firewall`, `virtual_host_isolation`, `virtual_account_hold`, and `virtual_monitoring`. Every simulated action carries a hardcoded `simulation: true` / `no_real_change: true` marker, and the broader recommended-response object's `auto_execute` flag is always `False`. Source-level inspection, backed by a source-scanning automated test, confirms the module contains no subprocess, shell, or network-call imports of any kind. **This module performs no real system modification whatsoever — it cannot open a firewall port, isolate a host, lock an account, or take any other real enforcement action, and no such capability exists anywhere in the current codebase.** It must not be described, in this paper or elsewhere, as automated incident response; it is a decision-support and demonstration aid only.

# 16. Implementation

The backend is implemented in Python using FastAPI with Pydantic v2 models and SQLAlchemy 2.0 ORM, running against SQLite in development and PostgreSQL 16 in the Docker Compose deployment. Configuration is environment-variable driven via `pydantic-settings`, with safe development defaults (e.g., a SQLite file database and a clearly-marked "dev-only-insecure" default secret key that must be overridden in production) and an explicit fix, applied during this project's development, to treat a *present-but-blank* environment variable the same as an *absent* one (needed because some hosting platforms inject configured-but-empty variables rather than omitting them). The frontend is a React/TypeScript/Vite single-page application. Deployment is supported via a three-service Docker Compose topology (PostgreSQL 16, the FastAPI backend, and an nginx-served frontend build) and, separately, a Vercel serverless configuration mapping API and static-asset routes to distinct services. The backend test suite comprises 19 pytest files with 173 passing tests at the last verified baseline, covering pipeline stages, individual detection rules, compression reconstruction, PII pseudonymization, RBAC enforcement, and the response simulator's zero-subprocess/shell/network guarantee; frontend end-to-end coverage consists of exactly one Playwright specification (login flow), which is minimal and should not be read as comprehensive UI test coverage. *(Figure 6)*

# 17. Experimental Methodology

Two quantitative results are reported in this paper, both obtained by independently re-executing the shipped implementation against its own bundled sample data during the preparation of this paper (not taken from documentation or prior runs without re-verification):

1. **Compression benchmark**: the project's `sample_logs/application/bulk_access.log` (600 lines) was uploaded through the real ingestion API, templates were mined via `/api/templates/mine`, and the benchmark was run via `/api/compression/benchmark`, all against a fresh SQLite database created for this run.
2. **Detection scenario**: the project's bundled `sample_logs/security_scenarios/scenario_brute_force/` dataset (four files — `firewall.log`, `linux.log`, `application.jsonl`, `windows.jsonl`, all referencing a single synthetic attacker IP) was ingested in sequence through the real ingestion API, detection was triggered via `/api/detection/run`, and the resulting alert and incident timeline were retrieved via the real alert-detail API.

Both runs were performed once, on a single development machine, against synthetic sample data bundled with the repository (not real-world or production traffic), and are reported as such. No statistical repetition, no varied hardware, and no varied dataset composition were performed; these are explicitly single-run demonstrations of the implementation working end-to-end, not benchmarks suitable for generalizable performance claims.

# 18. Results and Evaluation

**Compression.** See Section 13 for the full result. Reduction was 6.2% with 100% byte-exact reconstruction across all 600 lines, on a highly repetitive single-format dataset (a single Apache access-log template accounted for all 600 lines) — a favorable case for template-based compression, and not representative of a heterogeneous, multi-format corpus.

**Detection scenario.** Ingesting the four-source brute-force scenario (21 total normalized events across `application`, `firewall`, `linux`, and `windows` sources, 0 quarantined, 0 invalid) and running detection produced exactly one alert, keyed to rule `RULE_6` ("Failed auth burst followed by success"), with severity `critical` and **risk score 93/100**. The risk breakdown comprised eight named factors: failed-authentication volume (30 pts, 12 failed authentication events), cross-source correlation (20 pts, entity present across 4 independent sources), event severity (15 pts, highest individual event severity "high"), successful login after failures (15 pts), multiple affected hosts (14 pts, 3 hosts: `WIN-DC01`, `db-02`, `web-01`), multiple targeted accounts (9 pts, 3 accounts), time concentration (7 pts, 21 events in ≈4.2 minutes), and repeated blocked connections (5 pts, 5 firewall denials) — summing to a raw 115 points, compressed above the 60-point threshold to the reported 93. The alert's incident timeline contained 21 entries and 21 related events spanning all four ingested sources under one pseudonymized entity (`IP_5AF3E1`), demonstrating that cross-source correlation via pseudonymized identifiers functioned end-to-end for this scenario.

**Discrepancy disclosure.** Project documentation (README) states a risk score of "91/100" for this same scenario. The measurement independently re-executed for this paper produced **93/100**, not 91. Both values fall within the same "critical" band and do not change the qualitative conclusion that the scenario is correctly flagged, but the paper's authors could not reconcile the exact figure with the value currently produced by the shipped code, and no attempt is made here to select whichever number is more favorable. This discrepancy is reported honestly and should be investigated (e.g., for a version drift between when the README was written and the current scoring logic) before either figure is cited elsewhere. *(Table 5)*

**Test suite.** 173 backend tests passing across 19 files at the last verified baseline is reported as a qualitative correctness signal (the implementation behaves as its own authors specified), not as a coverage percentage or a substitute for the accuracy/precision/recall measurements listed as not evaluated in Section 20.

# 19. Security Analysis

The security shield's regex-based pre-parse screening addresses the log-injection attack class documented by OWASP [15]–[16] and MITRE [17], and specifically targets Log4Shell-style [18] message-content patterns before any parser touches a line; it was not, however, subjected to adversarial red-teaming or bypass testing in this work beyond its own unit tests — such evaluation is listed as future work (Section 23). The declarative parser-pack mechanism is restricted by construction to regular-expression matching and a fixed, closed transformation allow-list, with no code execution, which removes an entire class of "malicious parser pack" risk by design rather than by runtime enforcement. The experimental WASM parser sandbox adds defense-in-depth for cases where that guarantee is insufficient (e.g., a genuinely programmable parser extension), using an empty linker (no WASI, hence no filesystem/network/OS access from within the sandbox), fuel metering, wall-clock epoch interrupts, and a memory cap; this design explicitly does not treat WASM's own isolation as sufficient on its own, consistent with published findings on WASM binary-security limitations [23] and WASM-runtime resource-isolation weaknesses [24] — but the sandbox itself was not independently stress-tested or red-teamed as part of this work. The response-simulation module's zero real-system-modification property was verified by direct source inspection and is additionally enforced by an automated source-scanning test in the project's own test suite, giving it stronger assurance than most of the other claims in this section, which rest on design inspection alone rather than adversarial testing.

# 20. Performance Analysis

**Not evaluated in the current implementation:** sustained ingestion throughput or latency at scale (beyond the two single-run measurements in Section 18), behavior under concurrent ingestion jobs, CPU and memory profiling under load, horizontal scaling behavior of the Docker Compose deployment, and compression/detection performance across dataset sizes or formats other than the two specific samples measured. The two throughput figures reported in this paper (≈1,680 compression events/sec on 600 lines; ingestion rates of 66–232 records/sec observed incidentally during the detection-scenario run, on small files of 3–9 records each) are single-run, single-machine, small-sample measurements and must not be extrapolated into general performance claims.

# 21. Comparison with Existing Approaches

This comparison is presented descriptively, without ranking or a declared "winner," since no head-to-head benchmark against any existing product or research system was performed. Relative to ML-based log-parsing [1]–[3] and ML-based anomaly-detection approaches [10], [11], ULPF trades potential generalization to previously unseen log formats or attack patterns for full determinism, reproducibility, and human-readable explainability at both the parsing (template-mining) and detection (risk-scoring) stages. Relative to broad, externally governed normalization schemas such as OCSF [4] and ECS [5], ULPF's Universal Event schema is narrower and internal to its own pipeline rather than a cross-vendor interoperability standard. Relative to full SIEM platforms [7], [9], ULPF addresses only the ingestion-through-detection portion of the workflow and does not attempt case management, long-term analytics storage at scale, or compliance reporting. *(Table 6)*

# 22. Limitations

- The two quantitative results in this paper are single-run measurements on small, synthetic, bundled sample data on one development machine; they are not evidence of performance, accuracy, or scalability under production conditions.
- The compression benchmark was measured on a single, highly repetitive, single-format dataset (600 lines matching one template) and does not represent compression behavior on heterogeneous or less repetitive log data.
- The eight detection rules were exercised against one synthetic scenario designed to trigger them; no measurement of false-positive or false-negative rates against real-world or adversarially varied traffic exists.
- The exact risk-score figure (93) obtained by re-running the brute-force scenario does not match the "91" figure in project documentation; this discrepancy is unresolved as of this writing.
- "Demo Mode," described in the project's README, was not found anywhere in the backend or frontend codebase during this review and must not be treated as an implemented feature.
- Only `FILE` upload and a synthetic `SIMULATED` generator are functional log-source adapters; `SYSLOG`, `HTTP`, `WINDOWS`, and `FIREWALL` adapters are honest interface stubs with no live connectivity.
- Frontend end-to-end test coverage is minimal (one specification file); UI correctness beyond that path was not independently verified as part of this paper.
- The WASM sandbox and the security shield were evaluated by design/source inspection only, not by adversarial or penetration testing.
- No claim of legal/regulatory compliance (e.g., GDPR) is made or supported by this work.

# 23. Future Work

Future work that is technically sensible given the current architecture, without extending into unimplemented capability claims: (a) adversarial/red-team evaluation of the security shield's regex coverage and of the WASM sandbox's resource limits; (b) construction of a labeled evaluation corpus to measure detection-rule precision/recall/F1 against both synthetic and real-world traffic; (c) load and scalability testing of the ingestion pipeline and Docker Compose deployment under sustained and concurrent load; (d) compression benchmarking across a broader set of formats and dataset sizes, including comparison against established template-based approaches such as LogZip [13]; (e) implementation of at least one functional live-source adapter (e.g., a real syslog listener) to replace one of the current interface stubs; (f) formal reconciliation of the risk-scoring discrepancy identified in Section 18; (g) expansion of frontend end-to-end test coverage beyond the current single specification.

# 24. Conclusion

ULPF implements a fixed, auditable pipeline that combines pre-parse log-injection screening, pluggable and sandboxed parsing, deterministic PII pseudonymization, single-schema normalization, deterministic cross-source correlation and rule-based detection with a transparent risk score, deterministic template mining and lossless compression, an evidence-subordinated offline AI explainer, and a simulation-only response module. Two independently re-executed measurements confirm that the compression and detection paths function end-to-end on the project's own bundled sample data, while a documented discrepancy between a project-documentation figure and the independently re-measured risk score, along with a substantial list of unevaluated performance and accuracy claims, are disclosed rather than glossed over. The system is best characterized as an integrated, explainable combination of established preprocessing and detection techniques applied to the specific problem of heterogeneous security log pre-processing, rather than as a novel algorithm or a production-scale SIEM replacement.

---

# References

[1] P. He, J. Zhu, Z. Zheng, and M. R. Lyu, "Drain: An Online Log Parsing Approach with Fixed Depth Tree," in *Proc. IEEE Int. Conf. Web Services (ICWS)*, 2017.

[2] M. Du and F. Li, "Spell: Streaming Parsing of System Event Logs," in *Proc. IEEE Int. Conf. Data Mining (ICDM)*, 2016, pp. 859–864, doi: 10.1109/ICDM.2016.0103.

[3] J. Zhu, S. He, J. Liu, P. He, Q. Xie, Z. Zheng, and M. R. Lyu, "Tools and Benchmarks for Automated Log Parsing," in *Proc. 41st Int. Conf. Software Engineering: Software Engineering in Practice (ICSE-SEIP)*, 2019, doi: 10.1109/ICSE-SEIP.2019.00021.

[4] Open Cybersecurity Schema Framework (OCSF), Linux Foundation. [Online]. Available: https://ocsf.io/

[5] Elastic Common Schema (ECS) Reference, Elastic. [Online]. Available: https://www.elastic.co/guide/en/ecs/current/ecs-reference.html

[6] Common Event Format (CEF) Implementation Standard, v25, OpenText/Micro Focus (ArcSight). [Online]. Available: https://www.microfocus.com/documentation/arcsight/arcsight-smartconnectors/pdfdoc/common-event-format-v25/common-event-format-v25.pdf

[7] M. Cinque, D. Cotroneo, and A. Pecchia, "Challenges and Directions in Security Information and Event Management (SIEM)," in *Proc. IEEE Int. Symp. Software Reliability Engineering Workshops (ISSREW)*, 2018, pp. 95–99.

[8] K. Kent and M. Souppaya, "Guide to Computer Security Log Management," NIST Special Publication 800-92, 2006, doi: 10.6028/NIST.SP.800-92.

[9] M. Vardalachakis, M. Vasilakis, and M. Tampouratzis, "A Comprehensive Analysis of Features, Benefits, Challenges, and Best Practices of Security Information and Event Management (SIEM) Solutions," *Computer Sciences & Mathematics Forum*, vol. 12, no. 1, art. 18, 2026, doi: 10.3390/cmsf2025012018.

[10] S. He, J. Zhu, P. He, and M. R. Lyu, "Experience Report: System Log Analysis for Anomaly Detection," in *Proc. IEEE Int. Symp. Software Reliability Engineering (ISSRE)*, 2016, pp. 207–218.

[11] S. He, P. He, Z. Chen, T. Yang, Y. Su, and M. R. Lyu, "A Survey on Automated Log Analysis for Reliability Engineering," *ACM Computing Surveys*, vol. 54, no. 6, 2021, doi: 10.1145/3460345.

[12] R. A. Bridges, T. R. Glass-Vanderlan, M. D. Iannacone, M. S. Vincent, and Q. Chen, "A Survey of Intrusion Detection Systems Leveraging Host Data," *ACM Computing Surveys*, vol. 52, no. 6, art. 128, 2019, doi: 10.1145/3344382.

[13] J. Liu, J. Zhu, S. He, P. He, Z. Zheng, and M. R. Lyu, "Logzip: Extracting Hidden Structures via Iterative Clustering for Log Compression," in *Proc. 34th IEEE/ACM Int. Conf. Automated Software Engineering (ASE)*, 2019, doi: 10.1109/ASE.2019.00085.

[14] H. Lin, J. Zhou, B. Yao, M. Guo, and J. Li, "Cowic: A Column-Wise Independent Compression for Log Stream Analysis," in *Proc. 15th IEEE/ACM Int. Symp. Cluster, Cloud and Grid Computing (CCGrid)*, 2015.

[15] OWASP Foundation, "Log Injection," OWASP Community Pages. [Online]. Available: https://owasp.org/www-community/attacks/Log_Injection

[16] OWASP Foundation, "Logging Cheat Sheet," OWASP Cheat Sheet Series. [Online]. Available: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

[17] MITRE / CISA, "CWE-117: Improper Output Neutralization for Logs," Common Weakness Enumeration. [Online]. Available: https://cwe.mitre.org/data/definitions/117.html

[18] CVE Program, "CVE-2021-44228," MITRE / NVD, 2021. [Online]. Available: https://www.cve.org/CVERecord?id=CVE-2021-44228

[19] R. Aghili, H. Li, and F. Khomh, "Protecting Privacy in Software Logs: What Should Be Anonymized?," *Proceedings of the ACM on Software Engineering*, 2025, arXiv:2409.11313.

[20] S. Bargale, A. Vakati Venkata, J. Singh, and C. Rebeiro, "Privacy-Preserving Anonymization of System and Network Event Logs Using Salt-Based Hashing and Temporal Noise," arXiv:2507.21904, 2025.

[21] "Log Pseudonymization: Privacy Maintenance in Practice," *Journal of Information Security and Applications*, Elsevier. (Full author list not independently re-verified by the authors of this paper due to restricted access; cited for architectural placement only.)

[22] A. Varanda, L. Santos, R. L. d. C. Costa, A. Oliveira, and C. Rabadão, "The General Data Protection Regulation and Log Pseudonymization," in *Advanced Information Networking and Applications (AINA)*, Springer LNNS, 2021, doi: 10.1007/978-3-030-75078-7_48.

[23] D. Lehmann, J. Kinder, and M. Pradel, "Everything Old is New Again: Binary Security of WebAssembly," in *Proc. 29th USENIX Security Symposium*, 2020.

[24] Z. Yu, D. Zhan, L. Ye, H. Yu, H. Zhang, and Z. Tian, "Exploring and Exploiting the Resource Isolation Attack Surface of WebAssembly Containers," in *Proc. 34th USENIX Security Symposium*, 2025, pp. 1111–1128.

[25] Bytecode Alliance, "Wasmtime Security," Wasmtime Documentation. [Online]. Available: https://docs.wasmtime.dev/security.html

[26] G. Rjoub, J. Bentahar, O. A. Wahab, R. Mizouni, A. Song, R. Cohen, H. Otrok, and A. Mourad, "A Survey on Explainable Artificial Intelligence for Cybersecurity," *IEEE Transactions on Network and Service Management*, 2023, arXiv:2303.12942.

[27] "Too Much to Trust? Measuring the Security and Cognitive Impacts of Explainability in AI-Driven SOCs," arXiv:2503.02065, 2025. (Full author list not independently re-verified by the authors of this paper.)

[28] H.-L. Huynh, Q.-C. Tang, V.-T. Phan, and K. Nguyen-An, "Design and Evaluation of a Controlled Post-Alert Incident Orchestration and Response Subsystem Using a Rule Engine and a Local Large Language Model," in *Proc. 19th Conf. on Fundamental and Applied IT Research (FAIR)*, 2026, arXiv:2609.26316. (Preprint, not yet peer-reviewed.)

[29] B. E. Strom, A. Applebaum, D. P. Miller, K. C. Nickels, A. G. Pennington, and C. B. Thomas, "MITRE ATT&CK: Design and Philosophy," MITRE Corporation, 2020.

[30] OWASP Foundation, "OWASP Top 10:2021." [Online]. Available: https://owasp.org/Top10/2021/

---

# List of Figures

- **Figure 1 — High-level ULPF architecture.** Three layers: (i) ingestion/pipeline layer producing NormalizedEvents; (ii) analysis layer (correlation, rule-based detection, risk scoring, alerting) operating downstream over stored events; (iii) extension/assistance layer (parser packs + WASM sandbox, template mining/compression, offline AI explainer, response simulator) attached to the pipeline and to alerts respectively.
- **Figure 2 — End-to-end per-record pipeline.** The fixed eight-stage sequence (security_shield → format_detection → parsing → cleaning → field_extraction → pii_obfuscation → normalization → validation) with explicit QUARANTINED and INVALID exit branches feeding job-level counters.
- **Figure 3 — Universal Event schema.** The ~28-field NormalizedEvent grouped into provenance, core, identity, network, action/outcome, message/extra, and quality/versioning field clusters (Table 2).
- **Figure 4 — Security Shield flow.** Raw line → regex screen → verdict (SAFE / SUSPICIOUS / WEAPONIZED_LOG) → branch into "injection" (pipeline-threatening, e.g. CRLF, Log4Shell-style) vs. "payload" (attack recorded but log itself safe, e.g. SQLi string) → quarantine decision.
- **Figure 5 — Cross-source correlation and risk pipeline.** Multiple heterogeneous sources → pseudonymized entity linking (source_ip/username/host) → chronological timeline assembly → deterministic rule evaluation (RULE_1–RULE_8) → entity-group merging (≥60% event-ID overlap) → named-factor additive risk scoring → alert.
- **Figure 6 — Deployment architecture.** Docker Compose topology (PostgreSQL 16 container, FastAPI backend container, nginx-served React frontend container) alongside the separate Vercel serverless mapping (API routes → backend service, all other routes → frontend service).

# List of Tables

- **Table 1 — Log source characteristics.** The bundled sample sources (Apache/Nginx access logs, Linux auth.log/syslog, firewall iptables/vendor key-value logs, Windows security-event JSON, application JSON/syslog) with format, ingestion adapter used (FILE), and approximate record counts as used in this paper's measurements.
- **Table 2 — Universal Event schema fields.** The ~28 NormalizedEvent fields grouped by category (provenance, core, identity, network, action/outcome, content, quality metadata, provenance/versioning) with type and description.
- **Table 3 — Implemented parser types.** The 8 built-in Python parsers, the declarative YAML parser-pack mechanism (3 shipped packs: CEF, HAProxy, PostgreSQL), and the experimental WASM sandboxed parser path, with kind (built-in/declarative/sandboxed) and status (production path vs. experimental).
- **Table 4 — Detection rules.** RULE_1 through RULE_8 with name, description, default severity, default threshold, and default window, as defined in the bootstrap seed data (Section 10).
- **Table 5 — Experimental results.** The two independently re-executed measurements from Section 18 (compression benchmark; brute-force detection scenario, including the documented risk-score discrepancy) with exact figures.
- **Table 6 — Comparison with existing approaches.** Descriptive (non-ranked) comparison of ULPF against ML-based log parsing/detection literature, common schema efforts (OCSF/ECS/CEF), and general SIEM platforms, across the dimensions of determinism, explainability, and scope.
- **Table 7 — Security threat analysis.** Threat classes addressed (log injection, Log4Shell-style payloads, PII exposure during correlation, untrusted parser code) mapped to the corresponding ULPF mechanism (security shield, HMAC pseudonymization, declarative pack sandboxing, WASM sandbox) and its verification status (unit-tested / independently re-executed / design-inspection-only).

# List of Experiments Actually Performed

1. Compression benchmark re-execution against `sample_logs/application/bulk_access.log` via the real ingestion, template-mining, and compression-benchmark APIs (Section 13, Section 18).
2. Four-source brute-force detection scenario re-execution against `sample_logs/security_scenarios/scenario_brute_force/` via the real ingestion and detection APIs, including retrieval of the resulting alert's full risk breakdown and incident timeline (Section 18).
3. Backend automated test suite (19 files, 173 tests) — existing project baseline, not re-run fresh for this paper but consistent with the project's last verified checkpoint.
4. Source-level (static) inspection and, where present, automated-test confirmation of: the response simulator's absence of subprocess/shell/network imports; the WASM sandbox's linker/fuel/epoch/memory configuration; the declarative parser pack's restriction to regex plus a fixed transform allow-list; the presence and self-reported `NOT_CONFIGURED` status of the four non-functional log-source adapters; and the absence of any "Demo Mode" implementation despite its mention in project documentation.

# List of Claims Requiring Additional Validation Before Publication

1. The exact "risk 93/100" figure — reproduced once, on one machine, against synthetic data; not yet reconciled against the differing "91/100" figure in project documentation.
2. The 6.2% compression reduction figure — measured on one small, single-template dataset; not evaluated across formats, sizes, or repetition.
3. Any implicit generalization from the single brute-force scenario to detection accuracy (precision/recall/F1) on real-world or varied adversarial traffic — no such measurement exists.
4. Any implicit generalization from single-run throughput figures (≈1,680 events/sec compression; 66–232 records/sec ingestion) to production-scale performance or scalability claims.
5. The security shield's actual bypass resistance — verified only against its own unit-test patterns, not against independent adversarial testing.
6. The WASM sandbox's actual resource-exhaustion/escape resistance — verified only by design/configuration inspection, not by red-team testing.
7. The full author lists of two cited sources ([21], [27]) — titles/venues confirmed, but exact authorship should be re-verified against the primary source before final submission.
8. Authorship of citation [21] specifically requires re-confirmation, as the source page could not be directly accessed during this review.

# Suggested Keywords

Log preprocessing; heterogeneous log normalization; universal event schema; security information and event management; log injection prevention; deterministic detection rules; explainable risk scoring; PII pseudonymization; template mining; lossless log compression; WebAssembly sandboxing; offline security AI.

# Suggested IEEE-Style Title Alternatives

1. "ULPF: A Deterministic Pipeline for Heterogeneous Security Log Normalization, Pseudonymization, and Correlation"
2. "Toward Auditable Log Pre-processing: Combining Injection Screening, Deterministic Parsing, and Explainable Risk Scoring"
3. "Universal Log Pre-processing Framework: Design and Evaluation of a Rule-Based, Privacy-Preserving Security Log Pipeline"
4. "An Integrated, Deterministic Approach to Heterogeneous Log Normalization and Cross-Source Threat Correlation"
5. "From Raw Logs to Explainable Alerts: A Deterministic Pre-processing and Correlation Pipeline for Security Operations"
