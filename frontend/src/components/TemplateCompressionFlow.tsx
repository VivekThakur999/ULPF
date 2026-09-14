import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { decompressRecord, getTemplate } from "@/services/endpoints";
import { Badge, ErrorState, Spinner } from "@/components/ui";

const STAGES = [
  "RAW LOG",
  "TEMPLATE MINING",
  "TEMPLATE ID",
  "VARIABLE EXTRACTION",
  "COMPACT REPRESENTATION",
  "STORAGE",
  "RECONSTRUCTION",
] as const;

/**
 * Interactive walkthrough of one real record through the compression pipeline.
 * Every stage shows actual data from /compression/decompress + /templates -
 * nothing is illustrative.
 */
export default function TemplateCompressionFlow({ rawLogId }: { rawLogId: string }) {
  const [stage, setStage] = useState<(typeof STAGES)[number]>("RAW LOG");

  const decomp = useQuery({
    queryKey: ["decompress", rawLogId],
    queryFn: () => decompressRecord(rawLogId),
  });
  const templateKey = decomp.data?.template_key ?? null;
  const tpl = useQuery({
    queryKey: ["template", templateKey],
    queryFn: () => getTemplate(templateKey as string),
    enabled: !!templateKey,
  });

  const compact = useMemo(() => {
    if (!decomp.data || !templateKey) return null;
    const payload: Record<string, unknown> = { t: templateKey, v: decomp.data.variables };
    return JSON.stringify(payload);
  }, [decomp.data, templateKey]);

  if (decomp.isLoading) return <Spinner label="Loading round-trip…" />;
  if (decomp.isError) return <ErrorState error={decomp.error} onRetry={decomp.refetch} />;
  const d = decomp.data!;

  if (!templateKey) {
    return (
      <div className="card text-sm text-gray-400">
        This record has not been assigned a template yet. Run a benchmark or “Compress” first.
      </div>
    );
  }

  const originalBytes = new TextEncoder().encode(d.original).length;
  const compactBytes = compact ? new TextEncoder().encode(compact).length : 0;

  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-center gap-1">
        {STAGES.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <button
              onClick={() => setStage(s)}
              className={`rounded-md border px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide transition ${
                stage === s
                  ? "border-brand bg-brand/15 text-brand-fg"
                  : "border-base-border text-slate-500 hover:bg-slate-100"
              }`}
            >
              {s}
            </button>
            {i < STAGES.length - 1 && <ChevronRight className="h-3 w-3 text-gray-700" />}
          </div>
        ))}
      </div>

      <div className="rounded-md border border-base-border bg-base-bg p-3 text-xs">
        {stage === "RAW LOG" && (
          <>
            <p className="mb-1 text-gray-500">Original raw log ({originalBytes} bytes)</p>
            <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-slate-800">
              {d.original}
            </pre>
          </>
        )}

        {stage === "TEMPLATE MINING" && (
          <>
            <p className="mb-1 text-gray-500">
              Deterministic clustering assigned this line to a template shape.
            </p>
            {tpl.data ? (
              <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-slate-800">
                {tpl.data.pattern}
              </pre>
            ) : (
              <Spinner />
            )}
          </>
        )}

        {stage === "TEMPLATE ID" && (
          <>
            <p className="mb-1 text-gray-500">Stable, deterministic identifier</p>
            <div className="font-mono text-lg text-brand-fg">{templateKey}</div>
            {tpl.data && (
              <p className="mt-1 text-gray-500">
                signature <span className="font-mono">{tpl.data.token_signature}</span> ·{" "}
                {tpl.data.occurrences} occurrences share this template
              </p>
            )}
          </>
        )}

        {stage === "VARIABLE EXTRACTION" && (
          <>
            <p className="mb-1 text-gray-500">
              {d.variables.length} variable value(s) pulled from the fixed positions
            </p>
            <div className="flex flex-wrap gap-1.5">
              {d.variables.map((v, i) => (
                <span
                  key={i}
                  className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-[11px] text-amber-900"
                >
                  {v}
                </span>
              ))}
            </div>
          </>
        )}

        {stage === "COMPACT REPRESENTATION" && (
          <>
            <p className="mb-1 text-gray-500">
              Stored form: template reference + variables ({compactBytes} bytes vs {originalBytes} original)
            </p>
            <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-slate-800">
              {compact}
            </pre>
            <div className="mt-2 flex items-center gap-2">
              <Badge tone={compactBytes < originalBytes ? "green" : "amber"}>
                {compactBytes < originalBytes
                  ? `${(((originalBytes - compactBytes) / originalBytes) * 100).toFixed(0)}% smaller`
                  : `${(((compactBytes - originalBytes) / originalBytes) * 100).toFixed(0)}% larger`}
              </Badge>
              <span className="text-[10px] text-gray-600">
                (this single line; template definition stored once, shared across all occurrences)
              </span>
            </div>
          </>
        )}

        {stage === "STORAGE" && (
          <>
            <p className="mb-1 text-gray-500">
              Persisted as a <span className="font-mono">template_matches</span> row — the original
              raw log is also kept untouched for audit.
            </p>
            <pre className="overflow-x-auto font-mono text-slate-800">
{`raw_log_id : ${d.raw_log_id}
template   : ${templateKey}
variables  : ${d.variables.length} values
separators : default (single space) unless stored`}
            </pre>
          </>
        )}

        {stage === "RECONSTRUCTION" && (
          <>
            <p className="mb-1 text-gray-500">
              template + variables (+ this record’s separators) → exact original text
            </p>
            <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-slate-800">
              {d.reconstructed}
            </pre>
            <div className="mt-2">
              {d.exact_match ? (
                <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">
                  ✓ Exact reconstruction verified (byte-for-byte equal to the original)
                </span>
              ) : (
                <span className="rounded bg-red-100 px-2 py-1 text-red-800">
                  ✕ Reconstruction mismatch
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
