import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { searchLogs, type LogFilters } from "@/services/endpoints";
import { Badge, EmptyState, ErrorState, PageHeader, Spinner } from "@/components/ui";
import { severityClass } from "@/utils/severity";
import EventDetail from "@/components/EventDetail";

const FILTER_FIELDS: { key: keyof LogFilters; label: string; placeholder: string }[] = [
  { key: "text", label: "Full text", placeholder: "search message / raw / host…" },
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

  return (
    <div>
      <PageHeader
        title="Log Explorer"
        subtitle="Search normalized events across every source. Under DETERMINISTIC_HASH, a raw IP / username you type is pseudonymized automatically so it matches stored events."
      />

      <div className="card mb-4">
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
          <button
            className="btn-ghost"
            onClick={() => {
              setDraft({});
              setApplied({});
              setPage(0);
            }}
          >
            Clear
          </button>
        </div>
      </div>

      {q.data?.note && (
        <p className="mb-2 text-xs text-brand-fg">ℹ {q.data.note}</p>
      )}

      {q.isLoading ? (
        <Spinner />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : q.data && q.data.items.length > 0 ? (
        <>
          <div className="mb-2 text-xs text-gray-500">
            {q.data.total} event(s) · page {page + 1} / {Math.max(1, Math.ceil(q.data.total / PAGE))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="py-2 pr-3">Time</th>
                  <th className="py-2 pr-3">Source</th>
                  <th className="py-2 pr-3">Event type</th>
                  <th className="py-2 pr-3">Host</th>
                  <th className="py-2 pr-3">User</th>
                  <th className="py-2 pr-3">Source IP</th>
                  <th className="py-2 pr-3">Sev</th>
                  <th className="py-2 pr-3">Parser</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((e) => (
                  <tr
                    key={e.id}
                    className="cursor-pointer border-t border-base-border hover:bg-white/5"
                    onClick={() => setSelected(e.id)}
                  >
                    <td className="whitespace-nowrap py-1.5 pr-3 text-xs text-gray-400">
                      {e.timestamp ? new Date(e.timestamp).toLocaleString() : "—"}
                    </td>
                    <td className="py-1.5 pr-3">
                      <Badge tone="slate">{e.source}</Badge>
                    </td>
                    <td className="py-1.5 pr-3">{e.event_type ?? "—"}</td>
                    <td className="py-1.5 pr-3 text-gray-400">{e.host ?? "—"}</td>
                    <td className="py-1.5 pr-3 font-mono text-xs">{e.username ?? "—"}</td>
                    <td className="py-1.5 pr-3 font-mono text-xs">{e.source_ip ?? "—"}</td>
                    <td className="py-1.5 pr-3">
                      {e.severity && (
                        <span className={`badge ${severityClass(e.severity)}`}>{e.severity}</span>
                      )}
                    </td>
                    <td className="py-1.5 pr-3 text-xs text-gray-500">{e.parser}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex gap-2">
            <button className="btn-ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <button
              className="btn-ghost"
              disabled={(page + 1) * PAGE >= q.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <EmptyState title="No events match" hint="Ingest some logs first, or widen your filters." />
      )}

      {selected && <EventDetail eventId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
