# Parser Packs

Declarative parser definitions (YAML). A pack is **pure data** — detection
hints, named-group regexes, field mappings, a small fixed set of value
transformations, and self-tests. No code from a pack is ever executed.

Loaded automatically at backend startup (`parser_packs/**/*.yaml`) and also
manageable at runtime via `POST /api/parsers` (ADMIN), which stores versions in
the database.

The built-in parsers (`syslog`, `linux_auth`, `apache`, `nginx`, `firewall`,
`json`, `keyvalue`) live in code for performance; the packs here add formats the
built-ins don't cover.

## Schema

```yaml
parser:
  name: haproxy            # unique
  version: 1.0.0
  format: HAPROXY_HTTP
  schema_version: "1.0"
  specificity: 4           # tie-break vs other parsers on equal confidence
  description: "..."
detect:
  hints: ['regex', ...]    # raise can_parse confidence when present
patterns:                  # ordered; first match wins
  - 'named-group regex'
field_mappings:            # regex group name -> universal / raw field name
  captured_name: source_ip
transformations:           # applied to a group's value before mapping
  status: int
  ts: { type: strptime, format: "%d/%b/%Y:%H:%M:%S.%f" }
  service: { type: const, value: http }
event_type:
  default: http_request
tests:
  - input: 'a real line'
    expect: { source_ip: '1.2.3.4', response_code: 200 }
```

Allowed transform types: `int float lower upper strip strptime epoch const`.

## Bundled packs

| Pack | Format | Adds |
|------|--------|------|
| `haproxy` | `HAPROXY_HTTP` | HAProxy HTTP-mode access log |
| `cef` | `CEF` | ArcSight Common Event Format (`CEF:0|vendor|product|...`) |
| `postgresql` | `POSTGRESQL` | PostgreSQL server log line |
