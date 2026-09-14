import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Database,
  GitMerge,
  Layers,
  Lock,
  Radar,
  ScanSearch,
  ShieldCheck,
  Siren,
  Sparkles,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { analyticsPipeline, type PipelineNode } from "@/services/endpoints";
import { ErrorState, LiveDot, SectionHeader, Skeleton } from "@/components/ui";
import { TONE, type AccentTone } from "@/lib/tone";

const NODE_ICON: Record<string, LucideIcon> = {
  sources: Database,
  ingestion: Upload,
  detection: ShieldCheck,
  parsing: ScanSearch,
  cleaning: Sparkles,
  pii: Lock,
  normalization: Layers,
  validation: CheckCircle2,
  correlation: GitMerge,
  risk: Radar,
  alert: Siren,
};

/** What kind of stage this is — a fixed identity color, so a healthy pipeline
 * reads as many deliberately-colored stages rather than one repeated "ok" green. */
const NODE_IDENTITY: Record<string, AccentTone> = {
  sources: "sky",
  ingestion: "blue",
  detection: "emerald",
  parsing: "sky",
  cleaning: "cyan",
  pii: "purple",
  normalization: "blue",
  validation: "emerald",
  correlation: "violet",
  risk: "amber",
  alert: "red",
};

/** Short, static description of what each real stage does — labeling, not data. */
const NODE_CAPTION: Record<string, string> = {
  sources: "Heterogeneous log inputs",
  ingestion: "Raw record intake",
  detection: "Injection & integrity screening",
  parsing: "Format detection + field extraction",
  cleaning: "Dedup, validation, quarantine",
  pii: "Deterministic pseudonymization",
  normalization: "Universal event schema",
  validation: "Schema + field validation",
  correlation: "Cross-source event linking",
  risk: "Transparent, disclosed scoring",
  alert: "SOC alert dispatch",
};

/** Resolve a node's visual tone: a real problem always wins over identity color. */
function toneFor(n: PipelineNode) {
  if (n.status === "critical") return TONE.red;
  if (n.status === "warn") return TONE.amber;
  if (n.status === "idle") return TONE.slate;
  return TONE[NODE_IDENTITY[n.key] ?? "slate"];
}

const DETAIL_LABEL: Record<string, string> = {
  configured_sources: "configured sources",
  jobs_running: "jobs running",
  total_records: "total records",
  safe: "safe",
  suspicious: "suspicious",
  weaponized: "weaponized",
  invalid: "invalid",
  duplicates: "duplicates",
  quarantined: "quarantined",
  mode: "PII mode",
  protected_events: "protected events",
  schema_version: "schema version",
  ok: "ok",
  partial: "partial",
  error: "error",
  alerts_with_related_events: "correlated alerts",
  avg_risk_score: "avg risk score",
  total: "total alerts",
  new: "new alerts",
  by_parser: "by parser",
};

function renderValue(v: unknown): string {
  if (Array.isArray(v)) {
    return (
      v
        .map((row) =>
          row && typeof row === "object" && "label" in row
            ? `${(row as { label: string }).label} (${(row as { value: number }).value})`
            : String(row),
        )
        .join(", ") || "—"
    );
  }
  return String(v);
}

/**
 * The pipeline story: raw logs -> ... -> alerts, with a real count on every
 * stage (queried live from the backend) and a detail panel per stage. Nothing
 * here is animated fake activity — the flow accent only lights up while a
 * job is actually running.
 */
export default function PipelineFlow() {
  const [selected, setSelected] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["analytics-pipeline"],
    queryFn: analyticsPipeline,
    refetchInterval: 8000,
  });

  const nodes = q.data?.nodes ?? [];
  const active = nodes.find((n) => n.key === selected) ?? null;
  const flowing = nodes.some((n) => n.status === "running");

  return (
    <div className="surface bg-surface-sheen p-6">
      <SectionHeader
        title="ULPF Processing Pipeline"
        hint="Log Sources → Ingestion → Security Shield → Parsing → Cleaning → PII → Normalization → Validation → Correlation → Risk → Alert"
        right={flowing ? <LiveDot label="processing" /> : <LiveDot label="idle" />}
      />

      {q.isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {Array.from({ length: 11 }).map((_, i) => (
            <Skeleton key={i} className="h-[152px] rounded-xl" />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {nodes.map((n, i) => {
              const t = toneFor(n);
              const Icon = NODE_ICON[n.key] ?? Layers;
              const isActive = selected === n.key;
              return (
                <button
                  key={n.key}
                  onClick={() => setSelected(isActive ? null : n.key)}
                  aria-pressed={isActive}
                  className={`relative flex min-h-[152px] flex-col justify-between overflow-hidden rounded-xl border bg-white p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
                    isActive ? "border-brand ring-2 ring-brand/40" : "border-base-border"
                  }`}
                >
                  <span className={`absolute inset-x-0 top-0 h-1.5 ${t.bar}`} aria-hidden />
                  <div className="flex items-center justify-between">
                    <span className="text-2xs font-bold uppercase tracking-wider text-slate-400">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className={`grid h-7 w-7 place-items-center rounded-lg ${t.chip}`}>
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-900">{n.label}</div>
                    <div className="mt-0.5 text-2xs leading-snug text-slate-500">{NODE_CAPTION[n.key]}</div>
                  </div>
                  <div className={`inline-flex w-fit items-center gap-1 rounded px-1.5 py-0.5 text-2xs font-bold tnum ${t.chip}`}>
                    {n.count.toLocaleString()}
                  </div>
                </button>
              );
            })}
          </div>

          {active ? (
            <div className="mt-4 rounded-lg border border-base-border bg-base-panel-2 p-4 text-xs">
              <div className="mb-1.5 font-semibold text-slate-800">{active.label} — detail</div>
              {Object.keys(active.detail).length === 0 ? (
                <p className="text-slate-500">No breakdown for this stage.</p>
              ) : (
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-slate-500">
                  {Object.entries(active.detail).map(([k, v]) => (
                    <span key={k}>
                      {DETAIL_LABEL[k] ?? k}:{" "}
                      <span className="font-medium text-slate-800">{renderValue(v)}</span>
                    </span>
                  ))}
                </div>
              )}
              {active.count === 0 && <p className="mt-1 text-slate-400">No activity yet at this stage.</p>}
            </div>
          ) : (
            <p className="mt-4 text-2xs text-slate-400">Select a stage for its breakdown.</p>
          )}
        </>
      )}
    </div>
  );
}
