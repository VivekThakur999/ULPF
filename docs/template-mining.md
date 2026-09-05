# Template Mining & Micro-Compression (Modules 23–24)

## 1. Purpose

Most log volume is a handful of message shapes repeated with different values.
ULPF mines those shapes ("templates") from the **real ingested raw logs**, then
can store each occurrence as a *template reference + its variable values*
instead of the full string — while guaranteeing the original line can be
reconstructed **byte-for-byte**.

Nothing in this subsystem executes or interprets log content. It is pure
text/regex processing — verified by `tests/test_compression.py::test_no_eval_exec_in_template_or_compression_code`.

## 2. Mining algorithm

`app/services/templates/{classify,mining,service}.py`. Deterministic, no ML.

1. **Tokenize** each raw line into whitespace-delimited tokens
   (`re.finditer(r"\S+")`). The exact inter-token separators and any trailing
   text are captured verbatim so reconstruction is exact regardless of tabs,
   multiple spaces, or quote characters.
2. **Classify** each token with a conservative regex set:
   `ipv4, ipv6, uuid, mac, email, url, timestamp` (single-token forms),
   `hash` (hex ≥ 8 with a letter, or ≥ 32), `number`, `quoted`.
   `ipv6` explicitly rejects `hh:mm:ss` time strings.
3. **Bucket** lines by exact token count — a template never spans lines of
   different structural length.
4. Within a bucket, decide **per position** whether it is an **anchor**
   (structural, kept as literal text) or a **variable**, *order-independently*:
   - a position where ≥ 50 % of lines carry a high-cardinality variable type
     (`ipv4/ipv6/uuid/mac/timestamp/hash/email/url`) → **variable**;
   - a position whose single most-common value covers ≥ 50 % of the bucket, or
     which has one distinct value → **anchor** (e.g. `password`, `Failed`,
     `HTTP/1.1"`);
   - otherwise (a spread of many values — usernames, paths, ports) → **variable**.
5. **Cluster** lines by the tuple of their anchor-position values. Each cluster
   is one template: anchor positions become literal text, variable positions
   become `<*>` with a recorded type (`ip`, `number`, … or `value` when it was
   wildcarded only because it varied).
6. A **deterministic `TPL-XXXX` id** is assigned the first time a template
   shape is persisted (highest existing suffix + 1). Its `token_signature`
   (SHA-256 of `token_count | shape`) is the dedup key: re-mining the same data
   reuses the same id and updates the stats in place.

### Idempotency / scope contract

Each `POST /api/templates/mine` call is a **fresh full clustering pass** over
the rows its filters (`source`, `time_from`, `time_to`, `limit`) select. Re-running
with the same filters over unchanged data produces the same templates and ids.
Occurrence counts reflect exactly what that call scanned — mining is idempotent
per scope, not cumulative across different scopes. Default scan cap is 20 000
rows (`scan_limit_hit` is reported, never a silent truncation).

### Tuning knobs (`mining.py`)

`_ANCHOR_DOMINANCE = 0.5`, `_VARIABLE_TYPE_FRACTION = 0.5`. Lower dominance →
more aggressive templating (fewer, broader templates); higher → more granular.

### Known limitations

- Fixed token-count bucketing: a message with an optional trailing field lands
  in two templates.
- The whitespace tokenizer does not sub-tokenize inside a quoted request line,
  so a varying `"GET /path HTTP/1.1"` is one variable carrying the constant
  `GET`/`HTTP/1.1` text.
- O(buckets × distinct-anchor-keys); fine for the demo scale. A Drain-style
  prefix tree would scale better for very high volume (future work).

## 3. Template model

`templates` table (`app/models/template.py`):

| field | meaning |
|---|---|
| `template_key` | `TPL-0045` |
| `pattern` | readable form, `User <*> logged in from <*>` |
| `token_count` | |
| `literal_tokens` | `list[str \| null]` — null at variable positions |
| `variable_types` | type tag per variable position |
| `separators`, `trailing` | representative layout (for display) |
| `token_signature` | dedup identity of this shape |
| `occurrences`, `variable_count` | |
| `source_distribution` | `{source: count}` |
| `examples` | bounded sample (≤ 8) of real matching lines |
| `first_seen`, `last_seen`, `created_at`, `updated_at` | |

## 4. Compressed representation

`template_matches` table — one row per raw log:

```
raw_log_id  (unique)      template_id
variables : [<v0>, <v1>, …]      # the fixed-position values, in order
separators: null | [str, …]      # only stored if they differ from the template default
trailing  : ""   | str           # only if non-default
```

The **stored / measured** payload for a record is the JSON
`{"t": template_key, "v": variables[, "s": separators][, "e": trailing]}`
(compact separators, `ensure_ascii=False`).

### Reconstruction guarantee — `decompress(compress(log)) == log`

`reconstruct(template, match)` interleaves
`sep[i] + (literal[i] or next(variable)) + …  + trailing`, using the record's
own separators/trailing when stored and the template's otherwise. Because
literal tokens are copied verbatim, variables are exact original substrings,
and separators are captured byte-exact, the result is identical to the input.

This is **verified, never assumed**: `run_benchmark` reconstructs *every*
record in scope and compares to the stored original; `reconstructable_count`
and any `mismatches` are reported. `POST /api/compression/decompress` does the
same for a single record and returns `exact_match`.
`tests/test_compression.py` asserts exact equality across the bulk sample plus
Unicode, long lines, odd whitespace, quotes and attacker-payload lines.

## 5. Benchmark methodology

`POST /api/compression/benchmark` (persists a `compression_records` row):

| measured value | how |
|---|---|
| `original_bytes` | Σ `len(raw.content.encode("utf-8"))` |
| `compressed_bytes` | Σ bytes of each record's compact JSON payload |
| `metadata_bytes` | Σ bytes of each **distinct** template definition (stored once, shared by all its occurrences) |
| `total_compressed_bytes` | `compressed_bytes + metadata_bytes` |
| `savings_bytes` | `original_bytes − total_compressed_bytes` (**may be negative**) |
| `reduction_pct` | `savings_bytes / original_bytes × 100` (shown as-is, never clamped) |
| `reconstructable_count` | records that reconstructed byte-for-byte |
| `processing_seconds`, `events_per_sec` | wall-clock of the run |

Whether savings are positive depends entirely on the data: gains grow with line
length, repetition, and the fraction of each line that is constant. On a small
or highly heterogeneous scope the per-template metadata can exceed the
originals and the benchmark will honestly report a negative percentage.

**ULPF does not claim a fixed compression ratio.** Every figure shown in the UI
comes from an actual measured run.
