# Parser Development Guide

## Parser interface

Every parser (built-in or pack) implements:

```python
class BaseParser:
    name: str
    version: str
    format: str            # e.g. "SYSLOG"

    def can_parse(self, sample: str) -> float:      # 0.0–1.0 confidence
    def parse(self, line: str) -> ParseResult:      # fields + confidence + errors
    def validate(self) -> list[str]:                # self-check, returns problems
    def metadata(self) -> dict:
```

`ParseResult.fields` is a flat dict of raw field names; normalization maps them to the
[universal schema](universal-schema.md).

## Declarative parser packs (recommended)

`parser_packs/<name>/parser.yaml`:

```yaml
parser:
  name: apache
  version: 1.0.0
  format: APACHE_COMBINED
  schema_version: "1.0"
detect:
  # any regex that matches → contributes to can_parse confidence
  hints:
    - '^\S+ \S+ \S+ \[\d{2}/\w{3}/\d{4}'
patterns:
  - regex: '^(?P<source_ip>\S+) \S+ (?P<username>\S+) \[(?P<timestamp>[^\]]+)\] "(?P<http_method>\S+) (?P<url>\S+) [^"]*" (?P<response_code>\d{3}) (?P<bytes>\S+)'
field_mappings:
  bytes: extra.response_bytes
transformations:
  timestamp: { type: strptime, format: "%d/%b/%Y:%H:%M:%S %z" }
  response_code: { type: int }
event_type:
  default: http_request
tests:
  - input: '10.0.0.5 - alice [10/Oct/2024:13:55:36 +0000] "GET /x HTTP/1.1" 200 1024'
    expect: { source_ip: "10.0.0.5", response_code: 200, http_method: "GET" }
```

Packs are validated (regex compiles, named groups known, tests pass) before activation.
No Python is executed.

## WASM custom parsers

For formats a regex pack cannot express, compile a parser to WebAssembly exporting
`parse(ptr,len) -> ptr` over a simple JSON ABI. It runs in a sandbox with no
filesystem/network access and hard CPU/memory/time limits. See
`backend/app/services/wasm/`.

## Testing a parser

- Unit: `backend/tests/parsers/test_<name>.py`
- Live: paste a sample into the **Pipeline Debugger** and inspect each stage.
