"""Deterministic PII pseudonymization (Module 9).

Design:
  * keyed HMAC-SHA256 over  f"{scope}:{kind}:{normalized_value}"  with PII_HMAC_KEY
  * pseudonym =  f"{PREFIX}_{HEX[:token_length].upper()}"   e.g.  IP_7F82A1
  * same input -> same pseudonym within a privacy scope, enabling correlation
    without exposing the raw identifier.

Modes: OFF | MASK | DETERMINISTIC_HASH.  Plaintext PII is not persisted when a
protecting mode is active.  We do NOT claim this alone is "GDPR compliant".
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from app.core.config import settings
from app.services.normalization.aliases import FIELD_ALIASES

PII_OFF = "OFF"
PII_MASK = "MASK"
PII_HASH = "DETERMINISTIC_HASH"

# canonical universal field -> identifier kind
_CANONICAL_KIND = {
    "source_ip": "ip",
    "destination_ip": "ip",
    "email": "email",
    "username": "username",
    "host": "host",
}


def _kind_for(field_name: str) -> str | None:
    """Resolve a raw/aliased field name to an identifier kind (alias-aware)."""
    low = field_name.strip().lower()
    if low in _CANONICAL_KIND:
        return _CANONICAL_KIND[low]
    canonical = FIELD_ALIASES.get(low)
    if canonical in _CANONICAL_KIND:
        return _CANONICAL_KIND[canonical]
    return None


def _hmac_hex(kind: str, value: str, scope: str) -> str:
    msg = f"{scope}:{kind}:{value.strip().lower()}".encode("utf-8")
    return hmac.new(settings.pii_hmac_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def pseudonymize(value: str, kind: str, *, scope: str = "global", token_length: int = 6) -> str:
    prefix = {"ip": "IP", "email": "EMAIL", "username": "USER", "host": "HOST"}.get(
        kind, kind.upper()
    )
    digest = _hmac_hex(kind, value, scope)
    return f"{prefix}_{digest[:token_length].upper()}"


def mask(value: str, kind: str) -> str:
    v = value.strip()
    if kind == "ip":
        if ":" in v:  # ipv6
            head = v.split(":")[0]
            return f"{head}:xxxx::xxxx"
        parts = v.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
        return "x.x.x.x"
    if kind == "email":
        if "@" in v:
            local, _, domain = v.partition("@")
            return f"{local[:1]}***@{domain}"
        return "***"
    # username / host
    return f"{v[:1]}***" if v else "***"


class _Settings:
    """Lightweight view over a PiiSetting row or config defaults."""

    def __init__(self, row: Any = None, mode_override: str | None = None):
        self.mode = mode_override or (getattr(row, "mode", None) or settings.pii_default_mode)
        self.scope = getattr(row, "scope", None) or "global"
        self.token_length = getattr(row, "token_length", None) or 6
        self.protect_ip = getattr(row, "protect_ip", True)
        self.protect_email = getattr(row, "protect_email", True)
        self.protect_username = getattr(row, "protect_username", True)
        self.protect_host = getattr(row, "protect_host", False)

    def wants(self, kind: str) -> bool:
        return {
            "ip": self.protect_ip,
            "email": self.protect_email,
            "username": self.protect_username,
            "host": self.protect_host,
        }.get(kind, False)


def apply_pii(
    fields: dict[str, Any],
    *,
    settings: Any = None,
    mode_override: str | None = None,
) -> tuple[dict[str, Any], list[dict], str]:
    cfg = _Settings(settings, mode_override)
    if cfg.mode == PII_OFF:
        return dict(fields), [], PII_OFF

    out = dict(fields)
    transforms: list[dict] = []

    for key, value in list(fields.items()):
        if value in (None, ""):
            continue
        kind = _kind_for(key)
        if not kind or not cfg.wants(kind):
            continue

        original = str(value)
        if cfg.mode == PII_HASH:
            new_value = pseudonymize(original, kind, scope=cfg.scope,
                                     token_length=cfg.token_length)
        else:  # MASK
            new_value = mask(original, kind)

        out[key] = new_value
        transforms.append({
            "field": key,
            "kind": kind,
            "mode": cfg.mode,
            # NOTE: the original value is intentionally NOT recorded here.
            "pseudonym": new_value,
        })

    return out, transforms, cfg.mode
