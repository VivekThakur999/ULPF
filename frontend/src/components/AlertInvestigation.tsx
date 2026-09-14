import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, PlayCircle, Sparkles } from "lucide-react";
import { getAlert, updateAlert, type Alert, type TimelineEntry } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import {
  Badge,
  Drawer,
  ErrorState,
  RiskMeter,
  SectionHeader,
  Spinner,
  StatusPill,
} from "@/components/ui";
import EventDetail from "@/components/EventDetail";

const STATUSES = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"];

export default function AlertInvestigation({
  alertId,
  onClose,
}: {
  alertId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [eventId, setEventId] = useState<string | null>(null);

  const q = useQuery({ queryKey: ["alert", alertId], queryFn: () => getAlert(alertId) });
  const upd = useMutation({
    mutationFn: (body: { status?: string; resolution_note?: string }) => updateAlert(alertId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert", alertId] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["nav-active-alerts"] });
    },
  });

  const alert = q.data?.alert;

  return (
    <Drawer
      open
      onClose={onClose}
      width="max-w-3xl"
      title={alert?.title ?? "Alert investigation"}
      subtitle={alert ? `${alert.rule_key ?? "no rule"} · ${new Date(alert.ts).toLocaleString()}` : undefined}
      actions={
        alert && (
          <>
            <StatusPill status={alert.severity} />
            <StatusPill status={alert.status} />
          </>
        )
      }
    >
      {q.isLoading || !q.data ? (
        <Spinner label="Loading alert…" />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <Link to={`/assistant?alert=${alertId}`} className="btn-ghost py-1.5 text-xs" onClick={onClose}>
              <Sparkles className="h-3.5 w-3.5" /> Explain with AI
            </Link>
            <Link to={`/response?alert=${alertId}`} className="btn-ghost py-1.5 text-xs" onClick={onClose}>
              <PlayCircle className="h-3.5 w-3.5" /> Simulate Response
            </Link>
          </div>

          {hasRole("ANALYST") && (
            <div className="flex flex-wrap gap-1.5">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => upd.mutate({ status: s })}
                  disabled={upd.isPending}
                  className={`badge ${
                    q.data!.alert.status === s
                      ? "bg-brand text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {s.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          )}

          <InvestigationChain alert={q.data.alert} timeline={q.data.timeline} />

          <section>
            <SectionHeader title="Why this triggered" />
            <p className="text-sm text-slate-700">{q.data.alert.reason}</p>
          </section>

          <section>
            <SectionHeader
              title="Risk score"
              hint={q.data.alert.risk_breakdown.summary}
            />
            <RiskMeter
              score={q.data.alert.risk_breakdown.score}
              band={q.data.alert.risk_breakdown.band}
              factors={q.data.alert.risk_breakdown.factors}
            />
          </section>

          <CorrelationGraph alert={q.data.alert} timeline={q.data.timeline} />

          <section>
            <SectionHeader title="Recommended response" right={<StatusPill status="simulation" />} />
            <div className="surface-2 p-3 text-sm">
              <p className="font-medium text-slate-800">{q.data.alert.recommended_response.label}</p>
              <p className="mt-1 text-xs text-gray-400">{q.data.alert.recommended_response.note}</p>
              <p className="mt-1 text-xs text-gray-500">
                Model this in the Response Simulator — ULPF never enforces it.
              </p>
            </div>
          </section>

          <section>
            <SectionHeader title="Affected" />
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(q.data.alert.entity)
                .filter(([k]) => !["type", "incident_center", "window_seconds"].includes(k))
                .map(([k, v]) => (
                  <Badge key={k} tone="slate">
                    {k}: {String(v)}
                  </Badge>
                ))}
              {q.data.alert.affected_hosts.map((h) => (
                <Badge key={h} tone="neutral">
                  host: {h}
                </Badge>
              ))}
            </div>
          </section>

          <section>
            <SectionHeader title={`Incident timeline (${q.data.timeline.length})`} />
            <ol className="relative ml-2 space-y-2 border-l border-base-border pl-4">
              {q.data.timeline.map((t) => (
                <li key={t.event_id}>
                  <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-brand" aria-hidden />
                  <button className="text-left" onClick={() => setEventId(t.event_id)}>
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-mono text-gray-400">
                        {t.ts ? new Date(t.ts).toLocaleTimeString() : "—"}
                      </span>
                      <Badge tone="slate">{t.source}</Badge>
                      {t.severity && <StatusPill status={t.severity} />}
                    </div>
                    <p className="mt-0.5 text-sm text-slate-800">{t.summary}</p>
                  </button>
                </li>
              ))}
            </ol>
          </section>

          <section>
            <SectionHeader title={`Related evidence (${q.data.related_events.length})`} />
            <div className="space-y-1 text-xs">
              {q.data.related_events.slice(0, 40).map((e) => (
                <button
                  key={e.id}
                  onClick={() => setEventId(e.id)}
                  className="surface-2 flex w-full items-center gap-2 p-1.5 text-left hover:bg-slate-100"
                >
                  <span className="text-gray-500">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <Badge tone="slate">{e.source}</Badge>
                  <span className="text-slate-700">{e.event_type}</span>
                  <span className="ml-auto font-mono text-gray-500">{e.source_ip}</span>
                </button>
              ))}
              {q.data.related_events.length === 0 && (
                <p className="text-gray-500">No correlated evidence.</p>
              )}
            </div>
          </section>
        </div>
      )}

      {eventId && <EventDetail eventId={eventId} onClose={() => setEventId(null)} />}
    </Drawer>
  );
}

/**
 * The vertical "12 failed auth -> 4 sources -> same identity -> RULE -> risk ->
 * severity" chain. Built only from this alert's real timeline + risk data.
 */
function InvestigationChain({ alert, timeline }: { alert: Alert; timeline: TimelineEntry[] }) {
  const sources = new Set(timeline.map((t) => t.source));
  const hosts = new Set(timeline.map((t) => t.host).filter(Boolean));
  const steps = [
    `${timeline.length} correlated event${timeline.length === 1 ? "" : "s"}`,
    `${sources.size} source${sources.size === 1 ? "" : "s"}${hosts.size ? ` · ${hosts.size} host${hosts.size === 1 ? "" : "s"}` : ""}`,
    alert.rule_key ? `${alert.rule_key} triggered` : "correlation rule triggered",
    `Risk ${Math.round(alert.risk_score)} / 100 (${alert.risk_breakdown.band})`,
    `${alert.severity.toUpperCase()} severity alert`,
  ];
  return (
    <div className="surface-2 p-4">
      <ol className="space-y-1.5">
        {steps.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-sm">
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand/15 text-2xs font-semibold text-brand-fg">
              {i + 1}
            </span>
            <span className="text-slate-800">{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Sources ─ shared identity/indicator ─ rule. Uses the alert's real evidence. */
function CorrelationGraph({ alert, timeline }: { alert: Alert; timeline: TimelineEntry[] }) {
  const bySource = new Map<string, number>();
  for (const t of timeline) bySource.set(t.source, (bySource.get(t.source) ?? 0) + 1);
  const sources = [...bySource.entries()];
  if (sources.length === 0) return null;

  const pivotEntries = Object.entries(alert.entity).filter(
    ([k]) => !["type", "incident_center", "window_seconds"].includes(k),
  );
  const pivot = pivotEntries.length ? pivotEntries.map(([k, v]) => `${k}=${v}`).join(" · ") : "shared indicator";

  return (
    <section>
      <SectionHeader title="Correlation" hint="How ULPF linked these events" />
      <div className="surface-2 flex flex-col items-stretch gap-3 p-4 lg:flex-row lg:items-center">
        <div className="flex flex-1 flex-wrap justify-center gap-2">
          {sources.map(([src, n]) => (
            <div key={src} className="rounded-md border border-base-border bg-base-panel px-3 py-2 text-center text-xs">
              <div className="font-semibold uppercase tracking-wide text-slate-800">{src}</div>
              <div className="text-gray-500">{n} event{n === 1 ? "" : "s"}</div>
            </div>
          ))}
        </div>
        <ArrowRight className="mx-auto hidden h-4 w-4 shrink-0 text-gray-600 lg:block" />
        <div className="rounded-md border border-brand/40 bg-brand/10 px-3 py-2 text-center text-xs">
          <div className="font-semibold uppercase tracking-wide text-brand-fg">Shared</div>
          <div className="font-mono text-slate-700">{pivot}</div>
        </div>
        <ArrowRight className="mx-auto hidden h-4 w-4 shrink-0 text-gray-600 lg:block" />
        <div className="rounded-md border border-base-border bg-base-panel px-3 py-2 text-center text-xs">
          <div className="font-semibold uppercase tracking-wide text-slate-800">{alert.rule_key ?? "rule"}</div>
          <div className="text-gray-500">{alert.severity} · risk {Math.round(alert.risk_score)}</div>
        </div>
      </div>
    </section>
  );
}
