import { type ReactNode, useState } from "react";
import { AlertTriangle, Inbox, Loader2, RotateCw, X } from "lucide-react";
import clsx from "clsx";
import { statusKey, statusStyle, type StatusKey } from "@/lib/status";

/* ------------------------------------------------------------------ headers */

export function PageHeader({
  title,
  subtitle,
  eyebrow,
  actions,
}: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-1 text-2xs font-semibold uppercase tracking-[0.18em] text-brand-fg/80">
            {eyebrow}
          </div>
        )}
        <h1 className="text-xl font-semibold tracking-tight text-gray-50">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-gray-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SectionHeader({
  title,
  hint,
  right,
}: {
  title: string;
  hint?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <div>
        <h2 className="text-sm font-semibold text-gray-200">{title}</h2>
        {hint && <p className="text-xs text-gray-500">{hint}</p>}
      </div>
      {right}
    </div>
  );
}

/* ------------------------------------------------------------------ surfaces */

export function Card({
  children,
  className,
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return <div className={clsx("surface bg-surface-sheen", padded && "p-4", className)}>{children}</div>;
}

/* ------------------------------------------------------------------ states */

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-gray-400">
      <Loader2 className="h-4 w-4 animate-spin text-brand-fg" />
      {label ?? "Loading…"}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={clsx("relative overflow-hidden rounded-md bg-white/[0.04]", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
    </div>
  );
}

export function SkeletonTable({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="surface overflow-hidden">
      <div className="border-b border-base-border p-3">
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="divide-y divide-base-border/60">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 p-3">
            {Array.from({ length: cols }).map((__, c) => (
              <Skeleton key={c} className="h-3.5 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  icon: Icon = Inbox,
  action,
}: {
  title: string;
  hint?: string;
  icon?: typeof Inbox;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-base-border bg-base-panel/40 px-6 py-14 text-center">
      <div className="mb-3 rounded-lg border border-base-border bg-base-panel-2 p-2.5">
        <Icon className="h-5 w-5 text-gray-500" />
      </div>
      <p className="text-sm font-medium text-gray-300">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-xs text-gray-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg =
    (error as { message?: string })?.message ?? (typeof error === "string" ? error : "Request failed");
  return (
    <div className="flex items-start gap-3 rounded-xl border border-sev-critical/30 bg-sev-critical/[0.07] p-4 text-sm text-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-sev-critical" />
      <div className="flex-1">
        <p className="font-medium">Something went wrong</p>
        <p className="mt-0.5 text-xs text-red-200/80">{msg}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-red-400/30 bg-red-500/10 px-2.5 py-1.5 text-xs font-medium hover:bg-red-500/20"
        >
          <RotateCw className="h-3 w-3" /> Retry
        </button>
      )}
    </div>
  );
}

export function BackendUnavailable({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <div className="rounded-xl border border-sev-critical/30 bg-sev-critical/[0.07] p-4">
        <AlertTriangle className="h-7 w-7 text-sev-critical" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-gray-100">Backend unavailable</h2>
        <p className="mt-1 max-w-sm text-sm text-gray-400">
          ULPF can't reach the API. Check that the backend is running, then retry.
        </p>
      </div>
      <button className="btn-primary" onClick={onRetry}>
        <RotateCw className="h-4 w-4" /> Retry connection
      </button>
    </div>
  );
}

/**
 * Standardises loading / error / empty / content states for any API-driven view.
 */
export function QueryState<T>({
  query,
  loadingLabel,
  emptyTitle,
  emptyHint,
  isEmpty,
  skeleton,
  children,
}: {
  query: {
    isLoading: boolean;
    isError: boolean;
    error: unknown;
    data: T | undefined;
    refetch: () => void;
  };
  loadingLabel?: string;
  emptyTitle?: string;
  emptyHint?: string;
  isEmpty?: (data: T) => boolean;
  skeleton?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) return <>{skeleton ?? <Spinner label={loadingLabel} />}</>;
  if (query.isError) return <ErrorState error={query.error} onRetry={query.refetch} />;
  const data = query.data as T;
  if (isEmpty?.(data)) {
    return <EmptyState title={emptyTitle ?? "Nothing here yet"} hint={emptyHint} />;
  }
  return <>{children(data)}</>;
}

/* ------------------------------------------------------------------ status */

export function LiveDot({ label = "Live" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-2xs font-medium text-gray-500">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </span>
      {label}
    </span>
  );
}

export function StatusPill({
  status,
  label,
  dot = true,
  className,
}: {
  status: string | null | undefined;
  label?: string;
  dot?: boolean;
  className?: string;
}) {
  const s = statusStyle(status);
  return (
    <span className={clsx("badge", s.badge, className)}>
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: s.dot }}
          aria-hidden
        />
      )}
      {label ?? s.label}
    </span>
  );
}

/** Backward-compatible tone badge (kept so older pages keep working). */
const BADGE_TONES: Record<string, string> = {
  neutral: "bg-white/8 text-gray-300 ring-1 ring-white/10",
  green: "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25",
  amber: "bg-amber-500/12 text-amber-300 ring-1 ring-amber-500/25",
  red: "bg-red-500/12 text-red-300 ring-1 ring-red-500/30",
  blue: "bg-blue-500/12 text-blue-300 ring-1 ring-blue-500/25",
  slate: "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/25",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: keyof typeof BADGE_TONES;
  className?: string;
}) {
  return <span className={clsx("badge", BADGE_TONES[tone], className)}>{children}</span>;
}

export function verdictTone(v: string): keyof typeof BADGE_TONES {
  if (v === "WEAPONIZED_LOG") return "red";
  if (v === "SUSPICIOUS") return "amber";
  if (v === "SAFE") return "green";
  return "neutral";
}

export function statusTone(s: string): keyof typeof BADGE_TONES {
  const k = statusKey(s);
  if (["safe", "ok", "online", "completed", "resolved"].includes(k)) return "green";
  if (["processing", "running", "new"].includes(k)) return "blue";
  if (["failed", "error", "critical", "weaponized", "blocked"].includes(k)) return "red";
  if (["medium", "suspicious", "simulation", "acknowledged", "high", "investigating"].includes(k))
    return "amber";
  return "neutral";
}

/* ------------------------------------------------------------------ metrics */

export function Kpi({
  label,
  value,
  sub,
  status,
  icon: Icon,
  loading,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  status?: StatusKey | string;
  icon?: typeof Inbox;
  loading?: boolean;
}) {
  const dot = status ? statusStyle(status).dot : "#3b4658";
  return (
    <div className="surface bg-surface-sheen p-4 transition-colors hover:border-base-border-strong">
      <div className="flex items-center justify-between">
        <span className="text-2xs font-semibold uppercase tracking-wider text-gray-500">{label}</span>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: dot }} aria-hidden />
          {Icon && <Icon className="h-3.5 w-3.5 text-gray-600" />}
        </span>
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-20" />
      ) : (
        <div className="mt-1.5 text-2xl font-semibold tracking-tight text-gray-50 tnum">{value}</div>
      )}
      {sub && <div className="mt-0.5 text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

export function KpiGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">{children}</div>;
}

/* ------------------------------------------------------------------ drawer */

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  actions,
  width = "max-w-2xl",
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  width?: string;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-[2px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={clsx(
          "flex h-full w-full flex-col border-l border-base-border bg-base-panel shadow-2xl animate-slide-in-right",
          width,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-base-border px-5 py-3.5">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-gray-100">{title}</div>
            {subtitle && <div className="truncate text-xs text-gray-500">{subtitle}</div>}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {actions}
            <button
              onClick={onClose}
              aria-label="Close panel"
              className="rounded-lg border border-base-border bg-base-panel-2 p-1.5 text-gray-400 hover:text-gray-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ tabs */

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { key: T; label: ReactNode }[];
  value: T;
  onChange: (t: T) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-base-border">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={clsx(
            "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
            value === t.key
              ? "border-brand text-brand-fg"
              : "border-transparent text-gray-400 hover:text-gray-200",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ table */

export function DataTable({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("surface overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="tbl">{children}</table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ filters */

export function FilterChips({
  filters,
  onRemove,
  onClear,
}: {
  filters: Record<string, unknown>;
  onRemove: (key: string) => void;
  onClear: () => void;
}) {
  const entries = Object.entries(filters).filter(([, v]) => v !== undefined && v !== "" && v !== null);
  if (entries.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-2xs font-semibold uppercase tracking-wider text-gray-600">Filters</span>
      {entries.map(([k, v]) => (
        <button
          key={k}
          onClick={() => onRemove(k)}
          className="group inline-flex items-center gap-1 rounded-md border border-brand/25 bg-brand/10 px-1.5 py-0.5 text-2xs text-brand-fg hover:bg-brand/20"
        >
          <span className="text-gray-400">{k.replace(/_/g, " ")}:</span>
          <span className="font-medium">{String(v)}</span>
          <X className="h-3 w-3 opacity-50 group-hover:opacity-100" />
        </button>
      ))}
      <button onClick={onClear} className="text-2xs text-gray-500 hover:text-gray-300 underline">
        clear all
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ risk */

export function RiskMeter({
  score,
  band,
  factors,
  compact,
}: {
  score: number;
  band: string;
  factors?: { factor: string; points: number; detail?: string }[];
  compact?: boolean;
}) {
  const s = statusStyle(band);
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div>
      <div className="flex items-end gap-3">
        <div className="text-4xl font-bold tracking-tight tnum" style={{ color: s.dot }}>
          {Math.round(score)}
        </div>
        <div className="pb-1">
          <StatusPill status={band} label={`${band.toUpperCase()} RISK`} />
        </div>
      </div>
      <div className="mt-2">
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${pct}%`,
              background: `linear-gradient(90deg, #38bdf8, #fbbf24, #fb923c, #f87171)`,
              clipPath: `inset(0 ${100 - pct}% 0 0)`,
            }}
          />
        </div>
        <div className="mt-1 flex justify-between text-2xs text-gray-600">
          <span>0</span>
          <span>100</span>
        </div>
      </div>
      {!compact && factors && factors.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {factors.map((f) => (
            <li key={f.factor} className="flex items-center gap-2 text-xs">
              <span className="w-9 shrink-0 text-right font-mono font-semibold text-brand-fg">
                +{f.points}
              </span>
              <div className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-white/[0.06]">
                <div className="h-full bg-brand/70" style={{ width: `${Math.min(100, f.points * 3)}%` }} />
              </div>
              <span className="text-gray-300">{f.factor.replace(/_/g, " ")}</span>
              {f.detail && <span className="truncate text-gray-500">— {f.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ tooltip */

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const [show, setShow] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      {children}
      {show && (
        <span className="pointer-events-none absolute left-1/2 top-full z-50 mt-1.5 -translate-x-1/2 whitespace-nowrap rounded-md border border-base-border-strong bg-base-elevated px-2 py-1 text-2xs text-gray-200 shadow-panel">
          {label}
        </span>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ misc */

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
      <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso).getTime();
  const diff = Date.now() - d;
  const abs = Math.abs(diff);
  const m = 60_000, h = 3_600_000, day = 86_400_000;
  if (abs < m) return "just now";
  if (abs < h) return `${Math.round(diff / m)}m ago`;
  if (abs < day) return `${Math.round(diff / h)}h ago`;
  if (abs < 30 * day) return `${Math.round(diff / day)}d ago`;
  return new Date(iso).toLocaleDateString();
}
