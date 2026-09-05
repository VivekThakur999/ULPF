import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { FileUp, FlaskConical, PlayCircle } from "lucide-react";
import { importSample, listJobs, listSamples, simulateStream, uploadLog } from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  LiveDot,
  PageHeader,
  Progress,
  SectionHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import JobDrawer from "@/components/JobDrawer";

export default function IngestionPage() {
  const { hasRole } = useAuth();
  const canIngest = hasRole("ANALYST");
  const qc = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs({ limit: 15 }),
    refetchInterval: (q) =>
      (q.state.data?.items ?? []).some((j) => j.status === "RUNNING" || j.status === "PENDING") ? 800 : 5000,
  });

  const afterIngest = () => {
    setErr("");
    qc.invalidateQueries({ queryKey: ["jobs"] });
    qc.invalidateQueries({ queryKey: ["jobs-page"] });
  };

  return (
    <div>
      <PageHeader
        eyebrow="Pipeline"
        title="Ingestion"
        subtitle="Upload a log file, import a bundled synthetic sample, or generate a simulated stream. Every record is preserved verbatim, then run through the pre-processing pipeline."
      />

      {err && (
        <div className="mb-4">
          <ErrorState error={err} />
        </div>
      )}

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

      <SectionHeader
        title="Recent jobs"
        right={
          <div className="flex items-center gap-3">
            <LiveDot />
            <Link to="/jobs" className="text-2xs text-brand-fg hover:underline">
              All jobs →
            </Link>
          </div>
        }
      />
      {jobs.isLoading ? (
        <SkeletonTable rows={5} cols={6} />
      ) : jobs.isError ? (
        <ErrorState error={jobs.error} onRetry={jobs.refetch} />
      ) : jobs.data && jobs.data.items.length > 0 ? (
        <DataTable>
          <thead>
            <tr>
              <th>File</th>
              <th>Source</th>
              <th>Format</th>
              <th className="w-40">Progress</th>
              <th className="text-right">Records</th>
              <th className="text-right">Errors</th>
              <th>Started</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {jobs.data.items.map((j) => {
              const done = j.processed_records + j.invalid_records + j.duplicate_records + j.quarantined_records;
              const errs = j.invalid_records + j.quarantined_records;
              return (
                <tr key={j.id} className="clickable" onClick={() => setSelectedJob(j.id)}>
                  <td className="max-w-[200px] truncate font-mono text-xs">{j.filename}</td>
                  <td className="text-xs text-gray-400">{j.source_name}</td>
                  <td>{j.detected_format ? <StatusPill status="info" label={j.detected_format} dot={false} /> : "—"}</td>
                  <td>
                    <Progress value={done} max={j.total_records || 1} />
                  </td>
                  <td className="text-right tnum">{j.total_records.toLocaleString()}</td>
                  <td className={`text-right tnum ${errs ? "text-amber-300" : "text-gray-500"}`}>{errs}</td>
                  <td className="whitespace-nowrap text-xs text-gray-500">{relTime(j.created_at)}</td>
                  <td>
                    <StatusPill status={j.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      ) : (
        <EmptyState title="No ingestion jobs yet" hint="Upload a file or import a sample to get started." />
      )}

      <JobDrawer jobId={selectedJob} onClose={() => setSelectedJob(null)} />
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
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-200">
        <FileUp className="h-4 w-4 text-brand-fg" /> Upload file
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
      <p className="mt-2 text-2xs text-gray-600">.log .txt .json .jsonl .csv .syslog · max 50 MB</p>
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
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-200">
        <FlaskConical className="h-4 w-4 text-brand-fg" /> Import synthetic sample
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
        Import &amp; process
      </button>
      <p className="mt-2 text-2xs text-gray-600">Bundled datasets are clearly synthetic / demo data.</p>
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
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-200">
        <PlayCircle className="h-4 w-4 text-brand-fg" /> Simulated stream
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
        Generate &amp; process
      </button>
      <p className="mt-2 text-2xs text-gray-600">Synthetic sshd/apache lines from the SIMULATED adapter.</p>
    </Card>
  );
}
