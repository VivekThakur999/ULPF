import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAlerts, type Alert } from "@/services/endpoints";
import {
  Badge,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";
import AlertInvestigation from "@/components/AlertInvestigation";

const META_KEYS = ["type", "incident_center", "window_seconds"];

function pivotOf(alert: Alert): { key: string; label: string } {
  const entries = Object.entries(alert.entity).filter(([k]) => !META_KEYS.includes(k));
  if (entries.length === 0) return { key: alert.rule_key ?? alert.source, label: alert.rule_key ?? alert.source };
  const [k, v] = entries[0];
  return { key: `${k}:${String(v)}`, label: `${k} = ${String(v)}` };
}

interface Incident {
  key: string;
  label: string;
  alerts: Alert[];
  hosts: Set<string>;
  maxRisk: number;
  topBand: string;
  lastSeen: string;
}

const BAND_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

export default function IncidentsPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["alerts"], queryFn: () => listAlerts(), refetchInterval: 15000 });

  const incidents = useMemo<Incident[]>(() => {
    const map = new Map<string, Incident>();
    for (const a of q.data?.items ?? []) {
      const { key, label } = pivotOf(a);
      let inc = map.get(key);
      if (!inc) {
        inc = { key, label, alerts: [], hosts: new Set(), maxRisk: 0, topBand: "info", lastSeen: a.ts };
        map.set(key, inc);
      }
      inc.alerts.push(a);
      a.affected_hosts.forEach((h) => inc!.hosts.add(h));
      inc.maxRisk = Math.max(inc.maxRisk, a.risk_score);
      if ((BAND_RANK[a.risk_breakdown.band] ?? 0) > (BAND_RANK[inc.topBand] ?? 0)) inc.topBand = a.risk_breakdown.band;
      if (new Date(a.updated_at || a.ts) > new Date(inc.lastSeen)) inc.lastSeen = a.updated_at || a.ts;
    }
    return [...map.values()].sort((x, y) => y.maxRisk - x.maxRisk);
  }, [q.data]);

  const multiAlert = incidents.filter((i) => i.alerts.length > 1).length;

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Incidents"
        subtitle="Alerts grouped by the entity they converge on — the focus for an investigation. Each incident links every alert, host and correlated event ULPF associated with it."
        actions={<LiveDot />}
      />

      <div className="mb-5">
        <KpiGrid>
          <Kpi label="Incidents" value={incidents.length} loading={q.isLoading} />
          <Kpi label="Multi-alert" value={multiAlert} status={multiAlert ? "high" : "safe"} loading={q.isLoading} />
          <Kpi label="Alerts total" value={q.data?.items.length ?? 0} loading={q.isLoading} />
          <Kpi
            label="Hosts involved"
            value={new Set(incidents.flatMap((i) => [...i.hosts])).size}
            loading={q.isLoading}
          />
        </KpiGrid>
      </div>

      {q.isLoading ? (
        <SkeletonTable rows={4} cols={3} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : incidents.length === 0 ? (
        <EmptyState
          title="No incidents"
          hint="Incidents appear once the detection engine has produced alerts. Ingest a scenario and run detection on the Alerts page."
        />
      ) : (
        <div className="space-y-3">
          {incidents.map((inc) => (
            <div key={inc.key} className="surface bg-surface-sheen p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusPill status={inc.topBand} label={`${inc.topBand.toUpperCase()} · risk ${Math.round(inc.maxRisk)}`} />
                    <span className="font-mono text-sm text-gray-200">{inc.label}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {inc.alerts.length} alert{inc.alerts.length === 1 ? "" : "s"}
                    {inc.hosts.size > 0 && ` · ${inc.hosts.size} host${inc.hosts.size === 1 ? "" : "s"}: ${[...inc.hosts].join(", ")}`}
                    {` · last activity ${relTime(inc.lastSeen)}`}
                  </p>
                </div>
              </div>

              <div className="mt-3 space-y-1">
                {inc.alerts.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setSelected(a.id)}
                    className="surface-2 flex w-full flex-wrap items-center gap-2 p-2 text-left text-xs hover:bg-white/[0.04]"
                  >
                    <StatusPill status={a.severity} />
                    <span className="font-mono text-gray-500">{a.rule_key ?? "—"}</span>
                    <span className="min-w-0 flex-1 truncate text-gray-200">{a.title}</span>
                    <Badge tone="slate">{a.status.replace(/_/g, " ")}</Badge>
                    <span className="text-gray-500">{relTime(a.ts)}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && <AlertInvestigation alertId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
