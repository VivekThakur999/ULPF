import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { analyticsPipeline, type PipelineNode } from "@/services/endpoints";
import { Badge, ErrorState, LiveDot, Spinner } from "@/components/ui";

const STATUS_STYLE: Record<PipelineNode["status"], string> = {
  idle: "border-base-border bg-base-panel text-gray-500",
  ok: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  running: "border-blue-500/50 bg-blue-500/10 text-blue-300 animate-pulse",
  warn: "border-amber-500/50 bg-amber-500/10 text-amber-300",
  critical: "border-red-500/50 bg-red-500/10 text-red-300",
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
};

/**
 * The Dashboard's pipeline story: RAW -> ... -> ALERT, with a real count on
 * every node (queried live from the backend), clickable for the underlying
 * breakdown. Nothing here is animated fake activity.
 */
export default function PipelineFlow() {
  const [selected, setSelected] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["analytics-pipeline"],
    queryFn: analyticsPipeline,
    refetchInterval: 8000,
  });

  if (q.isLoading) return <Spinner label="Loading pipeline state…" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const nodes = q.data!.nodes;
  const active = nodes.find((n) => n.key === selected);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Pipeline — raw logs to alerts
        </h2>
        <LiveDot />
      </div>

      <div className="flex flex-wrap items-center gap-1">
        {nodes.map((n, i) => (
          <div key={n.key} className="flex items-center gap-1">
            <button
              onClick={() => setSelected(selected === n.key ? null : n.key)}
              className={`rounded-lg border px-3 py-2 text-left transition ${STATUS_STYLE[n.status]} ${
                selected === n.key ? "ring-2 ring-brand" : ""
              }`}
            >
              <div className="text-[10px] uppercase tracking-wide opacity-80">{n.label}</div>
              <div className="text-lg font-semibold tabular-nums">{n.count.toLocaleString()}</div>
            </button>
            {i < nodes.length - 1 && <ChevronRight className="h-4 w-4 shrink-0 text-gray-700" />}
          </div>
        ))}
      </div>

      {active && (
        <div className="mt-3 rounded-md border border-base-border bg-base-bg p-3 text-xs">
          <div className="mb-1.5 font-semibold text-gray-300">{active.label} — detail</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-gray-400">
            {Object.entries(active.detail).map(([k, v]) => (
              <span key={k}>
                {DETAIL_LABEL[k] ?? k}:{" "}
                <span className="font-medium text-gray-200">
                  {Array.isArray(v)
                    ? v.map((row) => (typeof row === "object" ? `${row.label}(${row.value})` : row)).join(", ") || "—"
                    : String(v)}
                </span>
              </span>
            ))}
          </div>
          {active.count === 0 && (
            <p className="mt-1 text-gray-600">No activity yet at this stage.</p>
          )}
        </div>
      )}
      {!active && <Badge tone="slate">click a stage for detail</Badge>}
    </div>
  );
}
