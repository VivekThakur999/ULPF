# Universal Log Event Schema

`schema_version: 1.0`

Every parser — built-in, parser pack, or WASM — MUST emit this shape. All analytical
fields are **nullable**; not every log carries every field.

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | assigned on store |
| `timestamp` | datetime \| null | event time (parsed from the log), UTC |
| `ingested_at` | datetime | when ULPF received it |
| `source` | string | logical source name (e.g. `linux-auth`, `edge-firewall`) |
| `host` | string \| null | hostname/device the event is about |
| `event_type` | string \| null | canonical, e.g. `authentication_failure`, `http_request` |
| `severity` | enum \| null | `info \| low \| medium \| high \| critical` |
| `username` | string \| null | may be pseudonymized (`USER_1A2B3C`) |
| `email` | string \| null | may be pseudonymized (`EMAIL_A8F31C`) |
| `source_ip` | string \| null | may be pseudonymized (`IP_7F82A1`) |
| `destination_ip` | string \| null | " |
| `source_port` | int \| null | |
| `destination_port` | int \| null | |
| `protocol` | string \| null | `tcp \| udp \| icmp \| ...` |
| `action` | string \| null | `allow \| deny \| login \| logout \| ...` |
| `status` | string \| null | `success \| failure \| ...` |
| `process` | string \| null | e.g. `sshd` |
| `service` | string \| null | e.g. `ssh`, `http` |
| `url` | string \| null | request target |
| `http_method` | string \| null | |
| `response_code` | int \| null | |
| `message` | string | human-readable summary / leftover text |
| `extra` | object | parsed fields with no dedicated column |
| `field_confidence` | object | `{field: 0.0–1.0}` extraction confidence |
| `raw_log` | string | verbatim original line |
| `parser` / `parser_version` | string | provenance |
| `pii_protected` | bool | `pii_mode` in `{OFF, MASK, DETERMINISTIC_HASH}` |
| `processing_status` | enum | `ok \| partial \| error` |
| `confidence` | float | overall parse confidence 0–1 |
| `template_id` | string \| null | e.g. `TPL-0045` (template mining) |

## Canonical `event_type` vocabulary (initial)

`authentication_success`, `authentication_failure`, `session_opened`, `session_closed`,
`http_request`, `connection_allowed`, `connection_denied`, `process_start`,
`config_change`, `privilege_escalation`, `generic`.

## Normalization aliases (configurable)

`src_ip, sourceIP, source_address, client_ip, remote_ip, SRC → source_ip`
`dst_ip, destinationIP, dest_addr → destination_ip`
`user, username, user_name, account, uid → username`
`event, event_name, eventType, action → event_type / action`

Full alias tables live in `backend/app/services/normalization/aliases.py` and are
overridable per parser pack.
