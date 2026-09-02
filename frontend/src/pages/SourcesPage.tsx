import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import {
  createSource,
  deleteSource,
  listAdapters,
  listSources,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  statusTone,
} from "@/components/ui";

const CATEGORIES = [
  "linux", "windows", "apache", "nginx", "firewall", "network", "application", "generic",
];

export default function SourcesPage() {
  const { hasRole } = useAuth();
  const qc = useQueryClient();
  const isAdmin = hasRole("ADMIN");
  const [showForm, setShowForm] = useState(false);

  const sources = useQuery({ queryKey: ["sources"], queryFn: listSources });
  const adapters = useQuery({ queryKey: ["adapters"], queryFn: listAdapters });

  const del = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  return (
    <div>
      <PageHeader
        title="Log Sources"
        subtitle="Configure where logs come from. The MVP genuinely supports file upload, sample import and a simulated stream; enterprise connectors expose the interface but report NOT_CONFIGURED until wired up."
        actions={
          isAdmin && (
            <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
              <Plus className="h-4 w-4" /> New source
            </button>
          )
        }
      />

      {showForm && isAdmin && (
        <SourceForm
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["sources"] });
          }}
        />
      )}

      <h2 className="mb-2 mt-2 text-sm font-semibold text-gray-300">Configured sources</h2>
      {sources.isLoading ? (
        <Spinner />
      ) : sources.isError ? (
        <ErrorState error={sources.error} />
      ) : sources.data && sources.data.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Category</th>
                <th className="py-2 pr-4">Adapter</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Events</th>
                <th className="py-2 pr-4">Last received</th>
                {isAdmin && <th />}
              </tr>
            </thead>
            <tbody>
              {sources.data.map((s) => (
                <tr key={s.id} className="border-t border-base-border">
                  <td className="py-2 pr-4 font-medium">{s.name}</td>
                  <td className="py-2 pr-4 text-gray-400">{s.category}</td>
                  <td className="py-2 pr-4">{s.adapter}</td>
                  <td className="py-2 pr-4">
                    <Badge tone={s.connection_status === "CONFIGURED" ? "slate" : statusTone(s.connection_status)}>
                      {s.connection_status}
                    </Badge>
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{s.events_processed}</td>
                  <td className="py-2 pr-4 text-gray-400">
                    {s.last_received_at ? new Date(s.last_received_at).toLocaleString() : "—"}
                  </td>
                  {isAdmin && (
                    <td className="py-2 text-right">
                      <button
                        className="text-gray-500 hover:text-sev-critical"
                        onClick={() => del.mutate(s.id)}
                        title="Delete source"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No sources configured" hint={isAdmin ? "Create one above, or just upload a file on the Ingestion page." : "Ask an admin to add a source."} />
      )}

      <h2 className="mb-2 mt-8 text-sm font-semibold text-gray-300">Adapter catalog</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {adapters.data?.map((a) => (
          <Card key={a.kind}>
            <div className="flex items-center justify-between">
              <span className="font-medium">{a.kind}</span>
              <Badge tone={a.mvp_supported ? "green" : "slate"}>
                {a.mvp_supported ? "MVP READY" : a.status}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-gray-400">{a.detail}</p>
            <p className="mt-1 text-xs text-gray-600">Needs: {a.requires}</p>
          </Card>
        ))}
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
          <input
            className="input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
      {err && <p className="mt-2 text-sm text-sev-critical">{err}</p>}
      <div className="mt-3 flex gap-2">
        <button
          className="btn-primary"
          disabled={!name || create.isPending}
          onClick={() => create.mutate()}
        >
          Create
        </button>
        <button className="btn-ghost" onClick={onDone}>
          Cancel
        </button>
      </div>
    </Card>
  );
}
