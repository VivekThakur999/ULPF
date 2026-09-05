import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import {
  Activity,
  BarChart3,
  Bug,
  ChevronLeft,
  Database,
  FileStack,
  Gauge,
  LayoutTemplate,
  ListChecks,
  LogOut,
  Package,
  ScrollText,
  Search,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { listAlerts } from "@/services/endpoints";
import { StatusPill, Tooltip } from "@/components/ui";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Search;
  end?: boolean;
}

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [
      { to: "/", label: "Command Center", icon: Gauge, end: true },
      { to: "/explorer", label: "Log Explorer", icon: Search },
      { to: "/alerts", label: "Alerts", icon: Siren },
      { to: "/incidents", label: "Incidents", icon: ShieldAlert },
    ],
  },
  {
    title: "Pipeline",
    items: [
      { to: "/ingestion", label: "Ingestion", icon: FileStack },
      { to: "/debugger", label: "Pipeline Debugger", icon: Bug },
      { to: "/parsers", label: "Parser Packs", icon: Package },
      { to: "/templates", label: "Templates", icon: LayoutTemplate },
      { to: "/compression", label: "Compression", icon: Waypoints },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { to: "/assistant", label: "AI Assistant", icon: Sparkles },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    title: "Response",
    items: [{ to: "/response", label: "Response Simulator", icon: Activity }],
  },
  {
    title: "System",
    items: [
      { to: "/sources", label: "Sources", icon: Database },
      { to: "/jobs", label: "Processing Jobs", icon: ListChecks },
      { to: "/privacy", label: "Privacy", icon: ShieldCheck },
      { to: "/audit", label: "Audit Trail", icon: ScrollText },
    ],
  },
];

const ALL_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

function useBackendHealth() {
  return useQuery({
    queryKey: ["health-pill"],
    queryFn: async () => (await axios.get("/health")).data as { status: string; database: string },
    refetchInterval: 20000,
    retry: false,
  });
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const health = useBackendHealth();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("ulpf.sidebar") === "collapsed";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("ulpf.sidebar", collapsed ? "collapsed" : "expanded");
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  const activeAlerts = useQuery({
    queryKey: ["nav-active-alerts"],
    queryFn: () => listAlerts({ status: "NEW" }),
    refetchInterval: 20000,
    retry: false,
  });

  const current =
    ALL_ITEMS.find((i) => (i.end ? location.pathname === i.to : location.pathname.startsWith(i.to))) ??
    { label: "" };

  return (
    <div className="flex min-h-screen bg-base-bg">
      <aside
        className={`flex shrink-0 flex-col border-r border-base-border bg-base-panel transition-[width] duration-200 ${
          collapsed ? "w-[64px]" : "w-60"
        }`}
      >
        {/* brand */}
        <div className="flex h-14 items-center gap-2.5 border-b border-base-border px-4">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-brand/30 bg-brand/10">
            <ShieldCheck className="h-4 w-4 text-brand-fg" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-tight text-gray-50">ULPF</div>
              <div className="truncate text-[10px] uppercase tracking-[0.16em] text-gray-600">
                Universal Log Pre-processing
              </div>
            </div>
          )}
        </div>

        {/* nav */}
        <nav className="flex-1 space-y-5 overflow-y-auto overflow-x-hidden px-2 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              {!collapsed && (
                <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-gray-600">
                  {group.title}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map(({ to, label, icon: Icon, end }) => {
                  const link = (
                    <NavLink
                      key={to}
                      to={to}
                      end={end}
                      className={({ isActive }) =>
                        `group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors ${
                          isActive
                            ? "bg-brand/12 text-brand-fg"
                            : "text-gray-400 hover:bg-white/[0.04] hover:text-gray-200"
                        } ${collapsed ? "justify-center" : ""}`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-brand" />
                          )}
                          <Icon className="h-4 w-4 shrink-0" />
                          {!collapsed && <span className="truncate">{label}</span>}
                          {!collapsed && to === "/alerts" && (activeAlerts.data?.total ?? 0) > 0 && (
                            <span className="ml-auto rounded-full bg-sev-critical/20 px-1.5 text-[10px] font-semibold text-red-300">
                              {activeAlerts.data!.total}
                            </span>
                          )}
                        </>
                      )}
                    </NavLink>
                  );
                  return collapsed ? (
                    <Tooltip key={to} label={label}>
                      {link}
                    </Tooltip>
                  ) : (
                    link
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center justify-center gap-2 border-t border-base-border py-2.5 text-2xs font-medium text-gray-500 hover:text-gray-300"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronLeft className={`h-3.5 w-3.5 transition-transform ${collapsed ? "rotate-180" : ""}`} />
          {!collapsed && "Collapse"}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="glass sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-base-border px-6">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-gray-500">ULPF</span>
            <span className="text-gray-700">/</span>
            <span className="font-medium text-gray-200">{current.label}</span>
          </div>

          <div className="flex items-center gap-4">
            {(activeAlerts.data?.total ?? 0) > 0 && (
              <NavLink to="/alerts" className="hidden items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 sm:flex">
                <Siren className="h-3.5 w-3.5 text-sev-high" />
                <span className="font-semibold text-gray-200">{activeAlerts.data!.total}</span> active
              </NavLink>
            )}
            <StatusPill
              status={health.isError ? "error" : health.data?.status === "ok" ? "online" : "processing"}
              label={
                health.isLoading
                  ? "connecting…"
                  : health.isError
                    ? "backend offline"
                    : `backend ${health.data?.status} · db ${health.data?.database}`
              }
            />
            <div className="flex items-center gap-2.5 border-l border-base-border pl-4">
              <div className="hidden text-right sm:block">
                <div className="max-w-[160px] truncate text-xs font-medium text-gray-200">
                  {user?.full_name || user?.email}
                </div>
                <div className="text-2xs uppercase tracking-wide text-gray-500">{user?.role}</div>
              </div>
              <div className="grid h-8 w-8 place-items-center rounded-full border border-base-border bg-base-panel-2 text-2xs font-semibold text-gray-300">
                {(user?.email ?? "?").slice(0, 2).toUpperCase()}
              </div>
              <button
                onClick={logout}
                aria-label="Sign out"
                className="rounded-lg border border-base-border bg-base-panel-2 p-1.5 text-gray-400 hover:text-gray-200"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] animate-fade-in-up p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
