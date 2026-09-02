import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import {
  getAlert,
  listAlerts,
  runDetection,
  updateAlert,
  type Alert,
} from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import { Badge, EmptyState, ErrorState, PageHeader, Spinner } from "@/components/ui";
import { severityClass } from "@/utils/severity";
import EventDetail from "@/components/EventDetail";

const STATUSES = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"];

export default function AlertsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => listAlerts() });
  const detect = useMutation({
    mutationFn: () => runDetection(24),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div>
      <PageHeader
        title="Security Alerts"
        subtitle="Produced by the deterministic correlation + rules engine. Every alert carries a transparent risk breakdown and an incident timeline."
        actions={
          hasRole("ANALYST") && (
            <button className="btn-ghost" disabled={detect.isPending} onClick={() => detect.mutate()}>
              <RefreshCw className={`h-4 w-4 ${detect.isPending ? "animate-spin" : ""}`} /> Run detection
            </button>
          )
        }
      />

      {alerts.isLoading ? (
        <Spinner />
      ) : alerts.isError ? (
        <ErrorState error={alerts.error} />
      ) : alerts.data && alerts.data.items.length > 0 ? (
        <div className="space-y-2">
          {alerts.data.items.map((a) => (
            <AlertRow key={a.id} alert={a} onOpen={() => setSelected(a.id)} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No alerts"
          hint="Ingest the brute-force scenario (Ingestion → Import sample), then Run detection."
        />
      )}

      {selected && <AlertDetail alertId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function AlertRow({ alert, onOpen }: { alert: Alert; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="flex w-full items-center gap-4 rounded-lg border border-base-border bg-base-panel p-3 text-left hover:bg-white/5"
    >
      <RiskDial score={alert.risk_score} band={alert.risk_breakdown.band} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`badge ${severityClass(alert.severity)}`}>{alert.severity}</span>
          <span className="truncate font-medium">{alert.title}</span>
        </div>
        <p className="mt-0.5 truncate text-xs text-gray-400">{alert.description}</p>
      </div>
      <Badge tone={alert.status === "NEW" ? "blue" : "slate"}>{alert.status}</Badge>
    </button>
  );
}

function RiskDial({ score, band }: { score: number; band: string }) {
  const color =
    band === "critical" ? "#ef4444" : band === "high" ? "#f97316" : band === "medium" ? "#f59e0b" : "#0ea5e9";
  return (
    <div
      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-bold"
      style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #1f2937 0deg)` }}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-base-panel">
        {Math.round(score)}
      </span>
    </div>
  );
}

function AlertDetail({ alertId, onClose }: { alertId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const { hasRole } = useAuth();
  const [eventId, setEventId] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["alert", alertId], queryFn: () => getAlert(alertId) });
  const upd = useMutation({
    mutationFn: (body: { status?: string; resolution_note?: string }) => updateAlert(alertId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert", alertId] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <div
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-base-border bg-base-panel p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {q.isLoading || !q.data ? (
          <Spinner />
        ) : (
          <>
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <RiskDial score={q.data.alert.risk_score} band={q.data.alert.risk_breakdown.band} />
                <div>
                  <h2 className="font-semibold">{q.data.alert.title}</h2>
                  <p className="text-xs text-gray-500">
                    {q.data.alert.rule_key} · {new Date(q.data.alert.ts).toLocaleString()}
                  </p>
                </div>
              </div>
              <button className="btn-ghost py-1 text-xs" onClick={onClose}>
                Close
              </button>
            </div>

            {hasRole("ANALYST") && (
              <div className="mb-4 flex flex-wrap gap-1.5">
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => upd.mutate({ status: s })}
                    className={`badge ${
                      q.data.alert.status === s ? "bg-brand text-white" : "bg-white/10 text-gray-300"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            <Section title="Why this triggered">
              <p className="text-sm text-gray-300">{q.data.alert.reason}</p>
            </Section>

            <Section title={`Risk score — ${q.data.alert.risk_breakdown.score}/100 (${q.data.alert.risk_breakdown.band})`}>
              <p className="mb-2 text-xs text-gray-400">{q.data.alert.risk_breakdown.summary}</p>
              <div className="space-y-1">
                {q.data.alert.risk_breakdown.factors.map((f) => (
                  <div key={f.factor} className="flex items-center gap-2 text-xs">
                    <span className="w-8 shrink-0 text-right font-mono text-brand-fg">+{f.points}</span>
                    <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded bg-white/10">
                      <div className="h-full bg-brand" style={{ width: `${Math.min(100, f.points * 3)}%` }} />
                    </div>
                    <span className="text-gray-300">{f.factor.replace(/_/g, " ")}</span>
                    <span className="truncate text-gray-500">— {f.detail}</span>
                  </div>
                ))}
              </div>
            </Section>

            <Section title="Recommended response (simulation only)">
              <div className="rounded border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
                <p className="font-medium">{q.data.alert.recommended_response.label}</p>
                <p className="mt-1 text-xs text-gray-400">{q.data.alert.recommended_response.note}</p>
                <p className="mt-1 text-xs text-gray-500">
                  Use the Response Simulator to model this action (no live enforcement).
                </p>
              </div>
            </Section>

            <Section title="Affected">
              <div className="flex flex-wrap gap-1.5 text-xs">
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
            </Section>

            <Section title={`Incident timeline (${q.data.timeline.length})`}>
              <ol className="relative ml-3 border-l border-base-border">
                {q.data.timeline.map((t) => (
                  <li key={t.event_id} className="mb-2 ml-4">
                    <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border-2 border-base-panel bg-brand" />
                    <button
                      className="text-left"
                      onClick={() => setEventId(t.event_id)}
                    >
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-mono text-gray-400">
                          {t.ts ? new Date(t.ts).toLocaleTimeString() : "—"}
                        </span>
                        <Badge tone="slate">{t.source}</Badge>
                        {t.severity && (
                          <span className={`badge ${severityClass(t.severity)}`}>{t.severity}</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-sm text-gray-200">{t.summary}</p>
                    </button>
                  </li>
                ))}
              </ol>
            </Section>

            <Section title={`Related evidence (${q.data.related_events.length})`}>
              <div className="space-y-1 text-xs">
                {q.data.related_events.slice(0, 40).map((e) => (
                  <button
                    key={e.id}
                    onClick={() => setEventId(e.id)}
                    className="flex w-full items-center gap-2 rounded border border-base-border p-1.5 text-left hover:bg-white/5"
                  >
                    <span className="text-gray-500">
                      {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "—"}
                    </span>
                    <Badge tone="slate">{e.source}</Badge>
                    <span>{e.event_type}</span>
                    <span className="ml-auto font-mono text-gray-500">{e.source_ip}</span>
                  </button>
                ))}
              </div>
            </Section>
          </>
        )}
      </div>
      {eventId && <EventDetail eventId={eventId} onClose={() => setEventId(null)} />}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
      {children}
    </div>
  );
}
