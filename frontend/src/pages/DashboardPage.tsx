import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, Database, Gauge, ShieldCheck, ShieldX, Zap } from "lucide-react";
import { analyticsOverview, listAlerts, searchLogs } from "@/services/endpoints";
import {
  DataTable,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  SectionHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import PipelineFlow from "@/components/PipelineFlow";
import EventDetail from "@/components/EventDetail";

export default function DashboardPage() {
  const [eventId, setEventId] = useState<string | null>(null);

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
    queryFn: () => searchLogs({ limit: 12 }),
    refetchInterval: 15000,
  });

  const d = overview.data;
  const items = alerts.data?.items ?? [];
  const active = items.filter((a) => !["RESOLVED", "FALSE_POSITIVE"].includes(a.status)).length;
  const highCrit = items.filter((a) => ["high", "critical"].includes(a.risk_breakdown.band)).length;

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="ULPF Command Center"
        subtitle="Universal log preprocessing, correlation and security intelligence. Every figure on this page is queried live — nothing is hard-coded or simulated."
        actions={
          <LiveDot
            label={d ? `updated ${new Date(d.generated_at).toLocaleTimeString()}` : "Live"}
          />
        }
      />

      <div className="mb-6">
        {overview.isError ? (
          <ErrorState error={overview.error} onRetry={overview.refetch} />
        ) : (
          <KpiGrid>
            <Kpi label="Events processed" value={(d?.cards.processed ?? 0).toLocaleString()} icon={Database} loading={overview.isLoading} />
            <Kpi
              label="Events / sec"
              value={(d?.cards.avg_processing_rate ?? 0).toFixed(0)}
              sub={d ? `peak ${d.cards.peak_processing_rate.toFixed(0)}/s` : undefined}
              icon={Zap}
              loading={overview.isLoading}
            />
            <Kpi
              label="Active alerts"
              value={active}
              status={active ? "investigating" : "safe"}
              icon={AlertTriangle}
              loading={alerts.isLoading}
            />
            <Kpi
              label="High / critical"
              value={highCrit}
              status={highCrit ? "high" : "safe"}
              icon={AlertTriangle}
              loading={alerts.isLoading}
            />
            <Kpi
              label="Shield events"
              value={(d?.shield_events ?? 0).toLocaleString()}
              status={(d?.shield_events ?? 0) > 0 ? "medium" : "safe"}
              icon={ShieldX}
              loading={overview.isLoading}
            />
            <Kpi label="Sources" value={d?.source_status.length ?? 0} icon={Database} loading={overview.isLoading} />
            <Kpi label="Normalized events" value={(d?.cards.normalized_events ?? 0).toLocaleString()} icon={Gauge} loading={overview.isLoading} />
            <Kpi
              label="Processing success"
              value={d ? `${d.processing_success_rate}%` : "—"}
              status={d ? (d.processing_success_rate >= 95 ? "safe" : d.processing_success_rate >= 80 ? "medium" : "high") : undefined}
              icon={ShieldCheck}
              loading={overview.isLoading}
            />
          </KpiGrid>
        )}
      </div>

      <div className="mb-6">
        <PipelineFlow />
      </div>

      <div>
        <SectionHeader
          title="Live event stream"
          hint="The most recent normalized events across every source"
          right={
            <Link to="/explorer" className="text-2xs text-brand-fg hover:underline">
              Open Log Explorer →
            </Link>
          }
        />
        {stream.isLoading ? (
          <SkeletonTable rows={6} cols={6} />
        ) : stream.isError ? (
          <ErrorState error={stream.error} onRetry={stream.refetch} />
        ) : (stream.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            icon={Activity}
            title="No events yet"
            hint="Ingest a file or import a sample on the Ingestion page — new events will surface here automatically."
          />
        ) : (
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
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {stream.data!.items.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => setEventId(e.id)}>
                  <td className="whitespace-nowrap text-xs text-gray-400" title={e.timestamp ?? ""}>
                    {relTime(e.timestamp)}
                  </td>
                  <td className="text-xs text-gray-300">{e.source}</td>
                  <td className="text-xs">{e.event_type ?? "—"}</td>
                  <td className="text-xs text-gray-400">{e.host ?? "—"}</td>
                  <td className="font-mono text-2xs text-gray-400">{e.username ?? e.email ?? "—"}</td>
                  <td className="font-mono text-2xs text-gray-400">{e.source_ip ?? "—"}</td>
                  <td>{e.severity ? <StatusPill status={e.severity} /> : "—"}</td>
                  <td>{e.processing_status ? <StatusPill status={e.processing_status} dot={false} /> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </div>

      {eventId && <EventDetail eventId={eventId} onClose={() => setEventId(null)} />}
    </div>
  );
}
