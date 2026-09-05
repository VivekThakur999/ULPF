import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, FlaskConical, PlayCircle } from "lucide-react";
import {
  getJob,
  getJobRecords,
  importSample,
  listJobs,
  listSamples,
  simulateStream,
  uploadLog,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LiveDot,
  PageHeader,
  Progress,
  Spinner,
  bytes,
  statusTone,
} from "@/components/ui";
import type { ProcessingJob } from "@/types";

export default function IngestionPage() {
  const { hasRole } = useAuth();
  const canIngest = hasRole("ANALYST");
  const qc = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs({ limit: 50 }),
    refetchInterval: (q) =>
      (q.state.data?.items ?? []).some((j) => j.status === "RUNNING" || j.status === "PENDING")
        ? 800
        : 5000,
  });

  const afterIngest = () => {
    setErr("");
    qc.invalidateQueries({ queryKey: ["jobs"] });
  };

  return (
    <div>
      <PageHeader
        title="Ingestion"
        subtitle="Upload a log file, import a bundled synthetic sample, or generate a simulated stream. Every record is preserved verbatim, then run through the pre-processing pipeline."
      />

      {err && <div className="mb-4"><ErrorState error={err} /></div>}

      {canIngest ? (
        <div className="mb-8 grid gap-4 lg:grid-cols-3">
          <UploadCard onError={setErr} onDone={afterIngest} />
          <SampleCard onError={setErr} onDone={afterIngest} />
          <SimulateCard onError={setErr} onDone={afterIngest} />
        </div>
      ) : (
        <Card className="mb-8">
          <p className="text-sm text-gray-400">
            You have read-only (VIEWER) access. Ingestion requires the ANALYST role.
          </p>
        </Card>
      )}

      <div className="mb-2 flex items-center gap-3">
        <h2 className="text-sm font-semibold text-gray-300">Processing jobs</h2>
        <LiveDot />
      </div>
      {jobs.isLoading ? (
        <Spinner />
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={jobs.refetch} />
      ) : jobs.data && jobs.data.items.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2 pr-4">Job</th>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Format</th>
                <th className="py-2 pr-4">Progress</th>
                <th className="py-2 pr-4">Processed</th>
                <th className="py-2 pr-4">Invalid</th>
                <th className="py-2 pr-4">Dup</th>
                <th className="py-2 pr-4">Quarantined</th>
                <th className="py-2 pr-4">Rate</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.data.items.map((j) => (
                <tr
                  key={j.id}
                  className="cursor-pointer border-t border-base-border hover:bg-white/5"
                  onClick={() => setSelectedJob(j.id)}
                >
                  <td className="py-2 pr-4 font-mono text-xs">{j.filename}</td>
                  <td className="py-2 pr-4">{j.source_name}</td>
                  <td className="py-2 pr-4">
                    {j.detected_format ? <Badge tone="blue">{j.detected_format}</Badge> : "—"}
                  </td>
                  <td className="w-40 py-2 pr-4">
                    <Progress value={j.processed_records + j.invalid_records + j.duplicate_records + j.quarantined_records} max={j.total_records || 1} />
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{j.processed_records}</td>
                  <td className="py-2 pr-4 tabular-nums">{j.invalid_records}</td>
                  <td className="py-2 pr-4 tabular-nums">{j.duplicate_records}</td>
                  <td className="py-2 pr-4 tabular-nums">{j.quarantined_records}</td>
                  <td className="py-2 pr-4 tabular-nums">{j.processing_rate.toFixed(0)}/s</td>
                  <td className="py-2 pr-4">
                    <Badge tone={statusTone(j.status)}>{j.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No ingestion jobs yet" hint="Upload a file or import a sample to get started." />
      )}

      {selectedJob && <JobDrawer jobId={selectedJob} onClose={() => setSelectedJob(null)} />}
    </div>
  );
}

function UploadCard({ onError, onDone }: { onError: (s: string) => void; onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [sourceName, setSourceName] = useState("upload");
  const m = useMutation({
    mutationFn: (file: File) => uploadLog(file, sourceName),
    onSuccess: onDone,
    onError: (e) => onError(apiError(e)),
  });
  return (
    <Card>
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        <FileUp className="h-4 w-4" /> Upload file
      </div>
      <label className="label">Source name</label>
      <input className="input mb-2" value={sourceName} onChange={(e) => setSourceName(e.target.value)} />
      <input
        ref={fileRef}
        type="file"
        accept=".log,.txt,.json,.jsonl,.ndjson,.csv,.syslog"
        className="block w-full text-xs text-gray-400 file:mr-3 file:rounded file:border-0 file:bg-brand file:px-3 file:py-1.5 file:text-white"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) m.mutate(f);
        }}
      />
      {m.isPending && <p className="mt-2 text-xs text-gray-400">Uploading…</p>}
      <p className="mt-2 text-xs text-gray-600">.log .txt .json .jsonl .csv .syslog · max 50 MB</p>
    </Card>
  );
}

function SampleCard({ onError, onDone }: { onError: (s: string) => void; onDone: () => void }) {
  const samples = useQuery({ queryKey: ["samples"], queryFn: listSamples });
  const [path, setPath] = useState("");
  const m = useMutation({
    mutationFn: () => importSample(path),
    onSuccess: onDone,
    onError: (e) => onError(apiError(e)),
  });
  const grouped = useMemo(() => {
    const g: Record<string, string[]> = {};
    for (const s of samples.data?.samples ?? []) (g[s.category] ??= []).push(s.path);
    return g;
  }, [samples.data]);

  return (
    <Card>
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        <FlaskConical className="h-4 w-4" /> Import synthetic sample
      </div>
      <select className="input mb-2" value={path} onChange={(e) => setPath(e.target.value)}>
        <option value="">Select a sample…</option>
        {Object.entries(grouped).map(([cat, paths]) => (
          <optgroup key={cat} label={cat}>
            {paths.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <button className="btn-primary w-full justify-center" disabled={!path || m.isPending} onClick={() => m.mutate()}>
        Import & process
      </button>
      <p className="mt-2 text-xs text-gray-600">Bundled datasets are clearly synthetic / demo data.</p>
    </Card>
  );
}

function SimulateCard({ onError, onDone }: { onError: (s: string) => void; onDone: () => void }) {
  const [count, setCount] = useState(30);
  const m = useMutation({
    mutationFn: () => simulateStream({ count }),
    onSuccess: onDone,
    onError: (e) => onError(apiError(e)),
  });
  return (
    <Card>
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        <PlayCircle className="h-4 w-4" /> Simulated stream
      </div>
      <label className="label">Record count</label>
      <input
        type="number"
        className="input mb-2"
        value={count}
        min={1}
        max={2000}
        onChange={(e) => setCount(Number(e.target.value))}
      />
      <button className="btn-primary w-full justify-center" disabled={m.isPending} onClick={() => m.mutate()}>
        Generate & process
      </button>
      <p className="mt-2 text-xs text-gray-600">Synthetic sshd/apache lines from the SIMULATED adapter.</p>
    </Card>
  );
}

function JobDrawer({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (q) =>
      q.state.data && (q.state.data.status === "RUNNING" || q.state.data.status === "PENDING")
        ? 800
        : false,
  });
  const [tab, setTab] = useState<"summary" | "QUARANTINED" | "INVALID">("summary");
  const records = useQuery({
    queryKey: ["job-records", jobId, tab],
    queryFn: () => getJobRecords(jobId, { status: tab === "summary" ? undefined : tab, limit: 100 }),
    enabled: tab !== "summary",
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <div
        className="h-full w-full max-w-xl overflow-y-auto border-l border-base-border bg-base-panel p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {job.isLoading || !job.data ? (
          <Spinner />
        ) : (
          <JobDetail job={job.data} tab={tab} setTab={setTab} records={records.data ?? []} onClose={onClose} />
        )}
      </div>
    </div>
  );
}

function JobDetail({
  job,
  tab,
  setTab,
  records,
  onClose,
}: {
  job: ProcessingJob;
  tab: "summary" | "QUARANTINED" | "INVALID";
  setTab: (t: "summary" | "QUARANTINED" | "INVALID") => void;
  records: { id: string; line_number: number; content: string; security_verdict: string; status: string }[];
  onClose: () => void;
}) {
  return (
    <div>
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="font-semibold">{job.filename}</h2>
          <p className="text-xs text-gray-500">Job {job.id}</p>
        </div>
        <button className="btn-ghost py-1 text-xs" onClick={onClose}>
          Close
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center text-sm">
        {[
          ["Total", job.total_records],
          ["Processed", job.processed_records],
          ["Invalid", job.invalid_records],
          ["Duplicates", job.duplicate_records],
          ["Quarantined", job.quarantined_records],
          ["Rate", `${job.processing_rate.toFixed(0)}/s`],
        ].map(([k, v]) => (
          <div key={k as string} className="rounded-md border border-base-border p-2">
            <div className="text-xs uppercase text-gray-500">{k}</div>
            <div className="mt-0.5 font-semibold tabular-nums">{v}</div>
          </div>
        ))}
      </div>

      <dl className="mt-4 space-y-1 text-sm">
        <Row k="Status" v={<Badge tone={statusTone(job.status)}>{job.status}</Badge>} />
        <Row k="Detected format" v={job.detected_format ?? "—"} />
        <Row k="Declared format" v={job.declared_format ?? "—"} />
        <Row k="Security events" v={String(job.stats?.security_events ?? 0)} />
        <Row k="Blank lines skipped" v={String(job.stats?.blank_lines ?? 0)} />
        <Row k="Elapsed" v={`${job.stats?.elapsed_seconds ?? "?"} s`} />
        <Row k="Bytes" v={typeof job.stats?.bytes === "number" ? bytes(job.stats.bytes) : "—"} />
        {job.error && <Row k="Error" v={<span className="text-sev-critical">{job.error}</span>} />}
      </dl>

      <div className="mt-5 flex gap-2 border-b border-base-border text-sm">
        {(["summary", "QUARANTINED", "INVALID"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-2 py-1.5 ${tab === t ? "border-b-2 border-brand text-brand-fg" : "text-gray-400"}`}
          >
            {t === "summary" ? "Summary" : t}
          </button>
        ))}
      </div>

      {tab !== "summary" && (
        <div className="mt-3 space-y-2">
          {records.length === 0 ? (
            <p className="text-sm text-gray-500">No {tab.toLowerCase()} records.</p>
          ) : (
            records.map((r) => (
              <div key={r.id} className="rounded border border-base-border p-2 text-xs">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-gray-500">line {r.line_number}</span>
                  <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                  <Badge tone={r.security_verdict === "SAFE" ? "green" : "amber"}>
                    {r.security_verdict}
                  </Badge>
                </div>
                <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px] text-gray-300">
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

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-base-border/50 py-1">
      <dt className="text-gray-500">{k}</dt>
      <dd className="text-right">{v}</dd>
    </div>
  );
}
