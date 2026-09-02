import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";

interface Health {
  status: string;
  version: string;
  environment: string;
  database: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: async () => (await axios.get<Health>("/health")).data,
    refetchInterval: 15000,
  });

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Dashboard</h1>
      <p className="mb-6 text-sm text-gray-400">
        Signed in as {user?.email} ({user?.role}). Full metrics dashboard arrives in Phase 14 -
        the tiles below reflect real backend state only.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Backend" value={isLoading ? "…" : isError ? "unreachable" : data?.status ?? "?"} />
        <Tile label="Database" value={isLoading ? "…" : isError ? "?" : data?.database ?? "?"} />
        <Tile label="API version" value={data?.version ?? "—"} />
        <Tile label="Environment" value={data?.environment ?? "—"} />
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-gray-400">{label}</div>
      <div className="mt-1 text-lg font-semibold capitalize">{value}</div>
    </div>
  );
}
