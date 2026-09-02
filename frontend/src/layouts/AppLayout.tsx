import { NavLink, Outlet } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Bug,
  Database,
  FileStack,
  LayoutDashboard,
  LogOut,
  Package,
  Search,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/sources", label: "Log Sources", icon: Database },
  { to: "/ingestion", label: "Ingestion", icon: FileStack },
  { to: "/explorer", label: "Log Explorer", icon: Search },
  { to: "/debugger", label: "Pipeline Debugger", icon: Bug },
  { to: "/alerts", label: "Alerts", icon: AlertTriangle },
  { to: "/parsers", label: "Parser Packs", icon: Package },
  { to: "/privacy", label: "Privacy", icon: ShieldCheck },
  { to: "/compression", label: "Compression", icon: Waypoints },
  { to: "/response", label: "Response Simulator", icon: Activity },
  { to: "/assistant", label: "AI Assistant", icon: Sparkles },
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col border-r border-base-border bg-base-panel">
        <div className="flex items-center gap-2 border-b border-base-border px-4 py-4">
          <ShieldCheck className="h-6 w-6 text-brand-fg" />
          <div>
            <div className="text-sm font-semibold">ULPF</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">
              Log Pre-processing
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm ${
                  isActive ? "bg-brand/15 text-brand-fg" : "text-gray-300 hover:bg-white/5"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
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
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
