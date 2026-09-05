import { useQuery } from "@tanstack/react-query";
import { analyticsOverview, type AnalyticsOverview } from "@/services/endpoints";
import {
  DataTable,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import { BarSeries, ChartCard, DonutSeries, TimeSeries } from "@/components/charts";

export default function AnalyticsPage() {
  const q = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: analyticsOverview,
    refetchInterval: 30000,
  });

  return (
    <div>
      <PageHeader
        eyebrow="Intelligence"
        title="Analytics"
        subtitle="Aggregate view of ingestion, normalization, privacy and detection. Every series is computed from stored events — empty charts mean no data, not an error."
        actions={
          <LiveDot
            label={q.data ? `updated ${new Date(q.data.generated_at).toLocaleTimeString()}` : "Live"}
          />
        }
      />

      {q.isLoading ? (
        <div className="space-y-4">
          <SkeletonTable rows={2} cols={4} />
          <SkeletonTable rows={4} cols={3} />
        </div>
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <Body d={q.data!} />
      )}
    </div>
  );
}

function Body({ d }: { d: AnalyticsOverview }) {
  const hasData = d.cards.total_logs > 0;

  return (
    <>
      <div className="mb-5">
        <KpiGrid>
          <Kpi label="Total logs" value={d.cards.total_logs.toLocaleString()} />
          <Kpi label="Normalized events" value={d.cards.normalized_events.toLocaleString()} />
          <Kpi
            label="Processing success"
            value={`${d.processing_success_rate}%`}
            status={d.processing_success_rate >= 95 ? "safe" : d.processing_success_rate >= 80 ? "medium" : "high"}
          />
          <Kpi
            label="Shield events"
            value={d.shield_events.toLocaleString()}
            status={d.shield_events ? "medium" : "safe"}
          />
          <Kpi label="Invalid" value={d.cards.invalid.toLocaleString()} status={d.cards.invalid ? "medium" : "safe"} />
          <Kpi label="Duplicates" value={d.cards.duplicates.toLocaleString()} />
          <Kpi label="Quarantined" value={d.cards.quarantined.toLocaleString()} status={d.cards.quarantined ? "high" : "safe"} />
          <Kpi
            label="Avg / peak rate"
            value={`${d.cards.avg_processing_rate.toFixed(0)}/s`}
            sub={`peak ${d.cards.peak_processing_rate.toFixed(0)}/s`}
          />
        </KpiGrid>
      </div>

      {!hasData && (
        <EmptyState
          title="No analytics yet"
          hint="Ingest a file or import a sample on the Ingestion page to populate these charts."
        />
      )}

      {hasData && (
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
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold text-gray-200">Source status</h2>
      {d.source_status.length === 0 ? (
        <EmptyState title="No sources yet" hint="Upload a file or import a sample on the Ingestion page." />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th>Source</th>
              <th>Category</th>
              <th>Adapter</th>
              <th>Status</th>
              <th className="text-right">Events</th>
              <th>Last received</th>
            </tr>
          </thead>
          <tbody>
            {d.source_status.map((s) => (
              <tr key={s.name}>
                <td className="font-medium text-gray-200">{s.name}</td>
                <td className="text-gray-400">{s.category}</td>
                <td className="text-gray-400">{s.adapter}</td>
                <td>
                  <StatusPill status={s.status} />
                </td>
                <td className="text-right tnum">{s.events_processed.toLocaleString()}</td>
                <td className="text-xs text-gray-500">{relTime(s.last_received)}</td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </>
  );
}
