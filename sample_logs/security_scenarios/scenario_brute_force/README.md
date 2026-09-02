# Scenario: SSH brute-force from 192.168.1.50  (SYNTHETIC)

Attacker source IP: **192.168.1.50** — targets host **db-02 / 10.20.0.20**.

Timeline (all 2025-09-02):
- 09:01:50–09:02:14 firewall drops repeated SYNs to port 22 from 192.168.1.50
- 09:02:11–09:02:20 Linux `db-02` logs 4 failed SSH passwords + a PAM auth failure for `admin`
- 09:02:12–09:02:19 application `auth-svc` logs 2 `login_failed` then `account_locked` for `admin`
- 09:01:59–09:02:22 Windows `WIN-DC01` logs EventID 4625 x2 then 4740 (lockout) for `Administrator`

Expected ULPF behaviour after ingesting all four files:
- the same pseudonymized IP appears across firewall + linux + application + windows events
- RULE_1 (multiple failed logins from same source) and RULE_3 (multi-host) fire
- risk score in the HIGH band with a transparent breakdown
- one correlated alert "Possible brute-force activity" with an incident timeline

Files: `linux.log`, `firewall.log`, `application.jsonl`, `windows.jsonl`.
