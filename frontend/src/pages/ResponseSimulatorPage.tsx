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
import { Badge, Card, ErrorState, PageHeader, Spinner } from "@/components/ui";
import { severityClass } from "@/utils/severity";

function SimBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/40">
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
        title="Response Simulator"
        subtitle="Safely test incident-response actions without changing real infrastructure. No firewall, host, or identity system is ever contacted."
        actions={<SimBadge />}
      />

      <Card className="mb-4">
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
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
            <Field k="Alert ID" v={selectedAlert.id} mono />
            <Field k="Severity" v={<span className={`badge ${severityClass(selectedAlert.severity)}`}>{selectedAlert.severity}</span>} />
            <Field k="Risk score" v={`${Math.round(selectedAlert.risk_score)} / 100`} />
            <Field k="Rule" v={selectedAlert.rule_key} />
            <Field k="Source / entity" v={JSON.stringify(selectedAlert.entity)} mono />
            <Field k="Timestamp" v={selectedAlert.ts ? new Date(selectedAlert.ts).toLocaleString() : "—"} />
            <div className="col-span-2 sm:col-span-3">
              <dt className="text-xs uppercase text-gray-500">Reason (ULPF, deterministic)</dt>
              <dd className="text-gray-300">{selectedAlert.reason}</dd>
            </div>
          </dl>
        )}
        {alertId && (
          <Link to={`/assistant?alert=${alertId}`} className="btn-ghost mt-3 py-1 text-xs">
            <Sparkles className="h-3.5 w-3.5" /> Explain this alert with AI
          </Link>
        )}
      </Card>

      {alertId && rec.isLoading && <Spinner label="Building recommendation…" />}
      {alertId && rec.isError && <ErrorState error={rec.error} onRetry={rec.refetch} />}

      {rec.data && (
        <RecommendationPanel data={rec.data} />
      )}

      {rec.data?.recommendation.available && (
        <>
          {err && <div className="my-3"><ErrorState error={err} /></div>}
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

      <h2 className="mb-2 mt-8 text-sm font-semibold text-gray-300">Simulation history</h2>
      {history.isLoading ? (
        <Spinner />
      ) : (history.data ?? []).length === 0 ? (
        <p className="text-sm text-gray-500">No simulations recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2 pr-3">When</th>
                <th className="py-2 pr-3">By</th>
                <th className="py-2 pr-3">Alert</th>
                <th className="py-2 pr-3">Category</th>
                <th className="py-2 pr-3">Actions</th>
                <th className="py-2 pr-3">Mode</th>
              </tr>
            </thead>
            <tbody>
              {(history.data ?? []).map((s) => (
                <tr key={s.id} className="border-t border-base-border">
                  <td className="py-2 pr-3 text-xs text-gray-400">{new Date(s.ts).toLocaleString()}</td>
                  <td className="py-2 pr-3 text-xs">{s.actor_email}</td>
                  <td className="max-w-xs truncate py-2 pr-3">{s.alert_title}</td>
                  <td className="py-2 pr-3">{s.recommendation.category}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{s.actions.map((a) => a.action).join(", ")}</td>
                  <td className="py-2 pr-3">
                    <Badge tone="amber">{s.simulation_only ? "SIMULATION_ONLY" : "?"}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RecommendationPanel({ data }: { data: RecommendResponse }) {
  const r = data.recommendation;
  if (!r.available) {
    return (
      <Card className="mb-4">
        <h3 className="text-xs font-semibold uppercase text-gray-500">Recommended Response</h3>
        <p className="mt-1 text-sm text-gray-400">{r.label}</p>
        <p className="text-xs text-gray-600">{r.rationale}</p>
      </Card>
    );
  }
  const primary = r.actions[0];
  return (
    <Card className="mb-4 border-brand/30">
      <h3 className="mb-1 text-xs font-semibold uppercase text-gray-500">Recommended Response</h3>
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-brand-fg">{r.label}</span>
        <Badge tone="slate">{r.category}</Badge>
      </div>
      <p className="mt-1 text-sm text-gray-300">
        <span className="text-gray-500">Why: </span>
        {r.rationale}
      </p>

      <div className="mt-3">
        <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">Evidence (ULPF)</h4>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
          {Object.entries(data.evidence.counts ?? {}).map(([k, v]) => (
            <span key={k}>{k.replace(/_/g, " ")}: <b className="text-gray-200">{String(v)}</b></span>
          ))}
          {(data.evidence.shield_verdicts ?? []).length > 0 && (
            <span>shield: <b className="text-amber-300">{(data.evidence.shield_verdicts as string[]).join(", ")}</b></span>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
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
            <div className="text-[10px] uppercase text-gray-500">Expected result</div>
            <div className="text-xs text-gray-300">{primary.detail}</div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function SimulationResult({ sim }: { sim: SimulateResponse }) {
  const p = sim.result.primary;
  return (
    <Card className="my-4 border-emerald-500/30">
      <div className="mb-2 flex items-center gap-2">
        <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-xs font-bold uppercase text-emerald-300">
          Simulation complete
        </span>
        <SimBadge />
        <span className="text-xs text-gray-500">audit id {sim.audit_id.slice(0, 8)}…</span>
      </div>
      <p className="text-xs text-amber-200/90">{sim.disclaimer}</p>

      {p && (
        <>
          <div className="mt-4 flex flex-col items-center gap-1 text-center text-sm">
            <div className="rounded-md border border-base-border bg-base-panel px-4 py-2">
              <div className="text-[10px] uppercase text-gray-500">Current state</div>
              <div className="font-semibold text-emerald-300">{p.state_change.before}</div>
            </div>
            <ArrowDown className="h-4 w-4 text-gray-700" />
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-amber-200">
              <div className="text-[10px] uppercase">Simulated change</div>
              <div className="font-mono text-xs">{p.kind}</div>
            </div>
            <ArrowDown className="h-4 w-4 text-gray-700" />
            <div className="rounded-md border border-base-border bg-base-panel px-4 py-2">
              <div className="text-[10px] uppercase text-gray-500">Simulated state</div>
              <div className="font-semibold text-red-300">{p.state_change.after}</div>
            </div>
          </div>

          <p className="mt-3 text-center text-xs text-gray-400">{p.expected_result}</p>
          <p className="mt-1 text-center text-xs font-medium text-gray-500">No real system was modified.</p>

          <details className="mt-3 text-xs">
            <summary className="cursor-pointer text-gray-500">before / after detail</summary>
            <div className="mt-1 grid gap-2 sm:grid-cols-2">
              <pre className="overflow-x-auto rounded bg-base-bg p-2">before: {JSON.stringify(p.before, null, 1)}</pre>
              <pre className="overflow-x-auto rounded bg-base-bg p-2">after: {JSON.stringify(p.after, null, 1)}</pre>
            </div>
          </details>
        </>
      )}
    </Card>
  );
}

function Field({ k, v, mono }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase text-gray-500">{k}</dt>
      <dd className={mono ? "truncate font-mono text-xs" : ""}>{v}</dd>
    </div>
  );
}

function ActionTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded border border-base-border p-2">
      <div className="text-[10px] uppercase text-gray-500">{label}</div>
      <div className="font-mono text-xs text-gray-200">{value}</div>
    </div>
  );
}
