import { type ReactNode, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getJob, getJobRecords } from "@/services/endpoints";
import { Drawer, Progress, Spinner, StatusPill, Tabs, bytes } from "@/components/ui";
import { statusStyle } from "@/lib/status";
import type { ProcessingJob, RawLogRecord } from "@/types";

type JobTab = "summary" | "QUARANTINED" | "INVALID";

function str(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

export default function JobDrawer({ jobId, onClose }: { jobId: string | null; onClose: () => void }) {
  const [tab, setTab] = useState<JobTab>("summary");

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) =>
      q.state.data && ["RUNNING", "PENDING"].includes(q.state.data.status) ? 800 : false,
  });

  const records = useQuery({
    queryKey: ["job-records", jobId, tab],
    queryFn: () =>
      getJobRecords(jobId as string, { status: tab === "summary" ? undefined : tab, limit: 100 }),
    enabled: !!jobId && tab !== "summary",
  });

  return (
    <Drawer
      open={!!jobId}
      onClose={onClose}
      title={job.data?.filename ?? "Processing job"}
      subtitle={jobId ? `Job ${jobId.slice(0, 8)}` : undefined}
      actions={job.data && <StatusPill status={job.data.status} />}
    >
      {job.isLoading || !job.data ? (
        <Spinner />
      ) : (
        <JobBody
          job={job.data}
          tab={tab}
          setTab={setTab}
          records={(records.data as RawLogRecord[] | undefined) ?? []}
          recordsLoading={records.isLoading}
        />
      )}
    </Drawer>
  );
}

function JobBody({
  job,
  tab,
  setTab,
  records,
  recordsLoading,
}: {
  job: ProcessingJob;
  tab: JobTab;
  setTab: (t: JobTab) => void;
  records: RawLogRecord[];
  recordsLoading: boolean;
}) {
  const done =
    job.processed_records + job.invalid_records + job.duplicate_records + job.quarantined_records;
  const stats = job.stats ?? {};

  const cards: { k: string; v: ReactNode; tone?: string }[] = [
    { k: "Total", v: job.total_records },
    { k: "Processed", v: job.processed_records, tone: "safe" },
    { k: "Invalid", v: job.invalid_records, tone: job.invalid_records ? "medium" : undefined },
    { k: "Duplicates", v: job.duplicate_records, tone: job.duplicate_records ? "medium" : undefined },
    { k: "Quarantined", v: job.quarantined_records, tone: job.quarantined_records ? "high" : undefined },
    { k: "Rate", v: `${job.processing_rate.toFixed(0)}/s` },
  ];

  return (
    <div>
      <div className="mb-4">
        <div className="mb-1 flex justify-between text-2xs text-gray-500">
          <span>progress</span>
          <span className="tnum">
            {done} / {job.total_records || "?"}
          </span>
        </div>
        <Progress value={done} max={job.total_records || 1} />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {cards.map((c) => (
          <div key={c.k} className="surface-2 p-2.5 text-center">
            <div className="text-2xs uppercase tracking-wide text-gray-500">{c.k}</div>
            <div
              className="mt-0.5 text-lg font-semibold tnum"
              style={c.tone ? { color: statusStyle(c.tone).dot } : undefined}
            >
              {c.v}
            </div>
          </div>
        ))}
      </div>

      <dl className="mt-4 space-y-1 text-sm">
        <Row k="Detected format" v={str(job.detected_format)} />
        <Row k="Declared format" v={str(job.declared_format)} />
        <Row k="Source" v={job.source_name} />
        <Row k="Security events" v={str(stats.security_events)} />
        <Row k="Blank lines skipped" v={str(stats.blank_lines)} />
        <Row k="Elapsed" v={stats.elapsed_seconds != null ? `${str(stats.elapsed_seconds)} s` : "—"} />
        <Row k="Bytes" v={typeof stats.bytes === "number" ? bytes(stats.bytes) : "—"} />
        {job.error && <Row k="Error" v={<span className="text-sev-critical">{job.error}</span>} />}
      </dl>

      <div className="mt-5">
        <Tabs<JobTab>
          tabs={[
            { key: "summary", label: "Summary" },
            { key: "QUARANTINED", label: `Quarantined (${job.quarantined_records})` },
            { key: "INVALID", label: `Invalid (${job.invalid_records})` },
          ]}
          value={tab}
          onChange={setTab}
        />
      </div>

      {tab !== "summary" && (
        <div className="mt-3 space-y-2">
          {recordsLoading ? (
            <Spinner />
          ) : records.length === 0 ? (
            <p className="py-4 text-sm text-gray-500">No {tab.toLowerCase()} records.</p>
          ) : (
            records.map((r) => (
              <div key={r.id} className="surface-2 p-2.5 text-xs">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="text-gray-500">line {r.line_number}</span>
                  <StatusPill status={r.status} />
                  <StatusPill status={r.security_verdict === "SAFE" ? "safe" : r.security_verdict} />
                </div>
                <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-2xs text-slate-800">
                  {r.content}
                </pre>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-base-border/50 py-1.5">
      <dt className="text-gray-500">{k}</dt>
      <dd className="text-right text-slate-800">{v}</dd>
    </div>
  );
}
