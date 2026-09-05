import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listJobs } from "@/services/endpoints";
import {
  DataTable,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  Progress,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import JobDrawer from "@/components/JobDrawer";

function duration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.max(0, (e - s) / 1000);
  return sec < 60 ? `${sec.toFixed(1)}s` : `${(sec / 60).toFixed(1)}m`;
}

export default function ProcessingJobsPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const jobs = useQuery({
    queryKey: ["jobs-page"],
    queryFn: () => listJobs({ limit: 100 }),
    refetchInterval: (q) =>
      (q.state.data?.items ?? []).some((j) => ["RUNNING", "PENDING"].includes(j.status)) ? 900 : 6000,
  });

  const items = jobs.data?.items ?? [];
  const active = items.filter((j) => ["RUNNING", "PENDING"].includes(j.status)).length;
  const totalRecords = items.reduce((a, j) => a + j.total_records, 0);
  const totalErrors = items.reduce((a, j) => a + j.invalid_records + j.quarantined_records, 0);

  return (
    <div>
      <PageHeader
        eyebrow="System"
        title="Processing Jobs"
        subtitle="Every ingestion job and its per-record outcome. Progress bars show real completion; nothing is simulated."
        actions={<LiveDot />}
      />

      <div className="mb-5">
        <KpiGrid>
          <Kpi label="Jobs" value={items.length} loading={jobs.isLoading} />
          <Kpi label="Active" value={active} status={active ? "running" : "idle"} loading={jobs.isLoading} />
          <Kpi label="Records processed" value={totalRecords.toLocaleString()} loading={jobs.isLoading} />
          <Kpi
            label="Invalid / quarantined"
            value={totalErrors.toLocaleString()}
            status={totalErrors ? "medium" : "safe"}
            loading={jobs.isLoading}
          />
        </KpiGrid>
      </div>

      {jobs.isLoading ? (
        <SkeletonTable rows={8} cols={7} />
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={jobs.refetch} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No processing jobs yet"
          hint="Head to Ingestion to upload a file, import a sample, or generate a simulated stream."
        />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th>File</th>
              <th>Source</th>
              <th>Format</th>
              <th className="w-40">Progress</th>
              <th className="text-right">Records</th>
              <th className="text-right">Success</th>
              <th className="text-right">Errors</th>
              <th className="text-right">Rate</th>
              <th>Duration</th>
              <th>Started</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((j) => {
              const done =
                j.processed_records + j.invalid_records + j.duplicate_records + j.quarantined_records;
              const errs = j.invalid_records + j.quarantined_records;
              return (
                <tr key={j.id} className="clickable" onClick={() => setSelected(j.id)}>
                  <td className="max-w-[220px] truncate font-mono text-xs">{j.filename}</td>
                  <td className="text-xs text-gray-400">{j.source_name}</td>
                  <td>{j.detected_format ? <StatusPill status="info" label={j.detected_format} dot={false} /> : "—"}</td>
                  <td>
                    <Progress value={done} max={j.total_records || 1} />
                  </td>
                  <td className="text-right tnum">{j.total_records.toLocaleString()}</td>
                  <td className="text-right tnum text-emerald-300/90">{j.processed_records.toLocaleString()}</td>
                  <td className={`text-right tnum ${errs ? "text-amber-300" : "text-gray-500"}`}>{errs}</td>
                  <td className="text-right tnum text-gray-400">{j.processing_rate.toFixed(0)}/s</td>
                  <td className="text-xs text-gray-400">{duration(j.started_at, j.finished_at)}</td>
                  <td className="whitespace-nowrap text-xs text-gray-500">{relTime(j.created_at)}</td>
                  <td>
                    <StatusPill status={j.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      )}

      <JobDrawer jobId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
