/**
 * Single source of truth for semantic status styling across ULPF.
 * Every badge / pill / indicator in the app should route through here so a
 * "HIGH" alert looks identical on every page.
 */
export type StatusKey =
  | "safe" | "info" | "low" | "medium" | "high" | "critical"
  | "suspicious" | "weaponized" | "blocked" | "simulation"
  | "processing" | "running" | "pending" | "completed" | "failed"
  | "resolved" | "new" | "acknowledged" | "investigating" | "false_positive"
  | "online" | "idle" | "error" | "ok" | "neutral";

interface StatusStyle {
  /** short label shown on the pill */
  label: string;
  /** dot colour (hex) */
  dot: string;
  /** tailwind classes for a filled badge */
  badge: string;
  /** tailwind text colour */
  text: string;
}

const S = (label: string, dot: string, badge: string, text: string): StatusStyle => ({
  label, dot, badge, text,
});

const MAP: Record<string, StatusStyle> = {
  safe: S("Safe", "#34d399", "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25", "text-emerald-300"),
  ok: S("OK", "#34d399", "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25", "text-emerald-300"),
  online: S("Online", "#34d399", "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25", "text-emerald-300"),
  completed: S("Completed", "#34d399", "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25", "text-emerald-300"),
  resolved: S("Resolved", "#34d399", "bg-emerald-500/12 text-emerald-300 ring-1 ring-emerald-500/25", "text-emerald-300"),

  info: S("Info", "#64748b", "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/25", "text-slate-300"),
  neutral: S("—", "#64748b", "bg-white/8 text-gray-300 ring-1 ring-white/10", "text-gray-300"),
  idle: S("Idle", "#64748b", "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/25", "text-slate-300"),
  pending: S("Pending", "#64748b", "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/25", "text-slate-300"),
  false_positive: S("False positive", "#64748b", "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/25", "text-slate-300"),

  low: S("Low", "#38bdf8", "bg-sky-500/12 text-sky-300 ring-1 ring-sky-500/25", "text-sky-300"),

  medium: S("Medium", "#fbbf24", "bg-amber-500/12 text-amber-300 ring-1 ring-amber-500/25", "text-amber-300"),
  suspicious: S("Suspicious", "#fbbf24", "bg-amber-500/12 text-amber-300 ring-1 ring-amber-500/25", "text-amber-300"),
  simulation: S("Simulation only", "#fbbf24", "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/35", "text-amber-300"),
  acknowledged: S("Acknowledged", "#fbbf24", "bg-amber-500/12 text-amber-300 ring-1 ring-amber-500/25", "text-amber-300"),

  high: S("High", "#fb923c", "bg-orange-500/12 text-orange-300 ring-1 ring-orange-500/25", "text-orange-300"),
  investigating: S("Investigating", "#fb923c", "bg-orange-500/12 text-orange-300 ring-1 ring-orange-500/25", "text-orange-300"),

  critical: S("Critical", "#f87171", "bg-red-500/12 text-red-300 ring-1 ring-red-500/30", "text-red-300"),
  weaponized: S("Weaponized", "#f87171", "bg-red-500/12 text-red-300 ring-1 ring-red-500/30", "text-red-300"),
  blocked: S("Blocked", "#f87171", "bg-red-500/12 text-red-300 ring-1 ring-red-500/30", "text-red-300"),
  failed: S("Failed", "#f87171", "bg-red-500/12 text-red-300 ring-1 ring-red-500/30", "text-red-300"),
  error: S("Error", "#f87171", "bg-red-500/12 text-red-300 ring-1 ring-red-500/30", "text-red-300"),

  processing: S("Processing", "#7ca9f9", "bg-blue-500/12 text-blue-300 ring-1 ring-blue-500/25", "text-blue-300"),
  running: S("Running", "#7ca9f9", "bg-blue-500/12 text-blue-300 ring-1 ring-blue-500/25", "text-blue-300"),
  new: S("New", "#7ca9f9", "bg-blue-500/12 text-blue-300 ring-1 ring-blue-500/25", "text-blue-300"),
};

/** Normalise arbitrary backend strings to a StatusKey. */
export function statusKey(raw: string | null | undefined): StatusKey {
  const k = String(raw ?? "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (k in MAP) return k as StatusKey;
  // common synonyms
  if (["accept", "allow", "allowed", "success", "success_rate"].includes(k)) return "safe";
  if (["deny", "denied", "drop", "dropped", "quarantined"].includes(k)) return "blocked";
  if (["invalid", "duplicate"].includes(k)) return "medium";
  if (["weaponized_log"].includes(k)) return "weaponized";
  if (["processed"].includes(k)) return "completed";
  if (["configured", "receiving"].includes(k)) return "online";
  return "neutral";
}

export function statusStyle(raw: string | null | undefined): StatusStyle {
  return MAP[statusKey(raw)] ?? MAP.neutral;
}

/** Colour for a numeric risk score 0-100. */
export function riskKey(score: number): StatusKey {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 40) return "medium";
  if (score >= 15) return "low";
  return "info";
}
