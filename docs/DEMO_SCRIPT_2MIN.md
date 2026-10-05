# Universal Log Pre-processing Framework (ULPF)
## 2-Minute Live Demonstration Walkthrough Script
**Smart India Hackathon 2026** | **Problem ID:** SIH26156 | **Organization:** NTRO

---

### Timing & Stage Breakdown

```
[00:00 - 00:20]   Step 1: Role Authentication & Command Center
[00:20 - 00:45]   Step 2: Heterogeneous Log Ingestion & Visual Pipeline Flow
[00:45 - 01:10]   Step 3: Log Explorer & Forensic Raw Traceability
[01:10 - 01:35]   Step 4: Correlation, Security Alerts & Offline AI Assistant
[01:35 - 01:50]   Step 5: Safe Response Simulator
[01:50 - 02:00]   Step 6: SIEM / ML-Ready Export & Conclusion
```

---

### Step-by-Step Script

#### Step 1: Login & Command Center (00:00 – 00:20)
- **Action**: Open `http://localhost:8080`. Log in as `admin@ulpf.io`.
- **Narrator**:
  > "Welcome to ULPF — the Universal Log Pre-processing Framework engineered for NTRO. Here in the Command Center, we observe real-time telemetry backed by our dual-storage architecture: MongoDB 8.0 for high-volume telemetry, and PostgreSQL 16 / Supabase for control plane security. Notice our operational status is completely live with zero mock data."

#### Step 2: Log Ingestion & Visual Pipeline Flow (00:20 – 00:45)
- **Action**: Navigate to **Ingestion** (`/ingestion`). Upload or select sample heterogeneous logs (e.g. Cisco ASA firewall + Linux SSH auth logs). Click **Process**.
- **Narrator**:
  > "We feed raw, unformatted perimeter logs into ULPF. In milliseconds, our AST-isolated Security Shield screens the payload for escape sequences and injection attacks. Format detection automatically identifies the Cisco ASA and Linux Auth formats, extracts normalized fields, and applies deterministic HMAC-SHA256 pseudonymization to protect client IPs and usernames."

#### Step 3: Log Explorer & Lossless Forensic Traceability (00:45 – 01:10)
- **Action**: Click **Log Explorer** (`/explorer`). Filter by `severity=ERROR` or `source=linux_auth`. Click an event row to open the Investigation Console. Show the **Raw Log** tab and SHA-256 hash.
- **Narrator**:
  > "In the Log Explorer, our sub-30 millisecond query engine renders the canonical universal event schema. When investigating a security incident, an analyst can inspect the full 9-stage pipeline transformation and instantly view the original, byte-for-byte raw log and its SHA-256 hash, maintaining strict forensic admissibility."

#### Step 4: Correlation, Security Alerts & Offline AI Assistant (01:10 – 01:35)
- **Action**: Navigate to **Alerts** (`/alerts`). Click on a brute-force or authentication anomaly alert. Show the cross-source correlation chain and click **AI Assistant** (`/assistant`) to request an explanation.
- **Narrator**:
  > "ULPF correlates events across disparate sources—linking Linux SSH failures with firewall drops. Our transparent risk scoring engine shows exactly why an alert fired. Furthermore, our offline AI assistant explains the attack vector locally without sending a single byte to the public cloud, ensuring total sovereignty in air-gapped defense networks."

#### Step 5: Safe Response Simulator (01:35 – 01:50)
- **Action**: Navigate to **Response Simulator** (`/simulator`). Select the active alert and trigger a simulated perimeter IP block.
- **Narrator**:
  > "In the Response Simulator, analysts evaluate containment actions—such as firewall blocks or host isolation. Notice the strict 'SIMULATION ONLY' guardrails: ULPF models the security outcome safely without modifying live network infrastructure."

#### Step 6: SIEM / ML-Ready Export & Closing (01:50 – 02:00)
- **Action**: Navigate to Log Explorer, click **Export** (or trigger `/api/logs/export/ndjson` and `/api/logs/export/ml-ready`).
- **Narrator**:
  > "Finally, ULPF streams normalized events to external SIEMs in Elastic Common Schema (ECS 1.12) NDJSON, and outputs 14-dimensional feature vectors directly to machine learning pipelines. Tested at over 24,000 writes/sec, ULPF delivers true universal, secure, and forensic log pre-processing. Thank you."
