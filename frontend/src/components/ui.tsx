import type { ReactNode } from "react";
import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import clsx from "clsx";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("card", className)}>{children}</div>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label ?? "Loading…"}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-base-border py-12 text-center">
      <Inbox className="mb-2 h-6 w-6 text-gray-500" />
      <p className="text-sm text-gray-300">{title}</p>
      {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const msg =
    (error as { message?: string })?.message ?? (typeof error === "string" ? error : "Request failed");
  return (
    <div className="flex items-center gap-2 rounded-lg border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-red-200">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {msg}
    </div>
  );
}

const BADGE_TONES: Record<string, string> = {
  neutral: "bg-white/10 text-gray-200",
  green: "bg-emerald-500/15 text-emerald-300",
  amber: "bg-amber-500/15 text-amber-300",
  red: "bg-red-500/15 text-red-300",
  blue: "bg-blue-500/15 text-blue-300",
  slate: "bg-slate-500/20 text-slate-300",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: keyof typeof BADGE_TONES;
}) {
  return <span className={clsx("badge", BADGE_TONES[tone])}>{children}</span>;
}

export function verdictTone(v: string): keyof typeof BADGE_TONES {
  if (v === "WEAPONIZED_LOG") return "red";
  if (v === "SUSPICIOUS") return "amber";
  if (v === "SAFE") return "green";
  return "neutral";
}

export function statusTone(s: string): keyof typeof BADGE_TONES {
  switch (s) {
    case "COMPLETED":
    case "PROCESSED":
      return "green";
    case "RUNNING":
    case "PENDING":
      return "blue";
    case "FAILED":
    case "INVALID":
      return "red";
    case "QUARANTINED":
    case "DUPLICATE":
      return "amber";
    default:
      return "neutral";
  }
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
      <div className="h-full bg-brand transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
