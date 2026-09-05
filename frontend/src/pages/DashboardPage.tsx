import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Database, FileWarning, Files, Layers, ShieldX, Zap } from "lucide-react";
import { analyticsOverview, type AnalyticsOverview } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import { Badge, ErrorState, LiveDot, PageHeader, Spinner } from "@/components/ui";
import { BarSeries, ChartCard, DonutSeries, TimeSeries } from "@/components/charts";
import PipelineFlow from "@/components/PipelineFlow";

export default function DashboardPage() {
  const { user } = useAuth();
  const q = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: analyticsOverview,
    refetchInterval: 10000,
  });

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Signed in as ${user?.email} (${user?.role}). Every number on this page is queried live from the backend — nothing is hard-coded.`}
        actions={<LiveDot label={q.data ? `updated ${new Date(q.data.generated_at).toLocaleTimeString()}` : "Live"} />}
      />

      <div className="mb-6">
        <PipelineFlow />
      </div>

      {q.isLoading ? (
        <Spinner label="Loading dashboard…" />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <DashboardBody data={q.data!} />
      )}
    </div>
  );
}

function DashboardBody({ data: d }: { data: AnalyticsOverview }) {
  const cards = [
    { label: "Total Logs", value: d.cards.total_logs, icon: Files },
    { label: "Processed", value: d.cards.processed, icon: Layers },
    { label: "Invalid", value: d.cards.invalid, icon: FileWarning },
    { label: "Duplicates", value: d.cards.duplicates, icon: Files },
    { label: "Quarantined", value: d.cards.quarantined, icon: ShieldX },
    { label: "Normalized Events", value: d.cards.normalized_events, icon: Database },
    { label: "Alerts", value: d.cards.alerts, icon: AlertTriangle },
    {
      label: "Processing Rate",
      value: `${d.cards.avg_processing_rate.toFixed(0)}/s`,
      sub: `peak ${d.cards.peak_processing_rate.toFixed(0)}/s`,
      icon: Zap,
    },
  ];

  const hasAnyData = d.cards.total_logs > 0;

  return (
    <>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="card transition hover:border-brand/40">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-gray-400">{c.label}</span>
              <c.icon className="h-4 w-4 text-gray-600" />
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{c.value}</div>
            {c.sub && <div className="text-xs text-gray-500">{c.sub}</div>}
          </div>
        ))}
      </div>

      <div className="mb-3 flex flex-wrap gap-4 text-xs text-gray-400">
        <span>
          Processing success rate:{" "}
          <span className="font-semibold text-gray-200">{d.processing_success_rate}%</span>
        </span>
        <span>
          Security-shield events:{" "}
          <span className="font-semibold text-gray-200">{d.shield_events}</span>
        </span>
      </div>

      {!hasAnyData && (
        <div className="mb-6 rounded-lg border border-dashed border-base-border p-6 text-center">
          <p className="text-sm text-gray-300">No logs ingested yet.</p>
          <p className="mt-1 text-xs text-gray-500">
            Go to <b>Ingestion</b> to upload a file, import a synthetic sample, or run the SIH Demo.
          </p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Events over time">
          <TimeSeries data={d.charts.events_over_time} />
        </ChartCard>
        <ChartCard title="Logs by source">
          <BarSeries data={d.charts.logs_by_source} />
        </ChartCard>
        <ChartCard title="Logs by format">
          <BarSeries data={d.charts.logs_by_format} />
        </ChartCard>
        <ChartCard title="Events by severity">
          <DonutSeries data={d.charts.events_by_severity} />
        </ChartCard>
        <ChartCard title="Events by type">
          <BarSeries data={d.charts.events_by_type} />
        </ChartCard>
        <ChartCard title="Processing outcomes">
          <DonutSeries data={d.charts.processing_outcomes} />
        </ChartCard>
        <ChartCard title="PII transformations">
          <DonutSeries data={d.charts.pii_transformations} />
        </ChartCard>
        <ChartCard title="Alerts by severity">
          <BarSeries data={d.charts.alerts_by_severity} colorByLabel />
        </ChartCard>
        <ChartCard title="Risk distribution">
          <BarSeries data={d.charts.risk_distribution} colorByLabel />
        </ChartCard>
      </div>

      <h2 className="mb-2 mt-8 text-sm font-semibold text-gray-300">Source status</h2>
      {d.source_status.length === 0 ? (
        <p className="text-sm text-gray-500">
          No sources yet — upload a file or import a sample on the Ingestion page.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Category</th>
                <th className="py-2 pr-4">Adapter</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Events</th>
                <th className="py-2 pr-4">Last received</th>
              </tr>
            </thead>
            <tbody>
              {d.source_status.map((s) => (
                <tr key={s.name} className="border-t border-base-border">
                  <td className="py-2 pr-4 font-medium">{s.name}</td>
                  <td className="py-2 pr-4 text-gray-400">{s.category}</td>
                  <td className="py-2 pr-4">{s.adapter}</td>
                  <td className="py-2 pr-4">
                    <Badge tone={s.status === "RECEIVING" ? "green" : "slate"}>{s.status}</Badge>
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{s.events_processed}</td>
                  <td className="py-2 pr-4 text-gray-400">
                    {s.last_received ? new Date(s.last_received).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
