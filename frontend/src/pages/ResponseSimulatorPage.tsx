import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowDown, PlayCircle, Sparkles } from "lucide-react";
import {
  getRecommendation,
  listAlerts,
  listSimulations,
  runResponseSimulation,
  type RecommendResponse,
  type SimulateResponse,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  SectionHeader,
  Spinner,
  StatusPill,
  relTime,
} from "@/components/ui";

function SimBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-amber-100 px-2 py-0.5 text-2xs font-bold uppercase tracking-wider text-amber-800 ring-1 ring-amber-300">
      Simulation only
    </span>
  );
}

export default function ResponseSimulatorPage() {
  const { hasRole } = useAuth();
  const [params, setParams] = useSearchParams();
  const [alertId, setAlertId] = useState<string | null>(params.get("alert"));
  const [sim, setSim] = useState<SimulateResponse | null>(null);
  const [err, setErr] = useState("");

  const alerts = useQuery({ queryKey: ["resp-alerts"], queryFn: () => listAlerts() });
  const rec = useQuery({
    queryKey: ["recommend", alertId],
    queryFn: () => getRecommendation(alertId as string),
    enabled: !!alertId,
  });
  const history = useQuery({ queryKey: ["simulations"], queryFn: () => listSimulations() });

  const run = useMutation({
    mutationFn: () => runResponseSimulation(alertId as string),
    onSuccess: (r) => {
      setErr("");
      setSim(r);
      history.refetch();
    },
    onError: (e) => setErr(apiError(e)),
  });

  useEffect(() => {
    setSim(null);
    setErr("");
  }, [alertId]);

  const selectedAlert = rec.data?.alert;

  return (
    <div>
      <PageHeader
        eyebrow="Response"
        title="Response Simulator"
        subtitle="Safely model incident-response actions without changing real infrastructure. No firewall, host, or identity system is ever contacted."
        actions={<SimBadge />}
      />

      <div className="surface bg-surface-sheen mb-4 p-4">
        <label className="label">Select alert</label>
        {alerts.isLoading ? (
          <Spinner />
        ) : alerts.isError ? (
          <ErrorState error={alerts.error} onRetry={alerts.refetch} />
        ) : (
          <select
            className="input"
            value={alertId ?? ""}
            onChange={(e) => {
              const v = e.target.value || null;
              setAlertId(v);
              setParams(v ? { alert: v } : {});
            }}
          >
            <option value="">Choose an alert…</option>
            {(alerts.data?.items ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                [{a.severity}] {a.title} — risk {Math.round(a.risk_score)}
              </option>
            ))}
          </select>
        )}

        {selectedAlert && (
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
            <Field k="Alert ID" v={selectedAlert.id} mono />
            <Field k="Severity" v={<StatusPill status={selectedAlert.severity} />} />
            <Field k="Risk score" v={`${Math.round(selectedAlert.risk_score)} / 100`} />
            <Field k="Rule" v={selectedAlert.rule_key} />
            <Field k="Source / entity" v={JSON.stringify(selectedAlert.entity)} mono />
            <Field k="Timestamp" v={selectedAlert.ts ? new Date(selectedAlert.ts).toLocaleString() : "—"} />
            <div className="col-span-2 sm:col-span-3">
              <dt className="label">Reason (ULPF, deterministic)</dt>
              <dd className="text-slate-700">{selectedAlert.reason}</dd>
            </div>
          </dl>
        )}
        {alertId && (
          <Link to={`/assistant?alert=${alertId}`} className="btn-ghost mt-3 py-1.5 text-xs">
            <Sparkles className="h-3.5 w-3.5" /> Explain this alert with AI
          </Link>
        )}
      </div>

      {alertId && rec.isLoading && <Spinner label="Building recommendation…" />}
      {alertId && rec.isError && <ErrorState error={rec.error} onRetry={rec.refetch} />}

      {rec.data && <RecommendationPanel data={rec.data} />}

      {rec.data?.recommendation.available && (
        <>
          {err && (
            <div className="my-3">
              <ErrorState error={err} />
            </div>
          )}
          <div className="my-4">
            {hasRole("ANALYST") ? (
              <button className="btn-primary" disabled={run.isPending} onClick={() => run.mutate()}>
                <PlayCircle className={`h-4 w-4 ${run.isPending ? "animate-pulse" : ""}`} />
                {run.isPending ? "Running simulation…" : "Run Simulation"}
              </button>
            ) : (
              <p className="text-sm text-gray-500">ANALYST role required to run a simulation.</p>
            )}
          </div>
        </>
      )}

      {sim && <SimulationResult sim={sim} />}

      <h2 className="mb-3 mt-8 text-sm font-semibold text-slate-800">Simulation history</h2>
      {history.isLoading ? (
        <Spinner />
      ) : (history.data ?? []).length === 0 ? (
        <EmptyState title="No simulations recorded yet" hint="Select an alert and run a simulation to see it here." />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th>When</th>
              <th>By</th>
              <th>Alert</th>
              <th>Category</th>
              <th>Actions</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            {(history.data ?? []).map((s) => (
              <tr key={s.id}>
                <td className="whitespace-nowrap text-xs text-gray-400">{relTime(s.ts)}</td>
                <td className="text-xs">{s.actor_email}</td>
                <td className="max-w-xs truncate">{s.alert_title}</td>
                <td className="text-xs text-gray-400">{s.recommendation.category}</td>
                <td className="font-mono text-2xs">{s.actions.map((a) => a.action).join(", ")}</td>
                <td>
                  <StatusPill status="simulation" label={s.simulation_only ? "SIMULATION_ONLY" : "?"} />
                </td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}

function RecommendationPanel({ data }: { data: RecommendResponse }) {
  const r = data.recommendation;
  if (!r.available) {
    return (
      <div className="surface bg-surface-sheen mb-4 p-4">
        <SectionHeader title="Recommended response" />
        <p className="mt-1 text-sm text-gray-400">{r.label}</p>
        <p className="text-xs text-gray-600">{r.rationale}</p>
      </div>
    );
  }
  const primary = r.actions[0];
  return (
    <div className="surface bg-surface-sheen mb-4 border-brand/25 p-4">
      <SectionHeader title="Recommended response" right={<StatusPill status="simulation" />} />
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-brand-fg">{r.label}</span>
        <span className="badge bg-slate-100 text-slate-700 ring-1 ring-slate-200">{r.category}</span>
      </div>
      <p className="mt-1 text-sm text-slate-700">
        <span className="text-gray-500">Why: </span>
        {r.rationale}
      </p>

      <div className="mt-3">
        <div className="label">Evidence (ULPF)</div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
          {Object.entries(data.evidence.counts ?? {}).map(([k, v]) => (
            <span key={k}>
              {k.replace(/_/g, " ")}: <b className="text-slate-800">{String(v)}</b>
            </span>
          ))}
          {(data.evidence.shield_verdicts ?? []).length > 0 && (
            <span>
              shield: <b className="text-amber-800">{(data.evidence.shield_verdicts as string[]).join(", ")}</b>
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-3">
        <div className="mb-2 flex items-center gap-2">
          <SimBadge />
          <span className="text-xs text-gray-400">structured action objects — representations only</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <ActionTile label="Source" value={primary.target} />
          <ActionTile label="Action" value={primary.action} />
          <ActionTile label="Protocol" value={primary.protocol ?? "—"} />
          <ActionTile label="Port" value={primary.port != null ? String(primary.port) : "—"} />
          <ActionTile label="Mode" value={primary.mode} />
          <div className="sm:col-span-3">
            <div className="label">Expected result</div>
            <div className="text-xs text-slate-700">{primary.detail}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SimulationResult({ sim }: { sim: SimulateResponse }) {
  const p = sim.result.primary;
  return (
    <div className="surface bg-surface-sheen my-4 border-emerald-500/25 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="badge bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300">
          Simulation complete
        </span>
        <SimBadge />
        <span className="text-xs text-gray-500">audit id {sim.audit_id.slice(0, 8)}…</span>
      </div>
      <p className="text-xs text-amber-800">{sim.disclaimer}</p>

      {p && (
        <>
          <div className="mt-4 flex flex-col items-center gap-1.5 text-center text-sm">
            <div className="rounded-lg border border-base-border bg-base-panel px-4 py-2">
              <div className="label">Current state</div>
              <div className="font-semibold text-emerald-700">{p.state_change.before}</div>
              {p.target && <div className="text-2xs text-gray-500">{p.target}</div>}
            </div>
            <ArrowDown className="h-4 w-4 text-gray-700" />
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-amber-900">
              <div className="label text-amber-800/80">Simulated change</div>
              <div className="font-mono text-xs">{p.kind}</div>
            </div>
            <ArrowDown className="h-4 w-4 text-gray-700" />
            <div className="rounded-lg border border-base-border bg-base-panel px-4 py-2">
              <div className="label">Simulated state</div>
              <div className="font-semibold text-red-700">{p.state_change.after}</div>
            </div>
          </div>

          <p className="mt-3 text-center text-xs text-gray-400">{p.expected_result}</p>
          <p className="mt-1 text-center text-xs font-medium text-gray-500">No real system was modified.</p>

          <details className="mt-3 text-xs">
            <summary className="cursor-pointer text-gray-500">before / after detail</summary>
            <div className="mt-1 grid gap-2 sm:grid-cols-2">
              <pre className="overflow-x-auto rounded-lg bg-base-bg p-2">before: {JSON.stringify(p.before, null, 1)}</pre>
              <pre className="overflow-x-auto rounded-lg bg-base-bg p-2">after: {JSON.stringify(p.after, null, 1)}</pre>
            </div>
          </details>
        </>
      )}
    </div>
  );
}

function Field({ k, v, mono }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="label">{k}</dt>
      <dd className={mono ? "truncate font-mono text-xs" : ""}>{v}</dd>
    </div>
  );
}

function ActionTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="surface-2 p-2">
      <div className="label">{label}</div>
      <div className="font-mono text-xs text-slate-800">{value}</div>
    </div>
  );
}
