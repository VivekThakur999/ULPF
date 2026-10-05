# ULPF Security Architecture & Threat Defense Model

## 1. Security Overview

The Universal Log Pre-processing Framework (ULPF) operates under a strict **Zero-Trust & Defense-in-Depth** security philosophy. Because log processing engines are prime targets for log-injection exploits (Log4Shell, SQLi in SIEM databases, XSS in log viewers, and command injection), ULPF enforces structural security controls at every pipeline boundary.

---

## 2. Core Security Pillars

```
+-------------------------------------------------------------------------------+
|                             ULPF SECURITY MODEL                               |
+-------------------------------------------------------------------------------+
| 1. SECURITY SHIELD          | Zero-Execution Static Log Sanitization          |
| 2. PII PROTECTION           | Irreversible HMAC-SHA256 Tokenization           |
| 3. AUTHENTICATION & RBAC    | Dual-Mode JWT + Argon2id + Strict Role Scopes   |
| 4. SERVICE-ROLE ISOLATION   | Backend-Only Secrets (Zero Frontend Leaks)      |
| 5. PARSER SANDBOXING        | Declarative YAML & WebAssembly Isolation        |
| 6. RESPONSE SIMULATION      | Mathematical Representation (No OS Execution)   |
| 7. TAMPER-EVIDENT AUDIT     | Immutable Append-Only Action Logs               |
+-------------------------------------------------------------------------------+
```

---

## 3. Security Shield (Pre-Parsing Threat Neutralization)

The Security Shield (`backend/app/services/security/shield.py`) executes **before** dynamic parsing or field extraction.

### Threat Detection Signatures
1. **JNDI / Log4Shell**: `${jndi:ldap://...}`, `${jndi:rmi://...}`, `${jndi:dns://...}`
2. **SQL Injection**: `' OR '1'='1`, `UNION SELECT`, `DROP TABLE`, `xp_cmdshell`
3. **Cross-Site Scripting (XSS)**: `<script>`, `javascript:`, `<img src=x onerror=...>`
4. **Command Injection**: `; rm -rf`, `| nc `, `&& wget`, `$(whoami)`
5. **Path Traversal**: `../../../../etc/passwd`, `..\..\..\windows\system32`

### Non-Execution Guarantee
The Security Shield operates purely through compiled static regular expressions. It never invokes subshells, `eval()`, `exec()`, or external interpreters. Weaponized logs are safely quarantined and flagged in `security_events` with forensic references preserved.

---

## 4. PII Protection & Cryptographic Pseudonymization

To eliminate plaintext personal identities from telemetry storage while preserving cross-source correlation capabilities, ULPF uses keyed `HMAC-SHA256` tokenization (`backend/app/services/privacy/pseudonymizer.py`).

### Key Properties
- **Cryptographic Irreversibility**: A pseudonym token cannot be decrypted to retrieve the original IP address or username without knowing `PII_HMAC_KEY`.
- **Deterministic Multi-Source Linkability**: The same IP address (e.g. `192.168.1.50`) evaluated across firewall logs, Linux auth logs, and Windows Active Directory logs always generates the exact same token (`IP_4442D87E`).
- **Pre-fixed Taxonomy**:
  - IP addresses $\rightarrow$ `IP_<HEX8>`
  - Usernames $\rightarrow$ `USER_<HEX8>`
  - Hostnames $\rightarrow$ `HOST_<HEX8>`
- **Preserved Formats**: Non-sensitive values and ports remain in native representations for analytical aggregation.

---

## 5. Authentication & Access Control (RBAC)

### Role Hierarchy & Permissions

| Permission | ADMIN | ANALYST | VIEWER |
| :--- | :---: | :---: | :---: |
| View Dashboard & Log Explorer | Yes | Yes | Yes |
| View Security Alerts & Incidents | Yes | Yes | Yes |
| Ingest New Logs / Create Ingestion Jobs | Yes | Yes | No |
| Triage & Update Alert Status (`INVESTIGATING`, `RESOLVED`) | Yes | Yes | No |
| Run Offline AI Explainer | Yes | Yes | No |
| Run Response Mitigation Simulations | Yes | Yes | No |
| Mine Templates & Run Compression Benchmarks | Yes | Yes | No |
| Create / Edit Declarative Parser Packs | Yes | No | No |
| Update Detection Rule Thresholds & Windows | Yes | No | No |
| Manage Users & Inspect Administrative Audit Logs | Yes | No | No |

---

## 6. Service-Role Key & Secret Isolation

- `SUPABASE_SERVICE_ROLE_KEY` is strictly confined to the FastAPI backend environment.
- The React / Vite frontend bundle only ever receives the user's ephemeral JWT access token.
- Verified via AST and grep scans: zero references to service-role keys or private HMAC secrets exist in the `frontend/` directory or compiled production bundles.

---

## 7. Safe Response Simulation Boundary

The Response Simulator (`backend/app/services/response/`) provides hypothetical mitigation modeling for SOC analysts.

### Strict Safety Invariants
1. Every simulated action explicitly carries `mode: "SIMULATION_ONLY"`.
2. Static AST tests (`backend/tests/test_security_no_exec.py`) verify that **zero execution primitives** (`subprocess`, `os.system`, `Popen`, `powershell`, `iptables`, `nft`, `netsh`, `winreg`, `ctypes`) exist in response modules.
3. Simulations are idempotent and produce immutable audit log entries without modifying network devices or host states.

---

## 8. Audit Logging & Forensic Accountability

Every security-sensitive action is recorded in PostgreSQL `audit_logs` and MongoDB `processing_jobs`:
- Authentication successes and failures.
- Ingestion job uploads and quarantine events.
- Detection rule execution and alert status updates.
- Response simulation executions.
- Administrative user creation and permission changes.
