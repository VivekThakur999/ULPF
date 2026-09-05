import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  Bug,
  Database,
  FileStack,
  LayoutDashboard,
  LogOut,
  LayoutTemplate,
  Package,
  Search,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Badge } from "@/components/ui";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  end?: boolean;
}

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard, end: true }],
  },
  {
    title: "Pipeline",
    items: [
      { to: "/sources", label: "Log Sources", icon: Database },
      { to: "/ingestion", label: "Ingestion", icon: FileStack },
      { to: "/explorer", label: "Log Explorer", icon: Search },
      { to: "/debugger", label: "Pipeline Debugger", icon: Bug },
    ],
  },
  {
    title: "Security",
    items: [
      { to: "/alerts", label: "Alerts", icon: AlertTriangle },
      { to: "/response", label: "Response Simulator", icon: Activity },
    ],
  },
  {
    title: "Platform",
    items: [
      { to: "/parsers", label: "Parser Packs", icon: Package },
      { to: "/templates", label: "Templates", icon: LayoutTemplate },
      { to: "/compression", label: "Compression", icon: Waypoints },
      { to: "/privacy", label: "Privacy", icon: ShieldCheck },
      { to: "/assistant", label: "AI Assistant", icon: Sparkles },
    ],
  },
];

const ALL_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

function useBackendHealth() {
  return useQuery({
    queryKey: ["health-pill"],
    queryFn: async () => (await axios.get("/health")).data as { status: string; database: string },
    refetchInterval: 15000,
    retry: false,
  });
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const health = useBackendHealth();
  const current = ALL_ITEMS.find((i) => (i.end ? location.pathname === i.to : location.pathname.startsWith(i.to)));

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-base-border bg-base-panel">
        <div className="flex items-center gap-2 border-b border-base-border px-4 py-4">
          <ShieldCheck className="h-6 w-6 text-brand-fg" />
          <div>
            <div className="text-sm font-semibold">ULPF</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">
              Log Pre-processing
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto p-2 pt-3">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                {group.title}
              </div>
              <div className="space-y-0.5">
                {group.items.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition ${
                        isActive ? "bg-brand/15 text-brand-fg" : "text-gray-300 hover:bg-white/5"
                      }`
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="border-t border-base-border p-3 text-xs">
          <div className="truncate text-gray-300">{user?.full_name || user?.email}</div>
          <div className="mb-2 text-gray-500">{user?.role}</div>
          <button onClick={logout} className="btn-ghost w-full justify-center py-1.5 text-xs">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-base-border bg-base-panel/60 px-6">
          <span className="text-sm font-medium text-gray-300">{current?.label ?? ""}</span>
          <div className="flex items-center gap-3">
            <Badge tone={health.data?.status === "ok" ? "green" : health.isError ? "red" : "slate"}>
              {health.isLoading
                ? "checking backend…"
                : health.isError
                  ? "backend unreachable"
                  : `backend ${health.data?.status} · db ${health.data?.database}`}
            </Badge>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
