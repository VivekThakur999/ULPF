import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PlayCircle } from "lucide-react";
import {
  listCompressionRecords,
  runBenchmark,
  searchLogs,
  type BenchmarkResult,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { Card, DataTable, EmptyState, ErrorState, PageHeader, SectionHeader, Spinner, bytes, relTime } from "@/components/ui";
import TemplateCompressionFlow from "@/components/TemplateCompressionFlow";

export default function CompressionPage() {
  const { hasRole } = useAuth();
  const [source, setSource] = useState("");
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [err, setErr] = useState("");

  const bench = useMutation({
    mutationFn: () => runBenchmark({ source: source || undefined }),
    onSuccess: (r) => {
      setErr("");
      setResult(r);
      history.refetch();
    },
    onError: (e) => setErr(apiError(e)),
  });

  const history = useQuery({ queryKey: ["compression-records"], queryFn: listCompressionRecords });

  // one real record to demonstrate the round-trip
  const sampleRecord = useQuery({
    queryKey: ["compression-sample", source],
    queryFn: () => searchLogs({ source: source || undefined, limit: 1 }),
  });
  const sampleRawId = sampleRecord.data?.items[0]?.raw_log_id ?? null;

  return (
    <div>
      <PageHeader
        eyebrow="Pipeline"
        title="Compression"
        subtitle="Template-based micro-compression. A record is stored as a template reference plus its variable values; every reported number is measured, and every record is verified to reconstruct byte-for-byte."
        actions={
          hasRole("ANALYST") && (
            <div className="flex items-center gap-2">
              <input
                className="input w-40 py-1.5 text-xs"
                placeholder="source filter (opt.)"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
              <button className="btn-primary" disabled={bench.isPending} onClick={() => bench.mutate()}>
                <PlayCircle className={`h-4 w-4 ${bench.isPending ? "animate-pulse" : ""}`} />
                Run benchmark
              </button>
            </div>
          )
        }
      />

      {err && <div className="mb-4"><ErrorState error={err} /></div>}

      {bench.isPending && <Spinner label="Compressing & verifying every record…" />}

      {result && <BenchmarkPanel r={result} />}

      {!result && !bench.isPending && (
        <Card className="mb-6">
          <p className="text-sm text-gray-400">
            {hasRole("ANALYST")
              ? "Run a benchmark to measure compression over the ingested raw logs. Mining runs automatically first."
              : "No benchmark has been run yet. Ask an analyst to run one."}
          </p>
        </Card>
      )}

      <div className="mt-6">
        <SectionHeader title="Template → compression → reconstruction" />
      </div>
      {sampleRawId ? (
        <TemplateCompressionFlow rawLogId={sampleRawId} />
      ) : (
        <Card>
          <p className="text-sm text-gray-500">
            Ingest logs {source && `for source “${source}” `}to see a live round-trip walkthrough.
          </p>
        </Card>
      )}

      <div className="mt-8">
        <SectionHeader title="Benchmark history" />
      </div>
      {history.isLoading ? (
        <Spinner />
      ) : history.isError ? (
        <ErrorState error={history.error} onRetry={history.refetch} />
      ) : (history.data ?? []).length === 0 ? (
        <EmptyState title="No benchmark runs recorded yet" hint="Run a benchmark above to measure compression." />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th>When</th>
              <th>Scope</th>
              <th className="text-right">Records</th>
              <th className="text-right">Reconstructed</th>
              <th className="text-right">Original</th>
              <th className="text-right">Compressed</th>
              <th className="text-right">Savings</th>
            </tr>
          </thead>
          <tbody>
            {history.data!.map((rec) => (
              <tr key={rec.id}>
                <td className="whitespace-nowrap text-xs text-gray-400">{relTime(rec.ts)}</td>
                <td className="font-mono text-xs">{rec.scope}</td>
                <td className="text-right tnum">{rec.record_count}</td>
                <td className="text-right tnum">
                  {rec.reconstructable_count === rec.record_count ? (
                    <span className="text-emerald-400">{rec.reconstructable_count} ✓</span>
                  ) : (
                    <span className="text-sev-critical">
                      {rec.reconstructable_count}/{rec.record_count}
                    </span>
                  )}
                </td>
                <td className="text-right tnum">{bytes(rec.original_bytes)}</td>
                <td className="text-right tnum">{bytes(rec.total_compressed_bytes)}</td>
                <td className={`text-right tnum ${rec.reduction_pct >= 0 ? "text-emerald-400" : "text-amber-400"}`}>
                  {rec.reduction_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}

function BenchmarkPanel({ r }: { r: BenchmarkResult }) {
  const reconstructed = r.reconstructable_count === r.record_count && r.record_count > 0;
  const maxBytes = Math.max(r.original_bytes, r.total_compressed_bytes, 1);
  return (
    <Card className="mb-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Original Size" value={bytes(r.original_bytes)} />
        <Metric label="Compressed Size" value={bytes(r.total_compressed_bytes)} />
        <Metric
          label="Storage Saved"
          value={`${r.savings_bytes >= 0 ? "" : "−"}${bytes(Math.abs(r.savings_bytes))}`}
          tone={r.savings_bytes >= 0 ? "green" : "amber"}
        />
        <Metric
          label="Savings %"
          value={`${r.reduction_pct.toFixed(1)}%`}
          tone={r.reduction_pct >= 0 ? "green" : "amber"}
        />
        <Metric label="Records" value={String(r.record_count)} />
        <Metric label="Templates" value={String(r.template_count)} />
        <Metric
          label="Reconstruction"
          value={reconstructed ? `${r.reconstructable_count} ✓ exact` : `${r.reconstructable_count}/${r.record_count}`}
          tone={reconstructed ? "green" : "red"}
        />
        <Metric label="Processing Rate" value={`${r.events_per_sec.toFixed(0)}/s`} />
      </div>

      <div className="mt-5 space-y-2">
        <BytesBar label="Original" value={r.original_bytes} max={maxBytes} tone="bg-slate-500" />
        <BytesBar
          label="Compressed"
          value={r.total_compressed_bytes}
          max={maxBytes}
          tone={r.savings_bytes >= 0 ? "bg-emerald-500" : "bg-amber-500"}
          note={`per-record ${bytes(r.compressed_bytes)} + template defs ${bytes(r.metadata_bytes)}`}
        />
      </div>

      {r.mismatches.length > 0 && (
        <div className="mt-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-xs">
          <p className="font-semibold text-red-300">
            {r.mismatches.length} record(s) did NOT reconstruct exactly:
          </p>
          {r.mismatches.map((m) => (
            <pre key={m.raw_log_id} className="mt-1 overflow-x-auto text-[11px] text-gray-300">
              orig: {m.original_preview}
              {"\n"}got:  {m.reconstructed_preview}
            </pre>
          ))}
        </div>
      )}

      <p className="mt-3 text-xs text-gray-500">
        Scope: <span className="font-mono">{r.scope}</span> · measured over {r.processing_seconds.toFixed(2)}s.
        Savings are (original − compressed) / original; a negative value means the compact
        representation was larger for this scope and is shown as-is.
      </p>
    </Card>
  );
}

function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "green" | "amber" | "red";
}) {
  const color =
    tone === "green" ? "text-emerald-300"
    : tone === "amber" ? "text-amber-300"
    : tone === "red" ? "text-red-300"
    : "text-gray-100";
  return (
    <div className="rounded-md border border-base-border p-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function BytesBar({
  label,
  value,
  max,
  tone,
  note,
}: {
  label: string;
  value: number;
  max: number;
  tone: string;
  note?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span className="tabular-nums">{bytes(value)}</span>
      </div>
      <div className="h-4 w-full overflow-hidden rounded bg-white/5">
        <div className={`h-full ${tone}`} style={{ width: `${(value / max) * 100}%` }} />
      </div>
      {note && <p className="mt-0.5 text-[10px] text-gray-600">{note}</p>}
    </div>
  );
}
