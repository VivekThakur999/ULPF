import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Sparkles } from "lucide-react";
import { getTemplate, getTemplateExamples, listTemplates, mineTemplates } from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Badge,
  Card,
  DataTable,
  Drawer,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  SectionHeader,
  SkeletonTable,
  Spinner,
  relTime,
} from "@/components/ui";
import TemplatePattern from "@/components/TemplatePattern";

export default function TemplatesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const [source, setSource] = useState("");
  const [minFreq, setMinFreq] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  const params = { source: source || undefined, min_frequency: minFreq, limit: 200 };
  const q = useQuery({ queryKey: ["templates", params], queryFn: () => listTemplates(params) });

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
      <PageHeaderRow
        onRefresh={() => q.refetch()}
        canMine={hasRole("ANALYST")}
        mining={mine.isPending}
        onMine={() => mine.mutate()}
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
        <SkeletonTable rows={8} cols={5} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <>
          <div className="mb-5">
            <KpiGrid>
              <Kpi label="Templates" value={q.data!.total} />
              <Kpi label="Events covered" value={q.data!.covered_events} />
              <Kpi label="Unique sources" value={q.data!.unique_sources} />
              <Kpi label="Average variables" value={q.data!.avg_variables.toFixed(2)} />
            </KpiGrid>
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
            <DataTable>
              <thead>
                <tr>
                  <th>Template ID</th>
                  <th>Pattern</th>
                  <th className="text-right">Frequency</th>
                  <th>Sources</th>
                  <th className="text-right">Variables</th>
                  <th>Last seen</th>
                </tr>
              </thead>
              <tbody>
                {q.data!.items.map((t) => (
                  <tr key={t.id} className="clickable" onClick={() => setSelected(t.template_key)}>
                    <td className="font-mono text-xs text-brand-fg">{t.template_key}</td>
                    <td className="max-w-md truncate font-mono text-xs">{t.pattern}</td>
                    <td className="text-right tnum">{t.occurrences}</td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(t.source_distribution).slice(0, 3).map((s) => (
                          <Badge key={s} tone="slate">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="text-right tnum">{t.variable_count}</td>
                    <td className="text-xs text-gray-500">{relTime(t.last_seen)}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </>
      )}

      {selected && <TemplateDrawer templateKey={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function PageHeaderRow({
  onRefresh,
  canMine,
  mining,
  onMine,
}: {
  onRefresh: () => void;
  canMine: boolean;
  mining: boolean;
  onMine: () => void;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div className="mb-1 text-2xs font-semibold uppercase tracking-[0.18em] text-brand-fg/80">Pipeline</div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Template Explorer</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-500">
          Discover recurring structures across heterogeneous logs. Templates are mined from the real
          ingested raw logs; every occurrence stays reconstructable.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button className="btn-ghost" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
        {canMine && (
          <button className="btn-primary" disabled={mining} onClick={onMine}>
            <Sparkles className={`h-4 w-4 ${mining ? "animate-pulse" : ""}`} /> Mine templates
          </button>
        )}
      </div>
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
    <Drawer open onClose={onClose} title={templateKey} subtitle="Mined template">
      {detail.isLoading || !detail.data ? (
        <Spinner />
      ) : detail.isError ? (
        <ErrorState error={detail.error} onRetry={detail.refetch} />
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge tone="slate">{detail.data.occurrences} occurrences</Badge>
            <Badge tone="slate">{detail.data.variable_count} variables</Badge>
            <Badge tone="slate">{detail.data.token_count} tokens</Badge>
          </div>

          <section>
            <SectionHeader title="Template — variable positions highlighted" />
            <TemplatePattern
              literals={detail.data.literal_tokens}
              separators={detail.data.separators}
              trailing={detail.data.trailing}
              types={detail.data.variable_types}
            />
          </section>

          <section>
            <SectionHeader title="Source distribution" />
            <div className="space-y-1">
              {Object.entries(detail.data.source_distribution)
                .sort((a, b) => b[1] - a[1])
                .map(([src, n]) => (
                  <div key={src} className="flex items-center gap-2 text-xs">
                    <span className="w-28 shrink-0 truncate text-gray-400">{src}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded bg-slate-100">
                      <div
                        className="h-full bg-brand"
                        style={{ width: `${(n / detail.data!.occurrences) * 100}%` }}
                      />
                    </div>
                    <span className="w-10 text-right tnum">{n}</span>
                  </div>
                ))}
            </div>
          </section>

          <section>
            <SectionHeader title="First / last seen" />
            <p className="text-xs text-gray-400">
              {new Date(detail.data.first_seen).toLocaleString()} —{" "}
              {new Date(detail.data.last_seen).toLocaleString()}
            </p>
          </section>

          <section>
            <SectionHeader title={`Matching examples (${examples.data?.length ?? 0})`} />
            {examples.isLoading ? (
              <Spinner />
            ) : (
              <div className="space-y-2">
                {(examples.data ?? []).map((ex) => (
                  <div key={ex.raw_log_id} className="surface-2 p-2 text-xs">
                    <div className="mb-1 flex items-center gap-2 text-gray-500">
                      <Badge tone="slate">{ex.source}</Badge>
                      {ex.ts && <span>{new Date(ex.ts).toLocaleString()}</span>}
                    </div>
                    <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-2xs text-slate-800">
                      {ex.raw}
                    </pre>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {ex.variables.map((v, i) => (
                        <span
                          key={i}
                          className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-[10px] text-amber-900"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </Drawer>
  );
}
