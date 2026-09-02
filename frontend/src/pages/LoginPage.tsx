import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { apiError } from "@/services/api";

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState("admin@ulpf.io");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(email, password);
      nav(loc.state?.from ?? "/", { replace: true });
    } catch (e) {
      setErr(apiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-brand-fg" />
          <div>
            <h1 className="text-lg font-semibold">ULPF</h1>
            <p className="text-xs text-gray-400">Universal Log Pre-processing Framework</p>
          </div>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)}
              autoComplete="username" required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </div>
          {err && <p className="text-sm text-sev-critical">{err}</p>}
          <button className="btn-primary w-full justify-center" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-center text-xs text-gray-500">
            Default demo admin seeded from environment. Change the password after first login.
          </p>
        </form>
      </div>
    </div>
  );
}
