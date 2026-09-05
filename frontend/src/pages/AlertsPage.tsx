import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { listAlerts, runDetection, type Alert } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import {
  DataTable,
  EmptyState,
  ErrorState,
  FilterChips,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import AlertInvestigation from "@/components/AlertInvestigation";

const STATUS_OPTIONS = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"];
const SEV_OPTIONS = ["critical", "high", "medium", "low", "info"];

export default function AlertsPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");

  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: () => listAlerts(),
    refetchInterval: 15000,
  });
  const detect = useMutation({
    mutationFn: () => runDetection(24),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["nav-active-alerts"] });
    },
  });

  const all = alerts.data?.items ?? [];
  const filtered = useMemo(
    () =>
      all.filter(
        (a) =>
          (!status || a.status === status) &&
          (!severity || a.risk_breakdown.band === severity || a.severity === severity),
      ),
    [all, status, severity],
  );

  const summary = useMemo(() => {
    const active = all.filter((a) => !["RESOLVED", "FALSE_POSITIVE"].includes(a.status)).length;
    return {
      active,
      critical: all.filter((a) => a.risk_breakdown.band === "critical").length,
      high: all.filter((a) => a.risk_breakdown.band === "high").length,
      investigating: all.filter((a) => a.status === "INVESTIGATING").length,
      resolved: all.filter((a) => a.status === "RESOLVED").length,
    };
  }, [all]);

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Security Alerts"
        subtitle="Produced by the deterministic correlation + rules engine. Every alert carries a transparent risk breakdown and an incident timeline."
        actions={
          <div className="flex items-center gap-3">
            <LiveDot />
            {hasRole("ANALYST") && (
              <button className="btn-ghost" disabled={detect.isPending} onClick={() => detect.mutate()}>
                <RefreshCw className={`h-4 w-4 ${detect.isPending ? "animate-spin" : ""}`} /> Run detection
              </button>
            )}
          </div>
        }
      />

      <div className="mb-5">
        <KpiGrid>
          <Kpi label="Active" value={summary.active} status={summary.active ? "investigating" : "safe"} loading={alerts.isLoading} />
          <Kpi label="Critical" value={summary.critical} status={summary.critical ? "critical" : "safe"} loading={alerts.isLoading} />
          <Kpi label="High" value={summary.high} status={summary.high ? "high" : "safe"} loading={alerts.isLoading} />
          <Kpi label="Investigating" value={summary.investigating} status="investigating" loading={alerts.isLoading} />
          <Kpi label="Resolved" value={summary.resolved} status="resolved" loading={alerts.isLoading} />
        </KpiGrid>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <select className="input max-w-[180px]" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          {SEV_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select className="input max-w-[200px]" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <FilterChips
          filters={{ severity: severity || undefined, status: status || undefined }}
          onRemove={(k) => (k === "severity" ? setSeverity("") : setStatus(""))}
          onClear={() => {
            setSeverity("");
            setStatus("");
          }}
        />
      </div>

      {alerts.isLoading ? (
        <SkeletonTable rows={6} cols={6} />
      ) : alerts.isError ? (
        <ErrorState error={alerts.error} onRetry={alerts.refetch} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={all.length ? "No alerts match these filters" : "No alerts"}
          hint={
            all.length
              ? "Clear a filter to see the full queue."
              : "Ingest the brute-force scenario (Ingestion → Import sample), then Run detection."
          }
        />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th className="w-16 text-right">Risk</th>
              <th>Severity</th>
              <th>Rule</th>
              <th>Title</th>
              <th>Source</th>
              <th>Affected hosts</th>
              <th>Last seen</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) => (
              <AlertRow key={a.id} alert={a} onOpen={() => setSelected(a.id)} />
            ))}
          </tbody>
        </DataTable>
      )}

      {selected && <AlertInvestigation alertId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function AlertRow({ alert, onOpen }: { alert: Alert; onOpen: () => void }) {
  const band = alert.risk_breakdown.band;
  return (
    <tr className="clickable" onClick={onOpen}>
      <td className="text-right">
        <span className="tnum font-semibold" style={{ color: bandColor(band) }}>
          {Math.round(alert.risk_score)}
        </span>
      </td>
      <td>
        <StatusPill status={alert.severity} />
      </td>
      <td className="font-mono text-xs text-gray-400">{alert.rule_key ?? "—"}</td>
      <td className="max-w-[280px] truncate font-medium text-gray-100" title={alert.title}>
        {alert.title}
      </td>
      <td className="text-xs text-gray-400">{alert.source}</td>
      <td className="max-w-[180px] truncate text-xs text-gray-400">
        {alert.affected_hosts.length ? alert.affected_hosts.join(", ") : "—"}
      </td>
      <td className="whitespace-nowrap text-xs text-gray-500">{relTime(alert.updated_at || alert.ts)}</td>
      <td>
        <StatusPill status={alert.status} />
      </td>
    </tr>
  );
}

function bandColor(band: string): string {
  return (
    { critical: "#f87171", high: "#fb923c", medium: "#fbbf24", low: "#38bdf8" }[band] ?? "#64748b"
  );
}
