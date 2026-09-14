import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  Database,
  Gauge,
  PieChart,
  RefreshCw,
  ShieldCheck,
  ShieldX,
  Terminal,
  Zap,
} from "lucide-react";
import { analyticsOverview, listAlerts, searchLogs } from "@/services/endpoints";
import {
  DataTable,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  SectionHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import { statusStyle } from "@/lib/status";
import PipelineFlow from "@/components/PipelineFlow";
import EventDetail from "@/components/EventDetail";

const RISK_BAND_ORDER = ["critical", "high", "medium", "low", "info"] as const;
const STREAM_FILTERS = [
  { key: "all", label: "All Events" },
  { key: "elevated", label: "High + Critical" },
  { key: "auth", label: "Auth Events" },
] as const;
type StreamFilter = (typeof STREAM_FILTERS)[number]["key"];

function useBackendHealth() {
  return useQuery({
    queryKey: ["health-pill"],
    queryFn: async () => (await axios.get("/health")).data as { status: string; database: string },
    refetchInterval: 20000,
    retry: false,
  });
}

export default function DashboardPage() {
  const qc = useQueryClient();
  const [eventId, setEventId] = useState<string | null>(null);
  const [streamFilter, setStreamFilter] = useState<StreamFilter>("all");

  const overview = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: analyticsOverview,
    refetchInterval: 10000,
  });
  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: () => listAlerts(),
    refetchInterval: 20000,
  });
  const stream = useQuery({
    queryKey: ["dashboard-stream"],
    queryFn: () => searchLogs({ limit: 15 }),
    refetchInterval: 15000,
  });
  const health = useBackendHealth();

  const d = overview.data;
  const items = alerts.data?.items ?? [];
  const active = items.filter((a) => !["RESOLVED", "FALSE_POSITIVE"].includes(a.status)).length;
  const highCrit = items.filter((a) => ["high", "critical"].includes(a.risk_breakdown.band)).length;
  const shieldFlags = d?.shield_events ?? 0;

  const streamRows = useMemo(() => {
    const rows = stream.data?.items ?? [];
    if (streamFilter === "elevated") return rows.filter((r) => ["high", "critical"].includes(r.severity ?? ""));
    if (streamFilter === "auth") return rows.filter((r) => (r.event_type ?? "").includes("auth"));
    return rows;
  }, [stream.data, streamFilter]);

  const riskBands = useMemo(() => {
    const series = d?.charts.risk_distribution ?? [];
    const map = new Map(series.map((s) => [s.label, s.value]));
    const total = series.reduce((a, s) => a + s.value, 0);
    return { total, entries: RISK_BAND_ORDER.map((band) => ({ band, count: map.get(band) ?? 0 })) };
  }, [d]);

  const topSources = useMemo(() => {
    const rows = d?.source_status ?? [];
    const total = rows.reduce((a, s) => a + s.events_processed, 0);
    return {
      total,
      rows: [...rows].sort((a, b) => b.events_processed - a.events_processed).slice(0, 5),
    };
  }, [d]);

  const refreshAll = () => {
    qc.invalidateQueries({ queryKey: ["analytics-overview"] });
    qc.invalidateQueries({ queryKey: ["analytics-pipeline"] });
    qc.invalidateQueries({ queryKey: ["alerts"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stream"] });
  };

  return (
    <div className="space-y-8">
      {/* ---------------------------------------------------------- sub-header */}
      <div className="surface bg-surface-sheen flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Command Center</h1>
            <span className="badge bg-slate-100 text-slate-600 ring-1 ring-slate-200 uppercase tracking-wider">
              Live Mode
            </span>
          </div>
          <p className="mt-1.5 max-w-2xl text-sm text-slate-500">
            Universal log preprocessing, cross-source correlation, and security intelligence — every figure
            below is queried live, nothing is simulated.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <LiveDot label={d ? `updated ${new Date(d.generated_at).toLocaleTimeString()}` : "Live"} />
          <button className="btn-ghost py-1.5 text-xs" onClick={refreshAll}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* ---------------------------------------------------------- KPI row */}
      {overview.isError ? (
        <ErrorState error={overview.error} onRetry={overview.refetch} />
      ) : (
        <KpiGrid>
          <Kpi
            label="Events processed"
            value={(d?.cards.processed ?? 0).toLocaleString()}
            tone="sky"
            icon={Database}
            loading={overview.isLoading}
          />
          <Kpi
            label="Events / sec"
            value={(d?.cards.avg_processing_rate ?? 0).toFixed(0)}
            sub={d ? `peak ${d.cards.peak_processing_rate.toFixed(0)}/s` : undefined}
            tone="blue"
            icon={Zap}
            loading={overview.isLoading}
          />
          <Kpi
            label="Active alerts"
            value={active}
            status={active ? "critical" : "safe"}
            icon={AlertTriangle}
            loading={alerts.isLoading}
          />
          <Kpi
            label="High / critical"
            value={highCrit}
            status={highCrit ? "critical" : "safe"}
            icon={AlertTriangle}
            loading={alerts.isLoading}
          />
          <Kpi
            label="Shield events"
            value={shieldFlags.toLocaleString()}
            status={shieldFlags > 0 ? "critical" : "safe"}
            icon={ShieldX}
            loading={overview.isLoading}
          />
          <Kpi label="Sources" value={d?.source_status.length ?? 0} tone="blue" icon={Database} loading={overview.isLoading} />
          <Kpi
            label="Normalized events"
            value={(d?.cards.normalized_events ?? 0).toLocaleString()}
            tone="violet"
            icon={Gauge}
            loading={overview.isLoading}
          />
          <Kpi
            label="Processing success"
            value={d ? `${d.processing_success_rate}%` : "—"}
            status={d ? (d.processing_success_rate >= 95 ? "safe" : d.processing_success_rate >= 80 ? "medium" : "high") : undefined}
            icon={ShieldCheck}
            loading={overview.isLoading}
          />
        </KpiGrid>
      )}

      {/* ---------------------------------------------------------- pipeline */}
      <PipelineFlow />

      {/* ---------------------------------------------------------- events + risk/health */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* LEFT (~60%): live event stream */}
        <div className="lg:col-span-7">
          <div className="surface bg-surface-sheen flex h-full flex-col p-6">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <SectionHeader title="Live Event Stream" hint="Real-time normalized events across every source" />
              <div className="flex items-center gap-1 rounded-lg bg-base-panel-2 p-1">
                {STREAM_FILTERS.map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setStreamFilter(f.key)}
                    className={`rounded-md px-2.5 py-1 text-2xs font-semibold transition-colors ${
                      streamFilter === f.key ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {stream.isLoading ? (
              <SkeletonTable rows={6} cols={6} />
            ) : stream.isError ? (
              <ErrorState error={stream.error} onRetry={stream.refetch} />
            ) : streamRows.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="No events yet"
                hint="Ingest a file or import a sample on the Ingestion page — new events will surface here automatically."
              />
            ) : (
              <>
                <DataTable>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Source</th>
                      <th>Event type</th>
                      <th>Host</th>
                      <th>Identity</th>
                      <th>Source IP</th>
                      <th>Severity</th>
                      <th className="text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {streamRows.map((e) => (
                      <tr key={e.id} className="clickable" onClick={() => setEventId(e.id)}>
                        <td className="whitespace-nowrap font-mono text-2xs text-slate-500" title={e.timestamp ?? ""}>
                          {relTime(e.timestamp)}
                        </td>
                        <td className="text-xs text-slate-700">{e.source}</td>
                        <td className="text-xs text-slate-800">{e.event_type ?? "—"}</td>
                        <td className="text-xs text-slate-500">{e.host ?? "—"}</td>
                        <td className="font-mono text-2xs text-slate-500">{e.username ?? e.email ?? "—"}</td>
                        <td className="font-mono text-2xs text-slate-500">{e.source_ip ?? "—"}</td>
                        <td>{e.severity ? <StatusPill status={e.severity} /> : "—"}</td>
                        <td className="text-right">
                          {e.processing_status ? <StatusPill status={e.processing_status} dot={false} /> : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </DataTable>
                <div className="mt-4 flex items-center justify-between text-2xs text-slate-500">
                  <span>
                    Displaying {streamRows.length} of {stream.data?.total.toLocaleString()} events
                  </span>
                  <div className="flex items-center gap-2">
                    <Link to="/alerts" className="btn-ghost py-1 text-2xs">
                      Review Alerts {active ? `(${active})` : ""}
                    </Link>
                    <Link to="/explorer" className="btn-primary py-1 text-2xs">
                      View in Log Explorer
                    </Link>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* RIGHT (~40%): risk spectrum + source activity + system health */}
        <div className="flex flex-col gap-6 lg:col-span-5">
          <div className="surface bg-surface-sheen p-6">
            <SectionHeader
              title="Risk Spectrum"
              hint={`Distribution of ${riskBands.total.toLocaleString()} analyzed alerts`}
              right={<PieChart className="h-4 w-4 text-slate-400" />}
            />
            {riskBands.total === 0 ? (
              <p className="text-xs text-slate-500">No alerts scored yet — nothing to distribute.</p>
            ) : (
              <div className="space-y-2">
                <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
                  {riskBands.entries.map(({ band, count }) =>
                    count > 0 ? (
                      <div
                        key={band}
                        style={{ width: `${(count / riskBands.total) * 100}%`, background: statusStyle(band).dot }}
                        title={`${count} ${band}`}
                      />
                    ) : null,
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-2xs text-slate-500">
                  {riskBands.entries.map(({ band, count }) => (
                    <span key={band} className="flex items-center gap-1 font-medium">
                      <span className="h-2 w-2 rounded-full" style={{ background: statusStyle(band).dot }} />
                      {count} {band}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="surface bg-surface-sheen p-6">
            <SectionHeader title="Source Activity" hint="Events processed by source" />
            {topSources.rows.length === 0 ? (
              <p className="text-xs text-slate-500">No sources configured yet.</p>
            ) : (
              <div className="space-y-3">
                {topSources.rows.map((s) => {
                  const pct = topSources.total > 0 ? (s.events_processed / topSources.total) * 100 : 0;
                  return (
                    <div key={s.name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-700">{s.name}</span>
                        <span className="font-mono text-2xs font-semibold text-slate-500">
                          {s.events_processed.toLocaleString()} ({pct.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full rounded-full bg-sky-500" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="surface bg-surface-sheen p-6">
            <SectionHeader title="System Health" right={<Terminal className="h-4 w-4 text-slate-400" />} />
            <div className="grid grid-cols-2 gap-3">
              <div className="surface-2 p-3">
                <div className="label">Backend</div>
                <StatusPill
                  status={health.isError ? "error" : health.data?.status === "ok" ? "online" : "processing"}
                  label={health.isLoading ? "connecting…" : health.isError ? "unreachable" : (health.data?.status ?? "—")}
                />
              </div>
              <div className="surface-2 p-3">
                <div className="label">Database</div>
                <div className="text-sm font-semibold text-slate-800">{health.data?.database ?? "—"}</div>
              </div>
              <div className="surface-2 p-3">
                <div className="label">Success rate</div>
                <div className="text-sm font-semibold text-slate-800">{d ? `${d.processing_success_rate}%` : "—"}</div>
              </div>
              <div className="surface-2 p-3">
                <div className="label">Shield events</div>
                <div className="text-sm font-semibold text-slate-800">{d?.shield_events.toLocaleString() ?? "—"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {eventId && <EventDetail eventId={eventId} onClose={() => setEventId(null)} />}
    </div>
  );
}
