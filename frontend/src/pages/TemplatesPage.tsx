import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Sparkles } from "lucide-react";
import {
  getTemplate,
  getTemplateExamples,
  listTemplates,
  mineTemplates,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { Badge, Card, EmptyState, ErrorState, PageHeader, Spinner } from "@/components/ui";
import TemplatePattern from "@/components/TemplatePattern";

export default function TemplatesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [source, setSource] = useState("");
  const [minFreq, setMinFreq] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  const params = { source: source || undefined, min_frequency: minFreq, limit: 200 };
  const q = useQuery({
    queryKey: ["templates", params],
    queryFn: () => listTemplates(params),
  });

  const mine = useMutation({
    mutationFn: () => mineTemplates({ source: source || undefined }),
    onSuccess: (r) => {
      setNotice(
        `Mined ${r.records_scanned} records → ${r.templates_total} templates ` +
          `(${r.templates_created} new) in ${r.duration_seconds}s` +
          (r.scan_limit_hit ? " — scan limit reached, some records not included" : ""),
      );
      qc.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (e) => setNotice(apiError(e)),
  });

  return (
    <div>
      <PageHeader
        title="Template Explorer"
        subtitle="Discover recurring structures across heterogeneous logs. Templates are mined from the real ingested raw logs; every occurrence stays reconstructable."
        actions={
          <div className="flex items-center gap-2">
            <button className="btn-ghost" onClick={() => q.refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            {hasRole("ANALYST") && (
              <button className="btn-primary" disabled={mine.isPending} onClick={() => mine.mutate()}>
                <Sparkles className={`h-4 w-4 ${mine.isPending ? "animate-pulse" : ""}`} />
                Mine templates
              </button>
            )}
          </div>
        }
      />

      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label">Source filter</label>
            <input
              className="input"
              placeholder="e.g. application, linux…"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Minimum frequency</label>
            <input
              type="number"
              min={1}
              className="input"
              value={minFreq}
              onChange={(e) => setMinFreq(Math.max(1, Number(e.target.value)))}
            />
          </div>
        </div>
        {notice && <p className="mt-2 text-xs text-brand-fg">{notice}</p>}
      </Card>

      {q.isLoading ? (
        <Spinner label="Loading templates…" />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Tile label="Templates" value={q.data!.total} />
            <Tile label="Events Covered" value={q.data!.covered_events} />
            <Tile label="Unique Sources" value={q.data!.unique_sources} />
            <Tile label="Average Variables" value={q.data!.avg_variables.toFixed(2)} />
          </div>

          {q.data!.items.length === 0 ? (
            <EmptyState
              title="No templates yet"
              hint={
                hasRole("ANALYST")
                  ? "Ingest some logs, then click “Mine templates”."
                  : "Ask an analyst to run template mining."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-gray-500">
                  <tr>
                    <th className="py-2 pr-3">Template ID</th>
                    <th className="py-2 pr-3">Template</th>
                    <th className="py-2 pr-3 text-right">Frequency</th>
                    <th className="py-2 pr-3">Sources</th>
                    <th className="py-2 pr-3 text-right">Variables</th>
                    <th className="py-2 pr-3">First Seen</th>
                    <th className="py-2 pr-3">Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {q.data!.items.map((t) => (
                    <tr
                      key={t.id}
                      className="cursor-pointer border-t border-base-border hover:bg-white/5"
                      onClick={() => setSelected(t.template_key)}
                    >
                      <td className="py-2 pr-3 font-mono text-xs text-brand-fg">{t.template_key}</td>
                      <td className="max-w-md truncate py-2 pr-3 font-mono text-xs">{t.pattern}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{t.occurrences}</td>
                      <td className="py-2 pr-3">
                        <div className="flex flex-wrap gap-1">
                          {Object.keys(t.source_distribution).slice(0, 3).map((s) => (
                            <Badge key={s} tone="slate">{s}</Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{t.variable_count}</td>
                      <td className="py-2 pr-3 text-xs text-gray-400">
                        {new Date(t.first_seen).toLocaleString()}
                      </td>
                      <td className="py-2 pr-3 text-xs text-gray-400">
                        {new Date(t.last_seen).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {selected && <TemplateDrawer templateKey={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function TemplateDrawer({ templateKey, onClose }: { templateKey: string; onClose: () => void }) {
  const detail = useQuery({ queryKey: ["template", templateKey], queryFn: () => getTemplate(templateKey) });
  const examples = useQuery({
    queryKey: ["template-examples", templateKey],
    queryFn: () => getTemplateExamples(templateKey, 10),
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" onClick={onClose}>
      <div
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-base-border bg-base-panel p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="btn-ghost mb-3 py-1 text-xs" onClick={onClose}>Close</button>
        {detail.isLoading || !detail.data ? (
          <Spinner />
        ) : detail.isError ? (
          <ErrorState error={detail.error} onRetry={detail.refetch} />
        ) : (
          <>
            <h2 className="font-mono text-brand-fg">{detail.data.template_key}</h2>
            <div className="mt-1 mb-4 flex flex-wrap gap-2 text-xs text-gray-400">
              <Badge tone="slate">{detail.data.occurrences} occurrences</Badge>
              <Badge tone="slate">{detail.data.variable_count} variables</Badge>
              <Badge tone="slate">{detail.data.token_count} tokens</Badge>
            </div>

            <Section title="Template (variable positions highlighted)">
              <TemplatePattern
                literals={detail.data.literal_tokens}
                separators={detail.data.separators}
                trailing={detail.data.trailing}
                types={detail.data.variable_types}
              />
            </Section>

            <Section title="Source distribution">
              <div className="space-y-1">
                {Object.entries(detail.data.source_distribution)
                  .sort((a, b) => b[1] - a[1])
                  .map(([src, n]) => (
                    <div key={src} className="flex items-center gap-2 text-xs">
                      <span className="w-28 shrink-0 truncate text-gray-400">{src}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded bg-white/10">
                        <div
                          className="h-full bg-brand"
                          style={{ width: `${(n / detail.data!.occurrences) * 100}%` }}
                        />
                      </div>
                      <span className="w-10 text-right tabular-nums">{n}</span>
                    </div>
                  ))}
              </div>
            </Section>

            <Section title="First / last seen">
              <p className="text-xs text-gray-400">
                {new Date(detail.data.first_seen).toLocaleString()} —{" "}
                {new Date(detail.data.last_seen).toLocaleString()}
              </p>
            </Section>

            <Section title={`Examples (${examples.data?.length ?? 0})`}>
              {examples.isLoading ? (
                <Spinner />
              ) : (
                <div className="space-y-2">
                  {(examples.data ?? []).map((ex) => (
                    <div key={ex.raw_log_id} className="rounded border border-base-border p-2 text-xs">
                      <div className="mb-1 flex items-center gap-2 text-gray-500">
                        <Badge tone="slate">{ex.source}</Badge>
                        {ex.ts && <span>{new Date(ex.ts).toLocaleString()}</span>}
                      </div>
                      <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px] text-gray-300">
                        {ex.raw}
                      </pre>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {ex.variables.map((v, i) => (
                          <span
                            key={i}
                            className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] text-amber-300"
                          >
                            {v}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
      {children}
    </div>
  );
}
