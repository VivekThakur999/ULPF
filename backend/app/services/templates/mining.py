"""Deterministic template mining (Module 23).

Algorithm (documented in docs/template-mining.md):

  1. tokenize each line into whitespace-delimited tokens; capture the exact
     inter-token separators so reconstruction stays byte-exact
  2. classify each token against a conservative set of regexes (IPv4/IPv6,
     UUID, MAC, email, URL, timestamp-like, hash, number, quoted)
  3. bucket lines by exact token count - a template never spans lines of
     different structural length
  4. inside a bucket, decide per position whether it is an ANCHOR (structural)
     or a VARIABLE, order-independently:
       * a position where >=50% of lines carry a high-cardinality variable
         type (ip, timestamp, ...) is a variable
       * a position whose most common value covers >=50% of the lines, or
         which has a single distinct value, is an anchor (a keyword like
         "password" or "Failed")
       * everything else (a spread of many values - usernames, paths) is a
         variable
  5. cluster lines by the tuple of their anchor-position values; every cluster
     is one template, anchors kept as literal text, variables wildcarded
  6. a deterministic TPL-XXXX id is assigned when a template shape is first
     persisted; re-mining the same data reuses it (matched by token_signature)

No ML dependency; no code execution; pure text/regex processing.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from app.services.templates.classify import (
    HIGH_CARDINALITY_TYPES,
    classify_token,
    separators_for,
    tokenize,
)

# A position is a structural anchor if its dominant value covers at least this
# fraction of the bucket (or it has a single value). Tunable - see the docs.
_ANCHOR_DOMINANCE = 0.5
# ...but not if this fraction of lines classify it as a high-cardinality variable.
_VARIABLE_TYPE_FRACTION = 0.5

WILDCARD = "<*>"


@dataclass
class RecordRef:
    ref_id: str
    source: str
    ts: datetime | None
    raw: str


@dataclass
class MinedCluster:
    token_count: int
    literals: list[str | None]          # None = wildcard position
    var_types: list[str | None]         # set at wildcard positions
    separators: list[str]               # from the first example
    trailing: str                       # from the first example
    members: list[RecordRef] = field(default_factory=list)

    @property
    def occurrences(self) -> int:
        return len(self.members)

    @property
    def variable_count(self) -> int:
        return sum(1 for t in self.literals if t is None)

    def pattern_text(self) -> str:
        parts = []
        for i, lit in enumerate(self.literals):
            parts.append(self.separators[i] if i < len(self.separators) else " ")
            parts.append(WILDCARD if lit is None else lit)
        parts.append(self.trailing)
        return "".join(parts).strip()

    def token_signature(self) -> str:
        """Stable identity for this exact literal/wildcard shape."""
        shape = [
            f"<{self.var_types[i] or 'VAR'}>" if lit is None else lit
            for i, lit in enumerate(self.literals)
        ]
        raw = f"{self.token_count}|" + "\x1f".join(shape)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def extract_variables(self, tokens: list[str]) -> list[str]:
        return [tok for tok, lit in zip(tokens, self.literals) if lit is None]


@dataclass
class _Parsed:
    rec: RecordRef
    tokens: list[str]
    types: list[str | None]
    seps: list[str]
    trailing: str


def _anchor_mask(rows: list[_Parsed], token_count: int) -> list[bool]:
    """True at positions that are structural anchors (kept literal)."""
    n = len(rows)
    mask = [True] * token_count
    for i in range(token_count):
        hc = sum(1 for r in rows if r.types[i] in HIGH_CARDINALITY_TYPES)
        if hc >= max(1, n * _VARIABLE_TYPE_FRACTION):
            mask[i] = False
            continue
        counts = Counter(r.tokens[i] for r in rows)
        if len(counts) == 1:
            continue  # single value everywhere -> anchor
        dominant = counts.most_common(1)[0][1]
        mask[i] = (dominant / n) >= _ANCHOR_DOMINANCE
    return mask


def mine_lines(records: list[RecordRef]) -> list[MinedCluster]:
    """Cluster records into templates. Order-independent and deterministic."""
    buckets: dict[int, list[_Parsed]] = {}
    for rec in records:
        line = rec.raw
        if not line or not line.strip():
            continue
        spans = tokenize(line)
        if not spans:
            continue
        tokens = [s.text for s in spans]
        types = [classify_token(t) for t in tokens]
        seps, trailing = separators_for(line, spans)
        buckets.setdefault(len(tokens), []).append(
            _Parsed(rec, tokens, types, seps, trailing)
        )

    clusters: list[MinedCluster] = []
    for token_count, rows in buckets.items():
        anchors = _anchor_mask(rows, token_count)
        by_key: dict[tuple, MinedCluster] = {}
        for r in rows:
            key = tuple(r.tokens[i] for i in range(token_count) if anchors[i])
            cluster = by_key.get(key)
            if cluster is None:
                literals: list[str | None] = []
                var_types: list[str | None] = []
                for i in range(token_count):
                    if anchors[i]:
                        literals.append(r.tokens[i])
                        var_types.append(None)
                    else:
                        literals.append(None)
                        var_types.append(r.types[i] or "value")
                cluster = MinedCluster(
                    token_count=token_count, literals=literals, var_types=var_types,
                    separators=r.seps, trailing=r.trailing,
                )
                by_key[key] = cluster
            else:
                # widen the recorded type if this occurrence disagrees
                for i in range(token_count):
                    if cluster.literals[i] is None and cluster.var_types[i] != (r.types[i] or "value"):
                        cluster.var_types[i] = "value"
            cluster.members.append(r.rec)
        clusters.extend(by_key.values())

    return clusters
