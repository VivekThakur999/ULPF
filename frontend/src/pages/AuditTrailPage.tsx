import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";
import { listAuditLogs } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import {
  Badge,
  DataTable,
  EmptyState,
  ErrorState,
  FilterChips,
  LiveDot,
  PageHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";

const SENSITIVE = new Set([
  "auth.login_failed",
  "user.delete",
  "user.update",
  "user.create",
  "privacy.settings_update",
  "rule.update",
  "response.simulate",
  "parser.pack_create",
  "source.delete",
]);

const PAGE = 100;

export default function AuditTrailPage() {
  const { hasRole } = useAuth();
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);

  const q = useQuery({
    queryKey: ["audit", action, page],
    queryFn: () => listAuditLogs({ action: action || undefined, limit: PAGE, offset: page * PAGE }),
    enabled: hasRole("ADMIN"),
    refetchInterval: 30000,
  });

  if (!hasRole("ADMIN")) {
    return (
      <div>
        <PageHeader eyebrow="System" title="Audit Trail" />
        <EmptyState
          icon={ShieldAlert}
          title="Administrator access required"
          hint="The audit trail records security-sensitive actions and is visible to ADMIN users only."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="System"
        title="Audit Trail"
        subtitle="Every security-sensitive action — authentication, user & role changes, privacy and detection-rule configuration, alert triage and response simulations."
        actions={<LiveDot />}
      />

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <input
          className="input max-w-xs"
          placeholder="filter by action, e.g. auth.login"
          value={action}
          onChange={(e) => {
            setPage(0);
            setAction(e.target.value.trim());
          }}
        />
        <FilterChips
          filters={action ? { action } : {}}
          onRemove={() => setAction("")}
          onClear={() => setAction("")}
        />
        {q.data && <span className="ml-auto text-xs text-gray-500">{q.data.total} entries</span>}
      </div>

      {q.isLoading ? (
        <SkeletonTable rows={10} cols={6} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (q.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="No audit entries" hint="Actions will appear here as users work in ULPF." />
      ) : (
        <>
          <DataTable>
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Detail</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {q.data!.items.map((row) => {
                const sensitive = SENSITIVE.has(row.action) || row.action.includes("failed");
                return (
                  <tr key={row.id}>
                    <td className="whitespace-nowrap text-xs text-gray-400">
                      <span title={new Date(row.ts).toLocaleString()}>{relTime(row.ts)}</span>
                    </td>
                    <td className="text-xs">{row.actor_email ?? <span className="text-gray-600">system</span>}</td>
                    <td>
                      {sensitive ? (
                        <StatusPill status="high" label={row.action} dot />
                      ) : (
                        <Badge tone="slate">{row.action}</Badge>
                      )}
                    </td>
                    <td className="text-xs text-gray-400">
                      {row.target_type ? `${row.target_type} ${(row.target_id ?? "").slice(0, 8)}` : "—"}
                    </td>
                    <td className="max-w-md truncate text-xs text-gray-400" title={row.detail}>
                      {row.detail || "—"}
                    </td>
                    <td className="font-mono text-2xs text-gray-500">{row.ip_address ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
          <div className="mt-3 flex items-center gap-2 text-xs">
            <button className="btn-ghost py-1" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <button
              className="btn-ghost py-1"
              disabled={(page + 1) * PAGE >= (q.data?.total ?? 0)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
            <span className="text-gray-600">page {page + 1}</span>
          </div>
        </>
      )}
    </div>
  );
}
