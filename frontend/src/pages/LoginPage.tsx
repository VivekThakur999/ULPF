import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  UserCheck,
  Eye,
  Lock,
  ShieldAlert,
  KeyRound,
  CheckCircle2,
  ChevronRight,
  Info,
  Sparkles,
  Layers,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { apiError } from "@/services/api";

interface DemoRole {
  role: "ADMIN" | "ANALYST" | "VIEWER";
  name: string;
  email: string;
  tagline: string;
  badgeText: string;
  icon: typeof ShieldCheck;
  permissions: string[];
}

const DEMO_ROLES: DemoRole[] = [
  {
    role: "ADMIN",
    name: "Administrator",
    email: "admin@ulpf.io",
    tagline: "Full system administration, pipeline mutation, and policy control",
    badgeText: "FULL ACCESS",
    icon: ShieldAlert,
    permissions: [
      "Pipeline configuration & WASM loaders",
      "Security correlation rule mutations",
      "User provisioning & RBAC governance",
      "Full forensic data export & backups",
    ],
  },
  {
    role: "ANALYST",
    name: "SOC Analyst",
    email: "analyst@ulpf.io",
    tagline: "Log search, alert triage, incident simulation, and AI log assistant",
    badgeText: "TRIAGE & AI",
    icon: UserCheck,
    permissions: [
      "Log Explorer & multi-facet queries",
      "Security alert correlation & risk scoring",
      "Threat response simulation sandbox",
      "AI offline log explanation assistant",
    ],
  },
  {
    role: "VIEWER",
    name: "Auditor / Viewer",
    email: "viewer@ulpf.io",
    tagline: "Read-only observation of Command Center KPIs, streams, and audits",
    badgeText: "READ ONLY",
    icon: Eye,
    permissions: [
      "Command Center executive metrics",
      "Live telemetry log stream monitoring",
      "System health & node telemetry",
      "Compliance audit log examination",
    ],
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
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 bg-gradient-to-br from-red-50 via-white to-red-100/70 text-slate-900 relative overflow-hidden font-sans">
      {/* Background Decorative Rings */}
      <div className="absolute top-[-10%] left-[-10%] w-[45vw] h-[45vw] rounded-full bg-red-200/40 blur-3xl pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[45vw] h-[45vw] rounded-full bg-red-300/30 blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-3.5 rounded-2xl bg-red-600 text-white shadow-xl shadow-red-600/30 transform hover:scale-105 transition duration-200">
            <ShieldCheck className="h-9 w-9 text-white" />
          </div>
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-red-100 border border-red-200 text-red-700 text-[11px] font-semibold tracking-wide uppercase mb-1">
              <Sparkles className="h-3 w-3 text-red-600" />
              <span>SIH 2026 Security Intelligence</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              ULPF Command Center
            </h1>
            <p className="text-xs text-slate-600 font-medium mt-1">
              Universal Log Pre-processing & Telemetry Plane
            </p>
          </div>
        </div>

        {/* Main Card Container */}
        <div className="bg-white rounded-3xl border border-red-100 shadow-2xl shadow-red-950/10 p-6 sm:p-7 space-y-6">
          {/* Persona Role Selection Header */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 uppercase tracking-wider">
                <Layers className="h-3.5 w-3.5 text-red-600" />
                <span>Select Login Persona</span>
              </div>
              <button
                type="button"
                onClick={() => setShowRbacDetails(!showRbacDetails)}
                className="text-xs font-semibold text-red-600 hover:text-red-700 inline-flex items-center gap-1 transition"
              >
                <Info className="h-3.5 w-3.5" />
                <span>{showRbacDetails ? "Hide Scope" : "View Scope"}</span>
              </button>
            </div>

            {/* Role Persona Tabs */}
            <div className="grid grid-cols-3 gap-2 sm:gap-2.5">
              {DEMO_ROLES.map((r) => {
                const Icon = r.icon;
                const isSelected = selectedRole === r.role;
                return (
                  <button
                    key={r.role}
                    type="button"
                    onClick={() => handleSelectRole(r)}
                    className={`flex flex-col items-center justify-center p-3 rounded-2xl border text-center transition-all duration-200 ${
                      isSelected
                        ? "bg-red-50/80 border-red-600 ring-2 ring-red-600/30 text-red-900 shadow-sm transform scale-[1.02]"
                        : "border-slate-200 bg-slate-50/60 text-slate-600 hover:border-red-300 hover:bg-red-50/30"
                    }`}
                  >
                    <div className={`p-2 rounded-xl mb-1.5 ${isSelected ? "bg-red-600 text-white" : "bg-white text-slate-600 border border-slate-200"}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-xs font-bold tracking-tight">{r.name.split(" ")[0]}</span>
                    <span
                      className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full mt-1 ${
                        isSelected ? "bg-red-600 text-white" : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {r.role}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Active Role Persona Description Box */}
            <div className="rounded-2xl bg-gradient-to-r from-red-50/80 via-white to-red-50/50 border border-red-200/80 p-3.5 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 text-xs">
                  {activeRoleData.name}
                </span>
                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-red-600 text-white uppercase tracking-wider">
                  {activeRoleData.badgeText}
                </span>
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed">
                {activeRoleData.tagline}
              </p>

              {showRbacDetails && (
                <div className="pt-2 mt-2 border-t border-red-200/60 space-y-1.5 animate-fadeIn">
                  <span className="text-[10px] font-bold text-red-800 uppercase tracking-wider block">
                    Granted Permissions:
                  </span>
                  <div className="grid grid-cols-1 gap-1 text-[11px] text-slate-700">
                    {activeRoleData.permissions.map((perm) => (
                      <div key={perm} className="flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />
                        <span>{perm}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Form Fields */}
          <form onSubmit={submit} className="space-y-4 pt-1">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Email Address
              </label>
              <input
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:outline-none focus:border-red-600 focus:ring-2 focus:ring-red-600/20 transition placeholder-slate-400"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                placeholder="email@ulpf.io"
                required
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-xs font-semibold text-red-600 hover:text-red-700 transition"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <div className="relative">
                <input
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl border border-slate-300 bg-white text-slate-900 font-mono text-sm focus:outline-none focus:border-red-600 focus:ring-2 focus:ring-red-600/20 transition placeholder-slate-400"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="Password"
                  required
                />
                <Lock className="absolute right-3.5 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
              </div>
            </div>

            {err && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-semibold flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-red-600 flex-shrink-0" />
                <span>{err}</span>
              </div>
            )}

            {/* Primary Action Button */}
            <button
              type="submit"
              disabled={busy}
              className="w-full py-3 px-4 rounded-xl bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-bold text-sm shadow-lg shadow-red-600/25 transition duration-150 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer"
            >
              {busy ? (
                "Authenticating…"
              ) : (
                <>
                  <span>Sign in as {activeRoleData.name}</span>
                  <ChevronRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick 1-Click Evaluation Login */}
          <div className="pt-3 border-t border-slate-100 text-center space-y-2">
            <button
              type="button"
              onClick={() => performLogin(activeRoleData.email, "ChangeMe!123")}
              disabled={busy}
              className="w-full py-2.5 px-3 rounded-xl text-xs font-bold bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 active:bg-red-200 transition flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-70"
            >
              <KeyRound className="h-3.5 w-3.5 text-red-600" />
              <span>1-Click Login as <strong>{activeRoleData.name}</strong></span>
            </button>
            <p className="text-[11px] text-slate-500 font-medium">
              Demo credentials pre-seeded with password <code className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 font-mono text-[10px] font-semibold">ChangeMe!123</code>
            </p>
          </div>
        </div>

        {/* Footer Badge */}
        <div className="text-center text-xs text-slate-500 font-medium">
          Protected by Argon2id / Supabase Dual-Auth & PII Tokenization
        </div>
      </div>
    </div>
  );
}
