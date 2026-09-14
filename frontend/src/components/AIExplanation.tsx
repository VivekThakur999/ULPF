import { AlertTriangle, ShieldCheck, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui";
import type { AIExplainResponse } from "@/services/endpoints";

const EVIDENCE_FIELDS = [
  "timestamp", "source", "host", "event_type", "username", "email",
  "source_ip", "destination_ip", "source_port", "destination_port",
  "protocol", "action", "status", "severity", "http_method", "response_code",
];

/**
 * Renders one AI explanation with a hard visual boundary between authoritative
 * ULPF EVIDENCE (server-retrieved) and the advisory AI EXPLANATION (generated).
 * The two are never merged.
 */
export default function AIExplanation({ data }: { data: AIExplainResponse }) {
  const e = data.explanation;
  const ev = data.evidence as Record<string, any>;
  const event = (ev.event ?? {}) as Record<string, any>;
  const alert = (ev.alert ?? {}) as Record<string, any>;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* ---------- ULPF EVIDENCE ---------- */}
      <section className="rounded-lg border-2 border-blue-500/40 bg-blue-500/5 p-4">
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-blue-700" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-800">ULPF Evidence</h3>
          <Badge tone="blue">authoritative · deterministic</Badge>
        </div>

        {data.kind === "alert" ? (
          <dl className="space-y-1 text-sm">
            <Row k="Alert" v={alert.title} />
            <Row k="Severity" v={alert.severity} />
            <Row k="Risk score" v={`${Math.round(alert.risk_score ?? 0)} / 100 (${alert.risk_breakdown?.band ?? "?"})`} />
            <Row k="Lead rule" v={alert.rule_key} />
            <Row k="Status" v={alert.status} />
            <Row k="Reason (ULPF)" v={alert.reason} />
            {alert.risk_breakdown?.factors?.length > 0 && (
              <div className="pt-1">
                <dt className="text-xs uppercase text-gray-500">Risk factors (deterministic)</dt>
                <ul className="mt-1 space-y-0.5 text-xs">
                  {alert.risk_breakdown.factors.map((f: any) => (
                    <li key={f.factor} className="flex gap-2">
                      <span className="w-8 shrink-0 text-right font-mono text-blue-700">+{f.points}</span>
                      <span className="text-slate-700">{f.factor.replace(/_/g, " ")}</span>
                      <span className="truncate text-gray-500">— {f.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {ev.correlation?.counts && (
              <Row k="Correlation" v={`${ev.correlation.counts.events ?? 0} events · ${(ev.correlation.sources ?? []).join(", ")}`} />
            )}
          </dl>
        ) : (
          <>
            {data.kind === "raw" && (
              <div className="mb-2">
                <Badge tone="amber">UNTRUSTED LOG INPUT</Badge>
                {ev.disposition && <span className="ml-2 text-xs text-gray-400">disposition: {ev.disposition}</span>}
              </div>
            )}
            {ev.security_verdict && ev.security_verdict !== "SAFE" && (
              <div className="mb-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
                Security Shield verdict: <b>{ev.security_verdict}</b>
              </div>
            )}
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              {EVIDENCE_FIELDS.filter((f) => event[f] !== null && event[f] !== undefined && event[f] !== "").map((f) => (
                <div key={f} className="col-span-2 flex justify-between gap-3 border-b border-blue-500/10 py-0.5 sm:col-span-1">
                  <dt className="text-gray-500">{f}</dt>
                  <dd className="truncate text-right font-mono text-xs">{String(event[f])}</dd>
                </div>
              ))}
            </dl>
            {ev.parser?.name && (
              <p className="mt-2 text-xs text-gray-500">
                Parser: <span className="font-mono">{ev.parser.name}</span>
                {ev.parser.version && ` v${ev.parser.version}`}
              </p>
            )}
            {ev.raw_log && (
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all rounded bg-base-bg p-2 font-mono text-[11px] text-slate-800">
                {ev.raw_log}
              </pre>
            )}
          </>
        )}
      </section>

      {/* ---------- AI EXPLANATION ---------- */}
      <section className="rounded-lg border-2 border-purple-500/40 bg-purple-500/5 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-700" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-purple-800">AI Explanation</h3>
          <Badge tone="slate">{data.provider}</Badge>
          <Badge tone={data.offline ? "green" : "amber"}>{data.offline ? "LOCAL / OFFLINE" : "external"}</Badge>
          {data.model && <Badge tone="slate">model: {data.model}</Badge>}
          {e.fallback_from && <Badge tone="amber">fell back from {e.fallback_from}</Badge>}
        </div>

        <div className="rounded border border-amber-300 bg-amber-50 p-2 text-[11px] text-amber-900">
          <AlertTriangle className="mr-1 inline h-3 w-3" />
          {e.disclaimer}
        </div>

        <Block title="Summary">{e.summary}</Block>

        {e.important_fields.length > 0 && (
          <div className="mt-3">
            <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">Important Fields</h4>
            <ul className="space-y-1 text-xs">
              {e.important_fields.map((f, i) => (
                <li key={i}>
                  <span className="font-mono text-purple-800">{f.field}</span>
                  {": "}
                  <span className="font-mono text-slate-700">{f.value}</span>
                  {f.note && <span className="text-gray-500"> — {f.note}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        <Block title="Why It Matters">{e.why_it_matters}</Block>
        <Block title="Detection Context">{e.detection_context}</Block>
        <Block title="Related Activity">{e.related_activity}</Block>

        {e.suggested_steps.length > 0 && (
          <div className="mt-3">
            <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">Suggested Investigation Steps</h4>
            <ol className="list-decimal space-y-1 pl-5 text-xs text-slate-700">
              {e.suggested_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>
        )}
      </section>
    </div>
  );
}

function Row({ k, v }: { k: string; v: unknown }) {
  return (
    <div className="flex justify-between gap-3 border-b border-blue-500/10 py-0.5">
      <dt className="shrink-0 text-gray-500">{k}</dt>
      <dd className="text-right text-slate-800">{v ? String(v) : "—"}</dd>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  if (!children) return null;
  return (
    <div className="mt-3">
      <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">{title}</h4>
      <p className="text-sm text-slate-800">{children}</p>
    </div>
  );
}
