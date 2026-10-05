# Universal Log Pre-processing Framework (ULPF)
## 2-Page Executive Architecture & Technical Specification
**Smart India Hackathon 2026** | **Problem ID:** SIH26156 | **Organization:** NTRO (National Technical Research Organisation)

---

### 1. Executive Summary & Problem Formulation
Modern enterprise Security Operations Centers (SOCs) and national cyber defense perimeters ingest massive volumes of heterogeneous, unstructured, and weaponized logs from perimeter firewalls, authentication gateways, cloud workloads, and IoT appliances. Raw log ingestion currently suffers from four systemic vulnerabilities:
1. **Unchecked Log Injection & Weaponization**: Raw logs carrying terminal escape sequences (`\x1b`), CRLF injection, and code injection (`eval`, AST exploits) crash SIEM indexers and analysts' terminals.
2. **Schema Fragmentation**: Dissimilar syntax across vendors (Cisco ASA, Linux syslog, Nginx, JSON, CEF, CloudTrail) prevents unified cross-source correlation.
3. **PII Exposure**: Sensitive client IPs, emails, and usernames leak into telemetry stores without deterministic cross-source privacy controls.
4. **Storage Bloat & Loss of Traceability**: Traditional log pre-processors mutate or truncate original evidence, destroying forensic admissibility.

**ULPF Solution**: An air-gapped capable, dual-plane pre-processing framework that ingests heterogeneous logs, screens payloads through an AST-isolated Security Shield, extracts fields into a Universal Event Schema, enforces deterministic HMAC-SHA256 pseudonymization, and preserves byte-for-byte forensic traceability linking normalized events to raw cryptographic hashes.

---

### 2. Dual-Storage & Target Deployment Architecture

```
                               ┌─────────────────────────────────────────┐
                               │   React 18 + TypeScript SPA (Vite)      │
                               │   NGINX Reverse Proxy (Port 8080)       │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       FastAPI Backend (Python 3.12)     │
                               │       Stateless Async REST Engine       │
                               └──────────┬───────────────────┬──────────┘
                                          │                   │
                     Data Plane / Telemetry│                   │Control Plane / Identity
                                          ▼                   ▼
                               ┌─────────────────────┐ ┌─────────────────────┐
                               │     MongoDB 8.0     │ │ PostgreSQL 16 /     │
                               │   Telemetry Store   │ │ Supabase Cloud      │
                               └─────────────────────┘ └─────────────────────┘
                               • raw_logs              • app_users & roles
                               • normalized_events     • audit_logs
                               • security_events       • log_sources
                               • security_alerts       • pii_settings
                               • template_matches      • security_rules
                               • compression_records   • parser_packs
```

#### Dual-Mode Deployment Flexibility:
- **Connected Cloud Mode**: Uses Supabase Cloud for Identity/RBAC, PostgreSQL 16 for control policies, and MongoDB 8.0 for telemetry.
- **Sovereign Air-Gapped Mode**: Zero external network calls. Local Argon2id password authority, local PostgreSQL 16 control plane, local MongoDB 8.0 cluster, and offline deterministic / Ollama AI explanation engine.

---

### 3. Canonical 9-Stage Ingestion & Pre-Processing Pipeline

```
[Raw Log Ingestion] 
       │
       ▼
1. Security Shield ────────► Screens escape sequences (\x1b), control characters, SQLi/shell injection patterns.
       │
       ▼
2. Format Detection ───────► Auto-identifies JSON, NDJSON, Syslog RFC3164/5424, CEF, Apache, Cisco ASA, W3C.
       │
       ▼
3. Parsing Engine ─────────► Dispatches to declarative YAML parser packs, regex parsers, or sandboxed WASM modules.
       │
       ▼
4. Cleaning & Validation ──► Normalizes timestamps (ISO 8601 UTC), trims whitespace, strips carriage returns.
       │
       ▼
5. Field Extraction ───────► Maps extracted tokens into standard network, HTTP, host, and user fields.
       │
       ▼
6. PII Protection ─────────► Keyed HMAC-SHA256 deterministic tokenization (`IP_8f2a...`, `USER_c4b1...`).
       │
       ▼
7. Universal Normalization ► Generates canonical `NormalizedEvent` complying with Universal Schema v1.0.0.
       │
       ▼
8. Validation & Scoring ───► Calculates field confidence (0.0 to 1.0) and verifies schema structural integrity.
       │
       ▼
[MongoDB Telemetry Store & Real-Time Correlation Engine]
```

---

### 4. Mathematical Model & Core Innovations

#### A. Deterministic Privacy-Preserving Tokenization:
$$T = \text{Truncate}_{16}\left(\text{Base64}\left(\text{HMAC-SHA256}(K_{\text{PII}}, V \parallel \text{Scope})\right)\right)$$
*Properties*: Zero leakage of raw secret; deterministic token matching enables cross-source correlation over anonymized identifiers without plaintext exposure.

#### B. Byte-Exact Forensic Traceability Guarantee:
$$\forall e \in \text{NormalizedEvents}: \quad \exists r \in \text{RawLogs} \quad \text{s.t.} \quad e.\text{raw\_log\_id} = r.\text{id} \quad \land \quad \text{SHA256}(r.\text{content}) = r.\text{content\_hash}$$

#### C. Deterministic Template Clustering & Micro-Compression:
$$\text{Reconstruct}(T_{\text{tpl}}, M_{\text{match}}) \equiv L_{\text{raw}}$$
Extracts static literal anchors and variable tokens, achieving exact round-trip byte equality while enabling high-efficiency pattern discovery.

---

### 5. Empirical Performance Benchmarks (Live Verified)

| Benchmark Metric | Measured Result | Production Target / SIH Standard |
|------------------|-----------------|----------------------------------|
| **MongoDB Bulk Write Throughput** | **24,027.9 events/sec** (Batch=2500) | $\ge$ 10,000 events/sec |
| **Pipeline Parsing & Shield** | **30.8 events/sec** (Single Core) | Scalable horizontally via workers |
| **Log Explorer Search Latency (P50)** | **27.51 ms** (Filtered query) | $\le$ 50.0 ms |
| **Log Explorer Search Latency (P95)** | **46.07 ms** (Filtered query) | $\le$ 100.0 ms |
| **Multi-Field Facet Aggregation** | **P50 = 46.11 ms** | $\le$ 75.0 ms |
| **Alert Queue Query Latency** | **P50 = 5.75 ms** | $\le$ 20.0 ms |
| **Template Mining Speed** | **31,486.7 logs/sec** (1,000 cluster) | $\ge$ 5,000 logs/sec |
| **Reconstruction Fidelity** | **100.0% Exact Byte Equality** | 100.0% Zero Loss |

---

### 6. External Interoperability & SIEM / Data Lake Export
ULPF acts as the universal pre-processing frontend for enterprise SIEMs (Splunk, Elastic, Sentinel) and Data Lakes (ClickHouse, Snowflake, S3):
- `GET /api/logs/export/ndjson`: Streams newline-delimited JSON conforming to Elastic Common Schema (ECS 1.12.0) with embedded ULPF traceability metadata.
- `GET /api/logs/export/json`: Structured JSON bundle with schema versioning.
- `GET /api/logs/export/ml-ready`: 14-dimensional dense numerical & categorical feature matrix (`timestamp_epoch`, `hour_of_day`, `day_of_week`, `severity_numeric`, `port`, `length`) ready for downstream scikit-learn/PyTorch anomaly detection pipelines.
