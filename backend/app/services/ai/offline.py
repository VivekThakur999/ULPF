"""LOCAL OFFLINE EXPLAINER - a deterministic, template-based explanation layer.

This is NOT a language model. It arranges the ULPF evidence it is given into a
readable structure using fixed rules. Same input -> same output. It makes zero
network calls and cannot execute anything.
"""
from __future__ import annotations

from typing import Any

from app.services.ai.base import AIProvider, ExplainContext, Explanation, ImportantField

NA = "Not available in the current event context."

_FIELD_NOTES = {
    "timestamp": "when the event occurred (event time, not ingestion time)",
    "ingested_at": "when ULPF received the record",
    "source": "the logical log source this came from",
    "host": "the host/device the event is about",
    "event_type": "ULPF's canonical classification of the event",
    "severity": "ULPF-assigned severity for this individual event",
    "username": "account involved (pseudonymized if PII protection is on)",
    "email": "email identifier (pseudonymized if PII protection is on)",
    "source_ip": "originating address (pseudonymized if PII protection is on)",
    "destination_ip": "target address",
    "source_port": "originating port",
    "destination_port": "target port / service",
    "protocol": "network protocol",
    "action": "the action taken or attempted",
    "status": "outcome of the action",
    "process": "process that emitted the log",
    "service": "service involved",
    "url": "requested resource",
    "http_method": "HTTP method",
    "response_code": "HTTP response status code",
}

_EVENT_TYPE_MEANING = {
    "authentication_failure": (
        "A login attempt failed. On its own a single failure is routine; repeated "
        "failures from one source or against one account can indicate credential "
        "guessing or a misconfigured client."
    ),
    "authentication_success": (
        "A login succeeded. Worth checking when it follows a run of failures for the "
        "same account or source, or comes from an unexpected location."
    ),
    "account_locked": (
        "An account was locked out, typically after repeated failed authentications - "
        "a strong signal of sustained guessing against that account."
    ),
    "connection_denied": (
        "A network connection was blocked by a firewall/ACL. Repeated denials from one "
        "source often precede or accompany scanning or brute-force activity."
    ),
    "connection_allowed": "A network connection was permitted by policy.",
    "privilege_escalation": (
        "A process or user gained elevated privileges. Legitimate in admin workflows; "
        "notable when unexpected or paired with prior suspicious activity."
    ),
    "http_request": (
        "A web request was served. Error codes (4xx/5xx), unusual paths, or scanner "
        "user-agents are the things to look at."
    ),
    "session_opened": "A user session started.",
    "session_closed": "A user session ended.",
}

_STEPS_BY_EVENT_TYPE = {
    "authentication_failure": [
        "Confirm whether the source IP / account is expected for this host.",
        "Search the Log Explorer for other events from the same source_ip and username.",
        "Check for any subsequent authentication_success for the same account (possible compromise).",
        "Review firewall/network logs for the same source around this time.",
    ],
    "account_locked": [
        "Identify every source that contributed failed logins for this account.",
        "Confirm with the account owner whether they were attempting to log in.",
        "Check whether a successful login occurred before or after the lockout.",
    ],
    "connection_denied": [
        "Check how many distinct destination ports/hosts this source touched (scanning).",
        "Correlate with authentication events from the same source_ip.",
        "Decide whether to model a block using the Response Simulator (simulation only).",
    ],
    "http_request": [
        "Inspect the URL and user-agent for scanner / exploitation signatures.",
        "Group by source_ip to see request volume and error ratio.",
    ],
    "privilege_escalation": [
        "Confirm the escalation matches a known change/admin activity.",
        "Review what the elevated session did next.",
    ],
}

_GENERIC_STEPS = [
    "Open the raw log alongside the universal event to confirm the parsed fields.",
    "Use cross-source correlation to see related activity for the same entity.",
]


def _field_notes_for(evidence: dict[str, Any]) -> list[ImportantField]:
    out: list[ImportantField] = []
    for name, note in _FIELD_NOTES.items():
        val = evidence.get(name)
        if val in (None, "", [], {}):
            continue
        out.append(ImportantField(field=name, value=str(val), note=note))
    return out


def _summ_event(ev: dict[str, Any]) -> str:
    et = ev.get("event_type")
    if not et and not ev:
        return (
            "This log line could not be normalized into a universal event (it may have "
            "been quarantined by the Security Shield or is an unrecognized format). "
            "See the raw log and the shield verdict below."
        )
    bits = [f"This is a **{et.replace('_', ' ')}**" if et else "This log line was normalized"]
    if ev.get("source"):
        bits.append(f"from the `{ev['source']}` source")
    if ev.get("host"):
        bits.append(f"concerning host `{ev['host']}`")
    if ev.get("username"):
        bits.append(f"for account `{ev['username']}`")
    if ev.get("source_ip"):
        bits.append(f"originating from `{ev['source_ip']}`")
    if ev.get("action") and ev.get("status"):
        bits.append(f"- action `{ev['action']}`, outcome `{ev['status']}`")
    if ev.get("response_code"):
        bits.append(f"(HTTP {ev['response_code']})")
    parser = ev.get("parser")
    if parser:
        bits.append(f". Parsed by `{parser}` v{ev.get('parser_version', '?')}.")
    return " ".join(bits).strip()


class LightweightOfflineProvider(AIProvider):
    name = "LOCAL OFFLINE EXPLAINER"
    offline = True
    model = None

    def available(self) -> bool:
        return True

    def explain(self, ctx: ExplainContext) -> Explanation:
        if ctx.kind == "alert":
            return self._explain_alert(ctx)
        return self._explain_event(ctx)

    # --- event / raw ----------------------------------------------------------

    def _explain_event(self, ctx: ExplainContext) -> Explanation:
        ev = ctx.event or {}
        et = ev.get("event_type")

        summary = _summ_event(ev)
        if ctx.raw_untrusted:
            summary = (
                "This explanation covers a log line pasted by the analyst "
                "(**untrusted input**, not stored). " + summary
            )

        shield = ctx.evidence.get("security_verdict")
        if shield in ("WEAPONIZED_LOG", "SUSPICIOUS") and not et:
            why = (
                f"The Security Shield classified this raw line as **{shield}** and it was "
                "not parsed into a universal event. The line contains characters or "
                "patterns associated with log injection / weaponization (e.g. terminal "
                "escapes, `${jndi:...}` lookups, control bytes). ULPF stores it as "
                "evidence but does not process it further."
            )
        else:
            why = _EVENT_TYPE_MEANING.get(
                et or "",
                "ULPF normalized this line into the universal schema. Review the fields "
                "below against the raw log to judge its significance.",
            )
        sev = ev.get("severity")
        if sev in ("high", "critical"):
            why += f" ULPF assigned this event a **{sev}** severity."

        detection = self._event_detection_context(ctx)
        related = self._related_text(ctx.correlation)

        steps = list(_STEPS_BY_EVENT_TYPE.get(et or "", []))
        steps += _GENERIC_STEPS
        steps.append(
            "Treat this explanation as advisory - ULPF's deterministic detection is authoritative."
        )

        return Explanation(
            provider=self.name, offline=True, model=None,
            summary=summary,
            important_fields=_field_notes_for(ctx.evidence.get("event", ev)),
            why_it_matters=why,
            detection_context=detection,
            related_activity=related,
            suggested_steps=steps,
        )

    def _event_detection_context(self, ctx: ExplainContext) -> str:
        parts = []
        shield = ctx.evidence.get("security_verdict")
        if shield and shield != "SAFE":
            parts.append(
                f"The Security Shield flagged the raw log as **{shield}** before parsing."
            )
        sec_events = ctx.evidence.get("security_events") or []
        if sec_events:
            types = ", ".join(sorted({s.get("detection_type", "?") for s in sec_events}))
            parts.append(f"{len(sec_events)} shield detection(s) recorded: {types}.")
        linked = ctx.evidence.get("linked_alerts") or []
        if linked:
            parts.append(
                "This event is cited as evidence in "
                + ", ".join(f"alert '{a}'" for a in linked) + "."
            )
        if not parts:
            parts.append(
                "This event did not itself trigger a shield detection or an alert. "
                "That determination is made only by ULPF's deterministic engine."
            )
        return " ".join(parts)

    # --- alert --------------------------------------------------------------

    def _explain_alert(self, ctx: ExplainContext) -> Explanation:
        al = ctx.alert or {}
        rb = al.get("risk_breakdown") or {}
        entity = al.get("entity") or {}
        entity_str = ", ".join(f"{k}={v}" for k, v in entity.items()
                               if k not in ("type", "incident_center", "window_seconds")) or "n/a"

        summary = (
            f"ULPF raised a **{al.get('severity', '?')}** alert: \"{al.get('title', 'alert')}\". "
            f"Deterministic risk score **{int(al.get('risk_score', 0))}/100** "
            f"({rb.get('band', '?')} band). Focus entity: {entity_str}."
        )

        why = (
            "ULPF's deterministic rule engine produced this alert. Its own stated reason: "
            f"\"{al.get('reason') or NA}\""
        )

        # detection context straight from the deterministic breakdown
        dc_lines = []
        if al.get("rule_key"):
            dc_lines.append(f"Lead rule: {al['rule_key']}. Description: {al.get('description', '')}")
        factors = rb.get("factors") or []
        if factors:
            top = "; ".join(f"+{f['points']} {f['factor'].replace('_', ' ')} ({f['detail']})"
                            for f in factors[:5])
            dc_lines.append(f"Risk factors (deterministic): {top}.")
            dc_lines.append(f"Summary: {rb.get('summary', '')}")
        else:
            dc_lines.append("No risk-factor breakdown available.")
        detection = " ".join(dc_lines)

        related = self._related_text(ctx.correlation)
        if ctx.related_events:
            seq = " -> ".join(
                f"{e.get('source', '?')}:{e.get('event_type', '?')}"
                for e in ctx.related_events[:6]
            )
            related += f" Observed sequence: {seq}."

        steps = [
            f"Verify the entity ({entity_str}) against known/expected activity.",
            "Walk the incident timeline in the alert view to confirm the sequence is coherent.",
            "Check for a successful authentication after the failures (possible compromise).",
            "If the activity is confirmed hostile, use the Response Simulator to model containment "
            "(recommendation only - no live enforcement).",
            "Set the alert status (ACKNOWLEDGED / INVESTIGATING / RESOLVED / FALSE_POSITIVE) as you triage.",
            "This explanation restates ULPF's deterministic findings; it does not change the risk score, "
            "severity, or which rules fired.",
        ]

        important = [
            ImportantField("severity", str(al.get("severity")), "ULPF-assigned, deterministic"),
            ImportantField("risk_score", str(al.get("risk_score")), "sum of disclosed factors, curve-adjusted"),
            ImportantField("rule", str(al.get("rule_key")), "lead detection rule"),
            ImportantField("status", str(al.get("status")), "analyst triage state"),
        ]
        for k, v in entity.items():
            if k in ("type", "incident_center", "window_seconds"):
                continue
            important.append(ImportantField(k, str(v), "alert focus entity"))
        for h in (al.get("affected_hosts") or [])[:5]:
            important.append(ImportantField("affected_host", str(h), "host touched by this activity"))

        return Explanation(
            provider=self.name, offline=True, model=None,
            summary=summary, important_fields=important, why_it_matters=why,
            detection_context=detection, related_activity=related, suggested_steps=steps,
        )

    # --- shared ----------------------------------------------------------

    @staticmethod
    def _related_text(corr: dict[str, Any]) -> str:
        if not corr:
            return NA
        counts = corr.get("counts") or {}
        sources = corr.get("sources") or []
        hosts = corr.get("hosts") or []
        if not counts.get("events"):
            return "No correlated activity found for this entity in the search window."
        span = counts.get("span_seconds")
        span_txt = f"over ~{span / 60:.1f} min" if span else ""
        bits = [
            f"{counts.get('events', 0)} related event(s) {span_txt}".strip(),
            f"across {len(sources)} source(s) ({', '.join(sources)})" if sources else "",
            f"touching {len(hosts)} host(s)" if hosts else "",
        ]
        if counts.get("auth_failures"):
            bits.append(f"{counts['auth_failures']} authentication failure(s)")
        if counts.get("auth_successes"):
            bits.append(f"{counts['auth_successes']} authentication success(es)")
        if counts.get("connections_denied"):
            bits.append(f"{counts['connections_denied']} denied connection(s)")
        return ", ".join(b for b in bits if b) + "."
