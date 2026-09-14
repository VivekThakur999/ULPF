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

  const operational = !health.isError && health.data?.status === "ok";

  return (
    <div className="flex min-h-screen bg-base-bg">
      <aside
        className={`flex shrink-0 flex-col bg-nav-bg transition-[width] duration-200 ${
          collapsed ? "w-[64px]" : "w-60"
        }`}
      >
        {/* brand */}
        <div className="flex h-14 items-center gap-2.5 border-b border-nav-border px-4">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand/20">
            <ShieldCheck className="h-4 w-4 text-blue-300" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-tight text-white">ULPF</div>
              <div className="truncate text-[10px] uppercase tracking-[0.16em] text-nav-text/90">
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
                <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-nav-text/80">
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
                            ? "bg-brand/25 text-nav-text-active"
                            : "text-nav-text hover:bg-white/5 hover:text-nav-text-active"
                        } ${collapsed ? "justify-center" : ""}`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r bg-blue-400" />
                          )}
                          <Icon className="h-4 w-4 shrink-0" />
                          {!collapsed && <span className="truncate">{label}</span>}
                          {!collapsed && to === "/alerts" && (activeAlerts.data?.total ?? 0) > 0 && (
                            <span className="ml-auto rounded-full bg-red-500/25 px-1.5 text-[10px] font-semibold text-red-300">
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

        <div className="border-t border-nav-border px-3 py-3">
          <div className="mb-1 flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              {operational && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
              )}
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${operational ? "bg-emerald-400" : "bg-red-400"}`}
              />
            </span>
            {!collapsed && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-nav-text-active">
                {operational ? "System operational" : "Backend unreachable"}
              </span>
            )}
          </div>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="mt-1 flex w-full items-center justify-center gap-2 rounded-lg py-1.5 text-2xs font-medium text-nav-text hover:bg-white/5 hover:text-nav-text-active"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <ChevronLeft className={`h-3.5 w-3.5 transition-transform ${collapsed ? "rotate-180" : ""}`} />
            {!collapsed && "Collapse"}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="glass sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-base-border px-6">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-slate-400">ULPF</span>
            <span className="text-slate-400">/</span>
            <span className="font-medium text-slate-800">{current.label}</span>
          </div>

          <div className="flex items-center gap-4">
            {(activeAlerts.data?.total ?? 0) > 0 && (
              <NavLink to="/alerts" className="hidden items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 sm:flex">
                <Siren className="h-3.5 w-3.5 text-sev-high" />
                <span className="font-semibold text-slate-800">{activeAlerts.data!.total}</span> active
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
                <div className="max-w-[160px] truncate text-xs font-medium text-slate-800">
                  {user?.full_name || user?.email}
                </div>
                <div className="text-2xs uppercase tracking-wide text-slate-400">{user?.role}</div>
              </div>
              <div className="grid h-8 w-8 place-items-center rounded-full border border-base-border bg-base-panel-2 text-2xs font-semibold text-slate-600">
                {(user?.email ?? "?").slice(0, 2).toUpperCase()}
              </div>
              <button
                onClick={logout}
                aria-label="Sign out"
                className="rounded-lg border border-base-border bg-white p-1.5 text-slate-500 hover:text-slate-800"
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
