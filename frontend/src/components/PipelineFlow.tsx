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

const NODE_STYLE: Record<PipelineNode["status"], { accent: string; chip: string; text: string; dot: string }> = {
  idle: { accent: "bg-slate-200", chip: "bg-slate-100 text-slate-500", text: "text-slate-400", dot: "#94a3b8" },
  ok: { accent: "bg-emerald-500", chip: "bg-emerald-100 text-emerald-800", text: "text-emerald-700", dot: "#059669" },
  running: { accent: "bg-blue-500", chip: "bg-blue-100 text-blue-800", text: "text-blue-700", dot: "#2563eb" },
  warn: { accent: "bg-amber-500", chip: "bg-amber-100 text-amber-900", text: "text-amber-700", dot: "#d97706" },
  critical: { accent: "bg-red-500", chip: "bg-red-100 text-red-800", text: "text-red-700", dot: "#dc2626" },
};

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
    <div className="surface bg-surface-sheen p-4">
      <SectionHeader
        title="ULPF processing pipeline"
        hint="Log Sources → Ingestion → Security Shield → Parsing → Cleaning → PII → Normalization → Validation → Correlation → Risk → Alert"
        right={flowing ? <LiveDot label="processing" /> : <LiveDot label="idle" />}
      />

      {q.isLoading ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 11 }).map((_, i) => (
            <Skeleton key={i} className="h-[104px] rounded-xl" />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {nodes.map((n, i) => {
              const st = NODE_STYLE[n.status];
              const Icon = NODE_ICON[n.key] ?? Layers;
              const isActive = selected === n.key;
              return (
                <button
                  key={n.key}
                  onClick={() => setSelected(isActive ? null : n.key)}
                  aria-pressed={isActive}
                  className={`relative flex min-h-[104px] flex-col justify-between overflow-hidden rounded-xl border bg-base-panel-2 p-3 text-left transition-all hover:bg-white hover:shadow-sm ${
                    isActive ? "border-brand ring-1 ring-brand" : "border-base-border"
                  }`}
                >
                  <span className={`absolute inset-x-0 top-0 h-1 ${st.accent}`} aria-hidden />
                  <div className="flex items-center justify-between">
                    <span className="text-2xs font-bold uppercase tracking-wider text-slate-400">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <Icon className={`h-4 w-4 ${st.text}`} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-800">{n.label}</div>
                    <div className={`mt-1 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-2xs font-bold tnum ${st.chip}`}>
                      {n.count.toLocaleString()}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {active ? (
            <div className="mt-3 rounded-lg border border-base-border bg-base-panel-2 p-3 text-xs">
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
            <p className="mt-3 text-2xs text-slate-400">Select a stage for its breakdown.</p>
          )}
        </>
      )}
    </div>
  );
}
