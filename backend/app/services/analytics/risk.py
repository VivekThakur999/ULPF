"""Transparent risk scoring (Module 16).

Every point in the 0-100 score is attributable to a named factor with a
human-readable explanation. There is no hidden model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_SEV_POINTS = {"critical": 22, "high": 15, "medium": 9, "low": 4, "info": 1}


@dataclass
class RiskFactor:
    factor: str
    points: int
    detail: str

    def to_dict(self) -> dict:
        return {"factor": self.factor, "points": self.points, "detail": self.detail}


@dataclass
class RiskResult:
    score: int
    band: str
    factors: list[RiskFactor] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "band": self.band,
            "factors": [f.to_dict() for f in self.factors],
            "summary": self.summary,
        }


def band_for(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 15:
        return "low"
    return "info"


@dataclass
class RiskContext:
    failed_logins: int = 0
    successful_logins: int = 0
    affected_hosts: int = 0
    distinct_sources: int = 0
    distinct_usernames: int = 0
    span_seconds: float | None = None
    total_events: int = 0
    max_event_severity: str | None = None
    shield_verdict: str | None = None            # SAFE | SUSPICIOUS | WEAPONIZED_LOG
    success_after_failures: bool = False
    connections_denied: int = 0
    rule_severity: str | None = None             # severity of the rule that fired


def compute_risk(ctx: RiskContext) -> RiskResult:
    factors: list[RiskFactor] = []

    if ctx.failed_logins:
        pts = min(30, ctx.failed_logins * 3)
        factors.append(RiskFactor(
            "failed_authentication_volume", pts,
            f"{ctx.failed_logins} failed authentication events observed",
        ))

    if ctx.affected_hosts > 1:
        pts = min(16, (ctx.affected_hosts - 1) * 7)
        factors.append(RiskFactor(
            "multiple_affected_hosts", pts,
            f"activity touched {ctx.affected_hosts} distinct hosts",
        ))

    if ctx.distinct_sources > 1:
        pts = min(20, (ctx.distinct_sources - 1) * 8)
        factors.append(RiskFactor(
            "cross_source_correlation", pts,
            f"the same entity appears across {ctx.distinct_sources} independent log sources",
        ))

    if ctx.span_seconds is not None and ctx.total_events >= 3:
        minutes = max(ctx.span_seconds / 60.0, 0.1)
        rate = ctx.total_events / minutes
        if rate >= 20:
            pts, lvl = 18, "very high"
        elif rate >= 8:
            pts, lvl = 12, "high"
        elif rate >= 3:
            pts, lvl = 7, "elevated"
        else:
            pts, lvl = 2, "moderate"
        factors.append(RiskFactor(
            "time_concentration", pts,
            f"{ctx.total_events} events in ~{minutes:.1f} min ({rate:.1f}/min, {lvl})",
        ))

    if ctx.max_event_severity:
        pts = _SEV_POINTS.get(ctx.max_event_severity, 0)
        if pts:
            factors.append(RiskFactor(
                "event_severity", pts,
                f"highest individual event severity is '{ctx.max_event_severity}'",
            ))

    if ctx.distinct_usernames > 1:
        pts = min(10, ctx.distinct_usernames * 3)
        factors.append(RiskFactor(
            "multiple_targeted_accounts", pts,
            f"{ctx.distinct_usernames} distinct accounts targeted",
        ))

    if ctx.shield_verdict == "WEAPONIZED_LOG":
        factors.append(RiskFactor("security_shield", 25,
                                  "Security Shield flagged weaponized log content"))
    elif ctx.shield_verdict == "SUSPICIOUS":
        factors.append(RiskFactor("security_shield", 10,
                                  "Security Shield flagged suspicious log content"))

    if ctx.success_after_failures:
        factors.append(RiskFactor(
            "successful_login_after_failures", 15,
            "a successful login followed a burst of failures for the same entity",
        ))

    if ctx.connections_denied >= 3:
        factors.append(RiskFactor(
            "repeated_blocked_connections", min(10, ctx.connections_denied),
            f"{ctx.connections_denied} firewall/network connections were denied",
        ))

    raw = sum(f.points for f in factors)
    # Transparent curve: linear up to 60, then compressed so that only genuinely
    # extreme, many-factor incidents approach 100.
    if raw <= 60:
        score = raw
    else:
        score = round(60 + (raw - 60) * 0.6)
    score = max(0, min(100, score))
    band = band_for(score)
    factors.sort(key=lambda f: f.points, reverse=True)
    top = factors[0].factor.replace("_", " ") if factors else "no notable factors"
    summary = (
        f"Risk {score}/100 ({band.upper()}). Sum of factor points = {raw}"
        + (f", compressed above 60 to {score}" if raw > 60 else "")
        + f". Primary driver: {top}. {len(factors)} contributing factor(s)."
    )
    return RiskResult(score=score, band=band, factors=factors, summary=summary)
