import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { searchLogs, type LogFilters } from "@/services/endpoints";
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

const FILTER_FIELDS: { key: keyof LogFilters; label: string; placeholder: string }[] = [
  { key: "text", label: "Full text", placeholder: "message / raw / host…" },
  { key: "source", label: "Source", placeholder: "linux, firewall…" },
  { key: "source_ip", label: "Source IP", placeholder: "raw IP or IP_… token" },
  { key: "username", label: "Username", placeholder: "raw or USER_… token" },
  { key: "event_type", label: "Event type", placeholder: "authentication_failure" },
  { key: "severity", label: "Severity", placeholder: "high" },
  { key: "host", label: "Host", placeholder: "db-02" },
  { key: "parser", label: "Parser", placeholder: "linux_auth" },
];

const PAGE = 50;

export default function LogExplorerPage() {
  const [draft, setDraft] = useState<LogFilters>({});
  const [applied, setApplied] = useState<LogFilters>({});
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

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
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {FILTER_FIELDS.map((f) => (
            <div key={f.key}>
              <label className="label">{f.label}</label>
              <input
                className="input"
                placeholder={f.placeholder}
                value={(draft[f.key] as string) ?? ""}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && apply()}
              />
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button className="btn-primary" onClick={apply}>
            <Search className="h-4 w-4" /> Search
          </button>
          <button className="btn-ghost" onClick={clearAll}>
            Clear
          </button>
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
                <th>Source</th>
                <th>Event type</th>
                <th>Host</th>
                <th>Identity</th>
                <th>Source IP</th>
                <th>Severity</th>
                <th>Parser</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => setSelected(e.id)}>
                  <td className="whitespace-nowrap text-xs text-gray-400" title={e.timestamp ?? ""}>
                    {relTime(e.timestamp)}
                  </td>
                  <td className="text-xs text-gray-300">{e.source}</td>
                  <td className="text-xs">{e.event_type ?? "—"}</td>
                  <td className="text-xs text-gray-400">{e.host ?? "—"}</td>
                  <td className="font-mono text-2xs text-gray-400">{e.username ?? e.email ?? "—"}</td>
                  <td className="font-mono text-2xs text-gray-400">{e.source_ip ?? "—"}</td>
                  <td>{e.severity ? <StatusPill status={e.severity} /> : "—"}</td>
                  <td className="text-2xs text-gray-500">{e.parser}</td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          <div className="mt-3 flex gap-2 text-xs">
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
