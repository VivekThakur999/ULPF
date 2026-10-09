import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, UserCheck, Eye, Lock, ShieldAlert, KeyRound, CheckCircle2, ChevronRight, Info } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { apiError } from "@/services/api";

interface DemoRole {
  role: "ADMIN" | "ANALYST" | "VIEWER";
  name: string;
  email: string;
  tagline: string;
  badgeClass: string;
  borderClass: string;
  bgClass: string;
  icon: typeof ShieldCheck;
  permissions: string[];
}

const DEMO_ROLES: DemoRole[] = [
  {
    role: "ADMIN",
    name: "Administrator",
    email: "admin@ulpf.io",
    tagline: "Full system administration, pipeline mutation, and policy control",
    badgeClass: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    borderClass: "border-red-500/40 shadow-red-500/5",
    bgClass: "hover:border-red-500/30",
    icon: ShieldAlert,
    permissions: ["Pipeline configuration", "Security rule mutations", "User management", "Full export"],
  },
  {
    role: "ANALYST",
    name: "SOC Analyst",
    email: "analyst@ulpf.io",
    tagline: "Log search, alert investigation, attack simulation, and AI assistant",
    badgeClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    borderClass: "border-blue-500/40 shadow-blue-500/5",
    bgClass: "hover:border-blue-500/30",
    icon: UserCheck,
    permissions: ["Log Explorer & Facets", "Alert correlation triage", "Threat simulator", "AI log assistant"],
  },
  {
    role: "VIEWER",
    name: "Auditor / Viewer",
    email: "viewer@ulpf.io",
    tagline: "Read-only access to operational dashboards, metrics, and audit logs",
    badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    borderClass: "border-emerald-500/40 shadow-emerald-500/5",
    icon: Eye,
    bgClass: "hover:border-emerald-500/30",
    permissions: ["Command Center KPI view", "Log stream observation", "Health check stats", "Audit log viewing"],
  },
];

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };

  const [selectedRole, setSelectedRole] = useState<"ADMIN" | "ANALYST" | "VIEWER">("ADMIN");
  const [email, setEmail] = useState("admin@ulpf.io");
  const [password, setPassword] = useState("ChangeMe!123");
  const [showPassword, setShowPassword] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [showRbacDetails, setShowRbacDetails] = useState(false);

  function handleSelectRole(roleItem: DemoRole) {
    setSelectedRole(roleItem.role);
    setEmail(roleItem.email);
    setPassword("ChangeMe!123");
    setErr("");
  }

  async function performLogin(targetEmail: string, targetPass: string) {
    setErr("");
    setBusy(true);
    try {
      await login(targetEmail, targetPass);
      nav(loc.state?.from ?? "/", { replace: true });
    } catch (e) {
      setErr(apiError(e));
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await performLogin(email, password);
  }

  const activeRoleData = DEMO_ROLES.find((r) => r.role === selectedRole) || DEMO_ROLES[0];

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-slate-950 dark:to-slate-900">
      <div className="w-full max-w-lg space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-brand-fg/10 text-brand-fg mb-1 shadow-inner">
            <ShieldCheck className="h-9 w-9 text-brand-fg" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
            Universal Log Pre-processing Framework
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            SIH 2026 • Dual-Storage Telemetry & Security Intelligence Control Plane
          </p>
        </div>

        {/* Card Container */}
        <div className="card shadow-xl border border-gray-200/80 dark:border-gray-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md p-6 space-y-6 rounded-2xl">
          {/* Persona Role Switcher */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Select Login Role / Persona
              </label>
              <button
                type="button"
                onClick={() => setShowRbacDetails(!showRbacDetails)}
                className="text-xs text-brand-fg hover:underline inline-flex items-center gap-1"
              >
                <Info className="h-3 w-3" />
                {showRbacDetails ? "Hide RBAC Scope" : "View RBAC Scope"}
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              {DEMO_ROLES.map((r) => {
                const Icon = r.icon;
                const isSelected = selectedRole === r.role;
                return (
                  <button
                    key={r.role}
                    type="button"
                    onClick={() => handleSelectRole(r)}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all duration-200 ${
                      isSelected
                        ? `bg-gray-50 dark:bg-slate-800/90 ${r.borderClass} ring-2 ring-brand-fg/30 scale-[1.02]`
                        : `border-gray-200 dark:border-gray-800 bg-transparent ${r.bgClass} opacity-75 hover:opacity-100`
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Icon className="h-4 w-4" />
                      <span className="text-xs font-bold tracking-wide">{r.name.split(" ")[0]}</span>
                    </div>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${r.badgeClass}`}>
                      {r.role}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Selected Role Summary & Permissions */}
            <div className="rounded-lg bg-gray-50 dark:bg-slate-800/60 border border-gray-200/60 dark:border-gray-700/60 p-3 text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-800 dark:text-gray-200">
                  {activeRoleData.name} Scope:
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${activeRoleData.badgeClass}`}>
                  {activeRoleData.role}
                </span>
              </div>
              <p className="text-gray-600 dark:text-gray-400 text-[11px]">
                {activeRoleData.tagline}
              </p>

              {showRbacDetails && (
                <div className="pt-2 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 gap-1 text-[10px] text-gray-500 dark:text-gray-400">
                  {activeRoleData.permissions.map((perm) => (
                    <div key={perm} className="flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3 text-brand-fg flex-shrink-0" />
                      <span>{perm}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Email Address</label>
              <input
                className="input w-full"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                placeholder="user@ulpf.io"
                required
              />
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Password</label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <div className="relative">
                <input
                  className="input w-full pr-10 font-mono text-sm"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="Enter password"
                  required
                />
                <Lock className="absolute right-3 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </div>

            {err && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-sev-critical flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 flex-shrink-0" />
                <span>{err}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full justify-center py-2.5 font-semibold text-sm shadow-md"
              disabled={busy}
            >
              {busy ? (
                "Authenticating…"
              ) : (
                <span className="inline-flex items-center gap-2">
                  <span>Sign in as {activeRoleData.role}</span>
                  <ChevronRight className="h-4 w-4" />
                </span>
              )}
            </button>
          </form>

          {/* Quick 1-Click Action */}
          <div className="pt-2 border-t border-gray-100 dark:border-gray-800 text-center space-y-2">
            <button
              type="button"
              onClick={() => performLogin(activeRoleData.email, "ChangeMe!123")}
              disabled={busy}
              className="w-full py-2 px-3 rounded-lg text-xs font-medium bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-700 transition flex items-center justify-center gap-1.5"
            >
              <KeyRound className="h-3.5 w-3.5 text-brand-fg" />
              <span>1-Click Demo Login as <strong>{activeRoleData.name}</strong></span>
            </button>
            <p className="text-[11px] text-gray-400 dark:text-gray-500">
              Default password is <code className="px-1 py-0.5 rounded bg-gray-100 dark:bg-slate-800 font-mono text-[10px]">ChangeMe!123</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
