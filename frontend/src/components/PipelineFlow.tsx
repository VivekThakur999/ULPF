import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsPipeline, type PipelineNode } from "@/services/endpoints";
import { ErrorState, LiveDot, SectionHeader, Skeleton } from "@/components/ui";

const NODE_STYLE: Record<PipelineNode["status"], { ring: string; text: string; dot: string }> = {
  idle: { ring: "border-base-border", text: "text-gray-500", dot: "#3b4658" },
  ok: { ring: "border-emerald-500/40", text: "text-emerald-300", dot: "#34d399" },
  running: { ring: "border-blue-500/50", text: "text-blue-300", dot: "#7ca9f9" },
  warn: { ring: "border-amber-500/40", text: "text-amber-300", dot: "#fbbf24" },
  critical: { ring: "border-red-500/50", text: "text-red-300", dot: "#f87171" },
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
 * stage (queried live from the backend) and a detail panel per stage. The
 * animated flow line only appears while a job is actually running.
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
        title="Processing pipeline"
        hint="Raw logs to alerts — every count is live from the backend"
        right={flowing ? <LiveDot label="processing" /> : <LiveDot label="idle" />}
      />

      {q.isLoading ? (
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-28 shrink-0 rounded-lg" />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <>
          <div className="-mx-1 overflow-x-auto px-1 pb-1">
            <div className="flex min-w-max items-stretch gap-1.5">
              {nodes.map((n, i) => {
                const st = NODE_STYLE[n.status];
                const isActive = selected === n.key;
                return (
                  <div key={n.key} className="flex items-center gap-1.5">
                    <button
                      onClick={() => setSelected(isActive ? null : n.key)}
                      aria-pressed={isActive}
                      className={`w-32 rounded-lg border bg-base-panel px-3 py-2 text-left transition ${st.ring} ${
                        isActive ? "ring-1 ring-brand" : "hover:border-base-border-strong"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: st.dot }} aria-hidden />
                        <span className="truncate text-2xs font-semibold uppercase tracking-wide text-gray-500">
                          {n.label}
                        </span>
                      </div>
                      <div className={`mt-1 text-lg font-semibold tnum ${st.text}`}>
                        {n.count.toLocaleString()}
                      </div>
                    </button>
                    {i < nodes.length - 1 && (
                      <div className="relative h-px w-4 shrink-0 bg-base-border-strong">
                        {flowing && (
                          <span className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-brand-fg/70 to-transparent" />
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {active ? (
            <div className="mt-3 rounded-lg border border-base-border bg-base-bg/60 p-3 text-xs">
              <div className="mb-1.5 font-semibold text-gray-200">{active.label}</div>
              {Object.keys(active.detail).length === 0 ? (
                <p className="text-gray-500">No breakdown for this stage.</p>
              ) : (
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-gray-400">
                  {Object.entries(active.detail).map(([k, v]) => (
                    <span key={k}>
                      {DETAIL_LABEL[k] ?? k}:{" "}
                      <span className="font-medium text-gray-200">{renderValue(v)}</span>
                    </span>
                  ))}
                </div>
              )}
              {active.count === 0 && <p className="mt-1 text-gray-600">No activity yet at this stage.</p>}
            </div>
          ) : (
            <p className="mt-3 text-2xs text-gray-600">Select a stage for its breakdown.</p>
          )}
        </>
      )}
    </div>
  );
}
