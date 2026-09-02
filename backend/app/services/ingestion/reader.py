"""Turn an uploaded file's bytes into an ordered stream of raw records.

Supported container formats: .log/.txt (newline), .json (array or object),
.jsonl/.ndjson (newline JSON), .csv (row -> logfmt line), .syslog (newline).
"""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator

MAX_RECORD_BYTES = 64 * 1024


def _decode(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc), warnings
        except UnicodeDecodeError:
            continue
    warnings.append("undecodable bytes replaced")
    return data.decode("utf-8", errors="replace"), warnings


def _logfmt(row: dict) -> str:
    parts = []
    for k, v in row.items():
        if v is None or v == "":
            continue
        s = str(v)
        parts.append(f'{k}="{s}"' if (" " in s or "=" in s) else f"{k}={s}")
    return " ".join(parts)


def iter_records(
    data: bytes,
    *,
    filename: str = "",
    fmt_hint: str | None = None,
) -> Iterator[tuple[int, str, bool]]:
    """Yield (line_number, record_text, is_blank).

    Blank lines are yielded (is_blank=True) so the caller can count "empty lines"
    without them ever reaching the pipeline.
    """
    text, _warn = _decode(data)
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    stripped = text.lstrip()

    # JSON array / single object
    if ext == ".json" or (fmt_hint == "JSON" and stripped[:1] in "[{"):
        try:
            obj = json.loads(text)
            if isinstance(obj, list):
                for i, item in enumerate(obj, start=1):
                    yield i, json.dumps(item, separators=(",", ":")), False
                return
            if isinstance(obj, dict):
                # could be {"events":[...]} or a single event
                for key in ("events", "records", "logs", "data"):
                    if isinstance(obj.get(key), list):
                        for i, item in enumerate(obj[key], start=1):
                            yield i, json.dumps(item, separators=(",", ":")), False
                        return
                yield 1, json.dumps(obj, separators=(",", ":")), False
                return
        except ValueError:
            pass  # fall through to line handling

    # CSV
    if ext == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        n = 0
        for row in reader:
            n += 1
            clean = {(k or "").strip(): (v or "").strip() for k, v in row.items() if k}
            yield n, _logfmt(clean), not any(clean.values())
        return

    # default: newline-delimited (log, txt, jsonl, ndjson, syslog, unknown)
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\r\n")
        if line.strip() == "":
            yield i, "", True
            continue
        if len(line.encode("utf-8", errors="ignore")) > MAX_RECORD_BYTES:
            line = line[:MAX_RECORD_BYTES]
        yield i, line, False
