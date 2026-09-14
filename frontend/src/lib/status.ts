/**
 * Single source of truth for semantic status styling across ULPF.
 * Every badge / pill / indicator in the app should route through here so a
 * "HIGH" alert looks identical on every page.
 *
 * Light enterprise surfaces: badges use the Material "container" pattern —
 * a soft tint background with a much darker foreground for AA contrast on
 * white/off-white cards (bg-emerald-100 text-emerald-800), never a light
 * color on a light background.
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
  safe: S("Safe", "#059669", "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", "text-emerald-700"),
  ok: S("OK", "#059669", "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", "text-emerald-700"),
  online: S("Online", "#059669", "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", "text-emerald-700"),
  completed: S("Completed", "#059669", "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", "text-emerald-700"),
  resolved: S("Resolved", "#059669", "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", "text-emerald-700"),

  info: S("Info", "#64748b", "bg-slate-100 text-slate-700 ring-1 ring-slate-200", "text-slate-600"),
  neutral: S("—", "#64748b", "bg-slate-100 text-slate-600 ring-1 ring-slate-200", "text-slate-600"),
  idle: S("Idle", "#64748b", "bg-slate-100 text-slate-700 ring-1 ring-slate-200", "text-slate-600"),
  pending: S("Pending", "#64748b", "bg-slate-100 text-slate-700 ring-1 ring-slate-200", "text-slate-600"),
  false_positive: S("False positive", "#64748b", "bg-slate-100 text-slate-700 ring-1 ring-slate-200", "text-slate-600"),

  low: S("Low", "#0284c7", "bg-sky-50 text-sky-800 ring-1 ring-sky-200", "text-sky-700"),

  medium: S("Medium", "#d97706", "bg-amber-50 text-amber-900 ring-1 ring-amber-200", "text-amber-800"),
  suspicious: S("Suspicious", "#d97706", "bg-amber-50 text-amber-900 ring-1 ring-amber-200", "text-amber-800"),
  simulation: S("Simulation only", "#d97706", "bg-amber-50 text-amber-900 ring-1 ring-amber-300", "text-amber-800"),
  acknowledged: S("Acknowledged", "#d97706", "bg-amber-50 text-amber-900 ring-1 ring-amber-200", "text-amber-800"),

  high: S("High", "#ea580c", "bg-orange-50 text-orange-800 ring-1 ring-orange-200", "text-orange-700"),
  investigating: S("Investigating", "#ea580c", "bg-orange-50 text-orange-800 ring-1 ring-orange-200", "text-orange-700"),

  // Severity red — a soft wash badge, deliberately never a solid fill so it
  // stays visually distinct from the solid crimson brand/interactive color.
  critical: S("Critical", "#dc2626", "bg-red-50 text-red-800 ring-1 ring-red-200", "text-red-700"),
  weaponized: S("Weaponized", "#dc2626", "bg-red-50 text-red-800 ring-1 ring-red-200", "text-red-700"),
  blocked: S("Blocked", "#dc2626", "bg-red-50 text-red-800 ring-1 ring-red-200", "text-red-700"),
  failed: S("Failed", "#dc2626", "bg-red-50 text-red-800 ring-1 ring-red-200", "text-red-700"),
  error: S("Error", "#dc2626", "bg-red-50 text-red-800 ring-1 ring-red-200", "text-red-700"),

  processing: S("Processing", "#2563eb", "bg-blue-50 text-blue-800 ring-1 ring-blue-200", "text-blue-700"),
  running: S("Running", "#2563eb", "bg-blue-50 text-blue-800 ring-1 ring-blue-200", "text-blue-700"),
  new: S("New", "#2563eb", "bg-blue-50 text-blue-800 ring-1 ring-blue-200", "text-blue-700"),
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
