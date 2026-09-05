import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { createSource, deleteSource, listAdapters, listSources } from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  Kpi,
  KpiGrid,
  LiveDot,
  PageHeader,
  SectionHeader,
  SkeletonTable,
  StatusPill,
  relTime,
} from "@/components/ui";

const CATEGORIES = ["linux", "windows", "apache", "nginx", "firewall", "network", "application", "generic"];

export default function SourcesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const isAdmin = hasRole("ADMIN");
  const [showForm, setShowForm] = useState(false);

  const sources = useQuery({ queryKey: ["sources"], queryFn: listSources, refetchInterval: 15000 });
  const adapters = useQuery({ queryKey: ["adapters"], queryFn: listAdapters });

  const del = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  const items = sources.data ?? [];
  const receiving = items.filter((s) => s.connection_status === "RECEIVING").length;
  const totalEvents = items.reduce((a, s) => a + s.events_processed, 0);

  return (
    <div>
      <PageHeader
        eyebrow="System"
        title="Log Sources"
        subtitle="Where logs come from. The MVP genuinely supports file upload, sample import and a simulated stream; enterprise connectors expose the interface but report NOT_CONFIGURED until wired up."
        actions={
          <div className="flex items-center gap-3">
            <LiveDot />
            {isAdmin && (
              <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
                <Plus className="h-4 w-4" /> New source
              </button>
            )}
          </div>
        }
      />

      <div className="mb-5">
        <KpiGrid>
          <Kpi label="Sources" value={items.length} loading={sources.isLoading} />
          <Kpi label="Receiving" value={receiving} status={receiving ? "online" : "idle"} loading={sources.isLoading} />
          <Kpi label="Events processed" value={totalEvents.toLocaleString()} loading={sources.isLoading} />
          <Kpi label="Adapters available" value={adapters.data?.filter((a) => a.mvp_supported).length ?? 0} />
        </KpiGrid>
      </div>

      {showForm && isAdmin && (
        <SourceForm
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["sources"] });
          }}
        />
      )}

      <SectionHeader title="Configured sources" />
      {sources.isLoading ? (
        <SkeletonTable rows={4} cols={6} />
      ) : sources.isError ? (
        <ErrorState error={sources.error} onRetry={sources.refetch} />
      ) : items.length > 0 ? (
        <DataTable>
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Adapter</th>
              <th>Status</th>
              <th className="text-right">Events</th>
              <th>Last activity</th>
              {isAdmin && <th />}
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td className="font-medium text-gray-200">{s.name}</td>
                <td className="text-gray-400">{s.category}</td>
                <td className="text-gray-400">{s.adapter}</td>
                <td>
                  <StatusPill status={s.connection_status} />
                </td>
                <td className="text-right tnum">{s.events_processed.toLocaleString()}</td>
                <td className="text-xs text-gray-500">{relTime(s.last_received_at)}</td>
                {isAdmin && (
                  <td className="text-right">
                    <button
                      className="text-gray-500 hover:text-sev-critical"
                      onClick={() => del.mutate(s.id)}
                      aria-label={`Delete ${s.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </DataTable>
      ) : (
        <EmptyState
          title="No sources configured"
          hint={isAdmin ? "Create one above, or just upload a file on the Ingestion page." : "Ask an admin to add a source."}
        />
      )}

      <div className="mt-8">
        <SectionHeader title="Adapter catalog" hint="Connector interfaces ULPF exposes" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {adapters.data?.map((a) => (
            <Card key={a.kind}>
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-200">{a.kind}</span>
                <StatusPill
                  status={a.mvp_supported ? "online" : "idle"}
                  label={a.mvp_supported ? "MVP READY" : a.status}
                  dot={false}
                />
              </div>
              <p className="mt-2 text-xs text-gray-400">{a.detail}</p>
              <p className="mt-1 text-2xs text-gray-600">Needs: {a.requires}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function SourceForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("linux");
  const [adapter, setAdapter] = useState("FILE");
  const [description, setDescription] = useState("");
  const [err, setErr] = useState("");

  const create = useMutation({
    mutationFn: () => createSource({ name, category, adapter, description }),
    onSuccess: onDone,
    onError: (e) => setErr(apiError(e)),
  });

  return (
    <Card className="mb-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label">Category</label>
          <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Adapter</label>
          <select className="input" value={adapter} onChange={(e) => setAdapter(e.target.value)}>
            {["FILE", "SIMULATED", "SYSLOG", "HTTP", "WINDOWS", "FIREWALL"].map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Description</label>
          <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
      </div>
      {err && <p className="mt-2 text-sm text-sev-critical">{err}</p>}
      <div className="mt-3 flex gap-2">
        <button className="btn-primary" disabled={!name || create.isPending} onClick={() => create.mutate()}>
          Create
        </button>
        <button className="btn-ghost" onClick={onDone}>
          Cancel
        </button>
      </div>
    </Card>
  );
}
