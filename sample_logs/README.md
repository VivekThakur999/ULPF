# Sample logs — SYNTHETIC / DEMO DATA

Every file in this tree is **synthetic data generated for testing and
demonstration**. No real hosts, users, IP addresses or events are represented.
IP addresses use RFC 1918 / documentation ranges; usernames and domains are made
up (`corp.example`, `admin`, `jdoe`, …).

| Folder | Contents |
|--------|----------|
| `linux/` | auth.log / secure style sshd, sudo, pam events |
| `syslog/` (under `application/`) | generic RFC 3164 syslog |
| `apache/` | Apache combined access logs |
| `nginx/` | Nginx extended access logs (XFF + timing) |
| `firewall/` | iptables kernel logs + vendor key=value firewall logs |
| `application/` | JSON / NDJSON application logs |
| `windows/` | Windows-like event logs (JSON export shape) |
| `malformed/` | broken lines, bad timestamps/IPs, encoding issues, duplicates |
| `security_scenarios/` | multi-source attack scenarios (see each subfolder's README) |
