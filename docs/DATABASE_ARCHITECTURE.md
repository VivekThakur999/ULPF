# ULPF Database Architecture Specification

## 1. Dual Storage Plane Philosophy

The Universal Log Pre-processing Framework (ULPF) implements a strict architectural separation of concerns between high-volume, semi-structured event telemetry and relational transactional metadata:

```
                                  ULPF Application
                                         |
                                  FastAPI Backend
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
         MongoDB 8.0 Telemetry Store             PostgreSQL 16 / Supabase Control
           (Database: ulpf_telemetry)                    (Database: ulpf)
                     |                                       |
     - raw_logs                              - app_users
     - normalized_events                     - api_keys
     - processing_jobs                       - log_sources
     - security_alerts                       - pii_settings
     - security_events                       - security_rules
     - templates                             - parser_packs
     - template_matches                      - parser_versions
     - compression_records                   - audit_logs
     - pipeline_runs                         - response_simulations
     - response_simulations (mirror)
```

---

## 2. Telemetry Plane: MongoDB 8.0 (`ulpf_telemetry`)

MongoDB 8.0 is the authoritative forensic storage engine for all log streams, ECS-normalized events, cluster templates, and incident records.

### Collections & Schema Definitions

#### 1. `raw_logs`
Stores immutable original log strings and content hashes.
- `_id` (`string`): Primary UUID key (`raw_log_id`).
- `job_id` (`string`): Associated ingestion job UUID.
- `source_name` (`string`): Identifier of the originating log source.
- `line_number` (`int`): Sequential line index in the source batch.
- `content` (`string`): Unaltered raw log string.
- `content_hash` (`string`): SHA-256 hex digest of `content`.
- `status` (`string`): Status (`PROCESSED`, `QUARANTINED`, `INVALID`).
- `received_at` (`datetime`): UTC ingestion timestamp.
- **Indexes**:
  - `(job_id, line_number)`
  - `(job_id, status)`
  - `content_hash`
  - `received_at DESC`

#### 2. `normalized_events`
Stores standardized ECS v1.0 event documents.
- `_id` (`string`): Primary event UUID.
- `raw_log_id` (`string`): Reference to corresponding `raw_logs._id`.
- `job_id` (`string`): Reference to `processing_jobs._id`.
- `schema_version` (`string`): Schema version (`"1.0"`).
- `timestamp` (`datetime`): Event occurrence time (UTC ISO 8601).
- `ingested_at` (`datetime`): System ingestion time (UTC).
- `source` (`string`): Log source category (`firewall`, `linux`, `windows`, etc.).
- `event_type` (`string`): Normalized event action (`authentication_failure`, `connection_denied`, etc.).
- `severity` (`string`): Normalized severity (`info`, `low`, `medium`, `high`, `critical`).
- `action` (`string`): Action verdict (`allow`, `deny`, `drop`, `login`, `logout`).
- `status` (`string`): Operation outcome (`success`, `failure`, `error`).
- `source_ip` (`string`): Pseudonymized source IP token (`IP_...`).
- `destination_ip` (`string`): Pseudonymized destination IP token (`IP_...`).
- `source_port` (`int`): Source port number.
- `destination_port` (`int`): Destination port number.
- `protocol` (`string`): Transport protocol (`TCP`, `UDP`, `ICMP`).
- `username` (`string`): Pseudonymized user token (`USER_...`).
- `host` (`string`): Pseudonymized machine hostname token (`HOST_...`).
- `process` (`string`): Originating process or daemon name.
- `message` (`string`): Sanitized human-readable log message.
- `raw_log` (`string`): Mirror of raw log content.
- `attributes` (`object`): Arbitrary source-specific structured attributes.
- `security_shield` (`object`): Shield scan verdict and threat types.
- **Indexes**:
  - `timestamp DESC`
  - `(source_ip, timestamp DESC)`
  - `(destination_ip, timestamp DESC)`
  - `(username, timestamp DESC)`
  - `(host, timestamp DESC)`
  - `(event_type, timestamp DESC)`
  - `(severity, timestamp DESC)`
  - `(source, timestamp DESC)`
  - `job_id`
  - `raw_log_id`
  - `processing_status`
  - `template_id`

#### 3. `processing_jobs`
Tracks streaming upload batches and parsing throughput.
- `_id` (`string`): Ingestion job UUID.
- `source_name` (`string`): Source name label.
- `status` (`string`): `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.
- `total_records` (`int`), `processed_records` (`int`), `invalid_records` (`int`), `quarantined_records` (`int`).
- `records_per_second` (`float`), `duration_seconds` (`float`).
- `created_at` (`datetime`), `completed_at` (`datetime`).
- **Indexes**:
  - `status`
  - `created_at DESC`
  - `source_name`

#### 4. `security_alerts`
Stores deduplicated security incident records.
- `_id` (`string`): Alert UUID.
- `dedup_key` (`string`): Unique entity key (e.g. `source_ip=IP_4442D87E`).
- `title` (`string`), `severity` (`string`), `risk_score` (`float`).
- `source` (`string`), `rule_key` (`string`), `description` (`string`), `reason` (`string`).
- `risk_breakdown` (`object`): Transparent factor contributions.
- `entity` (`object`): Focus entity details and time center.
- `related_event_ids` (`array[string]`): Normalized event IDs.
- `affected_hosts` (`array[string]`): Hostnames affected.
- `recommended_response` (`object`): Advisory simulated mitigation plan.
- `status` (`string`): `NEW`, `INVESTIGATING`, `RESOLVED`, `DISMISSED`.
- `ts` (`datetime`), `updated_at` (`datetime`).
- **Indexes**:
  - `dedup_key` (Unique)
  - `(status, ts DESC)`
  - `(severity, risk_score DESC)`
  - `(rule_key, ts DESC)`

#### 5. `templates` & `template_matches`
Stores extracted Drain structural log templates and variable slot matches.
- `templates._id` (`string`): Template UUID or integer ID.
- `token_signature` (`string`, Unique): Structural token signature.
- `template_key` (`string`, Unique): Key identifier (`TPL-XXXX`).
- `pattern` (`string`): Normalized pattern string (`User <*> logged in from <*>`).
- `token_count` (`int`), `literal_tokens` (`array`), `variable_types` (`array`), `separators` (`array`), `trailing` (`string`), `occurrences` (`int`).
- `template_matches._id` (`string`): Match UUID.
- `template_matches.raw_log_id` (`string`, Unique): Reference to `raw_logs._id`.
- `template_matches.template_id` (`string`): Reference to `templates._id`.
- `template_matches.variables` (`array`): Extracted dynamic variable values.
- **Indexes**:
  - `templates`: `token_signature` (Unique), `template_key` (Unique), `occurrences DESC`, `first_seen DESC`.
  - `template_matches`: `raw_log_id` (Unique), `(template_id, ts DESC)`.

---

## 3. Control Plane: PostgreSQL 16 / Supabase (`ulpf`)

The PostgreSQL relational store maintains administrative state, security rules, audit trails, and user identities.

### Entity Relationship Mapping

```
+-------------------+       1:N       +------------------------+
|     app_users     | --------------> |       audit_logs       |
+-------------------+                 +------------------------+
         |
         | 1:N
         v
+-------------------+
|     api_keys      |
+-------------------+

+-------------------+       1:N       +------------------------+
|   parser_packs    | --------------> |    parser_versions     |
+-------------------+                 +------------------------+

+-------------------+
|  security_rules   |
+-------------------+

+-------------------+
|   pii_settings    |
+-------------------+

+------------------------+
|  response_simulations  |  (alert_id decoupled from FK)
+------------------------+
```

---

## 4. Forensic Traceability Flow

```
[Raw Log Ingestion]
       |
       v
raw_logs (_id: R1, content: "Failed password for admin...")
       |
       +------------------------------------+
       |                                    |
       v                                    v
normalized_events                     security_events
- _id: E1                             - _id: S1
- raw_log_id: R1                      - raw_reference: R1
- source_ip: IP_A                     - verdict: SUSPICIOUS
       |
       v
security_alerts
- _id: A1
- related_event_ids: [E1]
- entity: {source_ip: IP_A}
       |
       v
response_simulations
- _id: SIM1
- alert_id: A1
- simulation_only: True
```
