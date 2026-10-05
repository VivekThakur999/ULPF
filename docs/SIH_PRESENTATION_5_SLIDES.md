# Universal Log Pre-processing Framework (ULPF)
## Official 5-Slide Presentation Deck Structure
**Smart India Hackathon 2026** | **Problem ID:** SIH26156 | **Organization:** NTRO

---

### Slide 1: Problem Statement & National Security Context
**Title**: The Perimeter Ingestion Dilemma — Heterogeneity, Weaponization & Privacy

- **Problem Context**: Critical infrastructure and national cyber defense networks process terabytes of log data daily from hundreds of perimeter appliances, cloud services, and legacy endpoints.
- **Pain Points**:
  - **Unformatted & Heterogeneous**: Every vendor (Cisco, CheckPoint, Linux, Apache, W3C, JSON) outputs distinct, incompatible log formats.
  - **Weaponized Telemetry**: Attackers inject terminal escape sequences (`\x1b`), CRLF, and log forging payloads to corrupt SIEM parsers and evade attribution.
  - **PII Leakage & Compliance Violations**: Sensitive internal IPs, usernames, and credentials leak unmasked into downstream analytics.
  - **Loss of Forensic Chain of Custody**: Current normalization tools mutate or drop raw strings, rendering evidence inadmissible during incident investigation.

---

### Slide 2: The ULPF Solution & Dual-Plane Architecture
**Title**: Universal Log Pre-Processing Framework (ULPF)

- **Core Vision**: A vendor-agnostic, dual-plane pre-processing engine providing lossless ingestion, AST-hardened security filtering, deterministic PII protection, and universal normalization.
- **Target Architecture**:
  - **Telemetry Data Plane (MongoDB 8.0)**: High-throughput ingestion of `raw_logs`, `normalized_events`, `security_alerts`, and `template_matches` (**24,027+ writes/sec**).
  - **Control Plane & Identity (PostgreSQL 16 / Supabase)**: Strict RBAC (Admin, Analyst, Viewer), policy enforcement, parser packs, and immutable audit trails.
  - **Dual Deployment Options**:
    - *Connected Cloud*: Supabase Auth + MongoDB 8.0 Cloud.
    - *Sovereign Air-Gapped*: 100% Offline with local Argon2id auth, local PostgreSQL, local MongoDB, and offline local AI.

---

### Slide 3: Technical Innovations & Core Differentiators
**Title**: Engineering Breakthroughs in Pre-Processing

1. **AST-Isolated Security Shield**: Zero dynamic code execution (`no eval`, `no exec`). Automatically sanitizes escape sequences and flags log injection attacks prior to parsing.
2. **Deterministic Privacy-Preserving Pseudonymization**: Keyed HMAC-SHA256 tokenization allows cross-source correlation of anonymized entities (`IP_9f82...`) without exposing raw network secrets.
3. **Lossless Forensic Traceability Chain**: Every normalized event, security alert, and incident maintains an immutable pointer (`raw_log_id` + SHA-256 hash) to the exact raw bytes.
4. **Deterministic Template Mining & Micro-Compression**: Discovers recurring patterns across heterogeneous streams with **100% byte-exact reconstruction** at **31,400+ logs/sec**.
5. **Plug-and-Play Extensibility**: Declarative YAML parser packs and sandboxed WebAssembly (WASM) modules allow new vendor support in minutes without backend recompilation.

---

### Slide 4: Live Workflow Demonstration & SIEM Interoperability
**Title**: From Raw Logs to Actionable Forensics & SIEM Exports

- **Ingestion & Validation**: Upload raw firewall or authentication logs $\rightarrow$ Automatic format detection $\rightarrow$ Security classification $\rightarrow$ Universal normalization.
- **SOC Investigation Console**:
  - *Command Center*: Live telemetry KPIs, source distribution, and threat breakdowns.
  - *Log Explorer*: Sub-30ms facet search across unified schemas with deep forensic links.
  - *Alerts & Incidents*: Multi-event correlation detecting brute force, privilege escalation, and network sweeps.
  - *Response Simulator*: Safe, non-destructive simulation of firewall blocks and host isolations with zero real-system mutation.
- **Enterprise SIEM / ML Exports**:
  - Elastic Common Schema (ECS 1.12.0) NDJSON export for Splunk/Elastic.
  - 14-dimensional feature vector export for downstream anomaly detection & ML pipelines.

---

### Slide 5: Impact, Scalability & Roadmap
**Title**: Scalability, SIH Compliance & Future Scope

- **Benchmarked Performance**:
  - **24,027.9 events/sec** bulk write throughput on MongoDB 8.0.
  - **27.5 ms P50 query latency** for real-time threat investigation.
  - **100% test suite pass rate** (197/197 backend tests, 27/27 frontend tests, 13/13 staging E2E stages passed).
- **Compliance Matrix**: Full compliance with all 15 NTRO SIH26156 requirements.
- **Future Extension Path**:
  - Horizontal distributed ingestion via Kafka / Apache Pulsar stream connectors.
  - Sharded MongoDB replica sets for multi-terabyte national SOC deployments.
  - Hardware-accelerated (eBPF) live packet stream capture integration.
