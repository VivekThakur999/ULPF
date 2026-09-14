import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { logStats, searchLogs, type LogFilters } from "@/services/endpoints";
import EventDetail from "@/components/EventDetail";
import {
  DataTable,
  EmptyState,
  ErrorState,
  FilterChips,
  PageHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";

/** Filters backed by real facet counts from /logs/stats — rendered as selects. */
const FACET_FIELDS: { key: keyof LogFilters; label: string }[] = [
  { key: "source", label: "Source" },
  { key: "host", label: "Host" },
  { key: "event_type", label: "Event type" },
  { key: "severity", label: "Severity" },
  { key: "parser", label: "Parser" },
  { key: "processing_status", label: "Processing status" },
];

/** Free-text filters — no fixed enum of values on the backend. */
const TEXT_FIELDS: { key: keyof LogFilters; label: string; placeholder: string }[] = [
  { key: "source_ip", label: "Source IP", placeholder: "raw IP or IP_… token" },
  { key: "username", label: "Identity", placeholder: "raw or USER_… token" },
];

const PAGE = 50;

export default function LogExplorerPage() {
  const [draft, setDraft] = useState<LogFilters>({});
  const [applied, setApplied] = useState<LogFilters>({});
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

  const stats = useQuery({ queryKey: ["log-stats"], queryFn: logStats, refetchInterval: 30000 });
  const q = useQuery({
    queryKey: ["logs", applied, page],
    queryFn: () => searchLogs({ ...applied, limit: PAGE, offset: page * PAGE }),
    placeholderData: keepPreviousData,
  });

  const apply = () => {
    setPage(0);
    setApplied(Object.fromEntries(Object.entries(draft).filter(([, v]) => v)));
  };
  const clearAll = () => {
    setDraft({});
    setApplied({});
    setPage(0);
  };
  const removeFilter = (key: string) => {
    const next = { ...applied };
    delete next[key as keyof LogFilters];
    setApplied(next);
    setDraft(next);
    setPage(0);
  };
  const setFacet = (key: keyof LogFilters, value: string) => {
    const next = { ...draft, [key]: value || undefined };
    setDraft(next);
    setApplied(Object.fromEntries(Object.entries(next).filter(([, v]) => v)));
    setPage(0);
  };

  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Log Explorer"
        subtitle="Search normalized events across every source. Under DETERMINISTIC_HASH, a raw IP or username you type is pseudonymized automatically so it matches stored events."
      />

      <div className="surface bg-surface-sheen mb-4 p-4">
        {/* Full-text search bar — the primary way to query the corpus */}
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="input pl-9 font-mono"
              placeholder="search message, raw log, host…"
              value={draft.text ?? ""}
              onChange={(e) => setDraft({ ...draft, text: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && apply()}
            />
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-primary" onClick={apply}>
              Search
            </button>
            <button className="btn-ghost" onClick={clearAll}>
              Clear
            </button>
          </div>
        </div>

        {/* Facet filters — real values + counts from /logs/stats */}
        <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {FACET_FIELDS.map((f) => {
            const options = stats.data?.facets[f.key as string] ?? [];
            const id = `filter-${f.key}`;
            return (
              <div key={f.key}>
                <label className="label" htmlFor={id}>{f.label}</label>
                <select
                  id={id}
                  className="input"
                  value={(draft[f.key] as string) ?? ""}
                  onChange={(e) => setFacet(f.key, e.target.value)}
                >
                  <option value="">All {f.label.toLowerCase()}s</option>
                  {options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.value} ({o.count})
                    </option>
                  ))}
                </select>
              </div>
            );
          })}
          {TEXT_FIELDS.map((f) => {
            const id = `filter-${f.key}`;
            return (
              <div key={f.key}>
                <label className="label" htmlFor={id}>{f.label}</label>
                <input
                  id={id}
                  className="input"
                  placeholder={f.placeholder}
                  value={(draft[f.key] as string) ?? ""}
                  onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                  onKeyDown={(e) => e.key === "Enter" && apply()}
                />
              </div>
            );
          })}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <FilterChips filters={applied as Record<string, unknown>} onRemove={removeFilter} onClear={clearAll} />
        {q.data && (
          <span className="text-xs text-gray-500">
            {total.toLocaleString()} event{total === 1 ? "" : "s"} · page {page + 1} / {pages}
          </span>
        )}
      </div>

      {q.data?.note && <p className="mb-2 text-xs text-brand-fg">ℹ {q.data.note}</p>}

      {q.isLoading ? (
        <SkeletonTable rows={10} cols={7} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : q.data && q.data.items.length > 0 ? (
        <>
          <DataTable>
            <thead>
              <tr>
                <th>Time</th>
                <th>Host / Source</th>
                <th>Event signature</th>
                <th className="hidden lg:table-cell">Identity</th>
                <th>Source IP</th>
                <th className="hidden lg:table-cell">Destination IP</th>
                <th>Severity</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => setSelected(e.id)}>
                  <td className="whitespace-nowrap font-mono text-2xs text-slate-500" title={e.timestamp ?? ""}>
                    {relTime(e.timestamp)}
                  </td>
                  <td>
                    <div className="text-xs font-semibold text-slate-800">{e.host ?? "—"}</div>
                    <div className="text-2xs text-slate-500">{e.source}</div>
                  </td>
                  <td>
                    <div className="text-xs text-slate-800">{e.event_type ?? "—"}</div>
                    {(e.action || e.status) && (
                      <div className="text-2xs text-slate-500">
                        {[e.action, e.status].filter(Boolean).join(" · ")}
                      </div>
                    )}
                  </td>
                  <td className="hidden font-mono text-2xs text-slate-500 lg:table-cell">
                    {e.username ?? e.email ?? "—"}
                  </td>
                  <td className="font-mono text-2xs text-slate-500">{e.source_ip ?? "—"}</td>
                  <td className="hidden font-mono text-2xs text-slate-500 lg:table-cell">
                    {e.destination_ip ?? "—"}
                  </td>
                  <td>{e.severity ? <StatusPill status={e.severity} /> : "—"}</td>
                  <td>{e.processing_status ? <StatusPill status={e.processing_status} dot={false} /> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-gray-500">
              Showing {page * PAGE + 1}–{Math.min(total, (page + 1) * PAGE)} of {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button className="btn-ghost py-1" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                Previous
              </button>
              <button
                className="btn-ghost py-1"
                disabled={(page + 1) * PAGE >= total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      ) : (
        <EmptyState
          title={Object.keys(applied).length > 0 ? "No events match these filters" : "No events yet"}
          hint={
            Object.keys(applied).length > 0
              ? "Try clearing a filter or widening the time range."
              : "Ingest a file or sample on the Ingestion page to populate the explorer."
          }
        />
      )}

      {selected && <EventDetail eventId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
