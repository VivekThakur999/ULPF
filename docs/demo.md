# ULPF — SIH Demo Guide

> All datasets used here are **synthetic / demo data** (see `sample_logs/`).

## Demo Mode

`Settings → Demo Mode → Load demo data` (or `POST /api/demo/load`) seeds sources,
sample logs, runs ingestion, and produces the brute-force alert. Idempotent.

## Live walkthrough (≈6 min)

1. **Login** as `admin@ulpf.io`.
2. **Dashboard** — real tiles: total logs, processed, invalid, duplicates,
   quarantined, alerts, processing rate.
3. **Log Sources** — Linux, Firewall, Application, Apache/Nginx (status = CONFIGURED;
   we never fake a live enterprise link).
4. **Ingestion** — upload / import a sample; watch the job progress with real counts.
5. **Format detection** — show `{format, confidence}` per file.
6. **Pipeline** — open the processing detail: shield → detect → parse → clean → PII →
   normalize → validate.
7. **PII protection** — `192.168.1.50 → IP_7F82A1`, `admin@corp.example → EMAIL_…`.
8. **Universal schema** — one event shape across all sources.
9. **Search** the pseudonymized IP `IP_7F82A1` in the Log Explorer.
10. **Cross-source** — the same pseudonym appears in Linux + firewall + application events.
11. **Correlation** — timeline of the correlated activity.
12–13. **Suspicious activity + risk** — RULE_1/RULE_3/RULE_5/RULE_6 fire → one
    consolidated alert, **risk in the HIGH/CRITICAL band** with a fully itemised
    breakdown (every point attributable to a named factor).
14. **Alert** — open "Possible brute-force attack".
15. **Incident timeline** — 18:20:10 → 18:20:20 sequence.
16. **Pipeline Debugger** — paste
    `Failed password for admin from 192.168.1.50 port 443` and show the highlighted
    matches (`admin → username`, `192.168.1.50 → source_ip`, `443 → source_port`,
    `event → authentication_failure`).
17. **Explain this log** — local AI plain-language explanation (clearly marked AI, not
    authoritative).
18. **Response Simulator** — recommendation "Block source IP" → *Simulate Response* →
    "Response sent to simulated firewall. Status: SUCCESS" (labelled SIMULATION).

## Critical scenario — brute force from `192.168.1.50`

`sample_logs/security_scenarios/scenario_brute_force/` contains time-aligned
Linux, firewall, application and Windows logs. Import all four, then Alerts →
Run detection. ULPF then shows:

1. the same pseudonymized IP (`IP_3D3563`) across all four sources
   (Log Explorer → search `192.168.1.50`, note the auto-pseudonymization);
2. every event in one Universal schema;
3. one consolidated alert "Successful login after repeated failures";
4. the incident timeline (firewall drops → Linux failures → app lockout →
   Windows 4625/4740 → success);
5. exactly which rules triggered (RULE_1/3/5/6) and why (`reason`);
6. the itemised risk breakdown (failed-auth volume, cross-source correlation,
   multiple hosts, time concentration, success-after-failures, …);
7. the recommended response ("Block source IP …") — recommendation only.
