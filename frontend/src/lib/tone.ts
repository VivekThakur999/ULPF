/**
 * Category / identity accent colors — distinct from `status.ts` (which encodes
 * health/severity). This palette answers "what kind of thing is this" (data,
 * interaction, AI, structure) rather than "is this healthy". Used for KPI
 * accent bars and pipeline-stage identity so the Command Center reads as
 * many deliberately-colored surfaces, not one repeated status color.
 *
 * Every string here is a complete, static Tailwind class — never build these
 * by concatenating a variable into a class name, or the JIT compiler won't
 * find them.
 */
export type AccentTone =
  | "sky" | "blue" | "cyan" | "purple" | "violet"
  | "emerald" | "amber" | "red" | "slate";

interface ToneStyle {
  /** top accent bar background */
  bar: string;
  /** small filled chip: bg + text */
  chip: string;
  /** icon text color */
  icon: string;
  /** hex, for inline SVG / chart use */
  dot: string;
}

export const TONE: Record<AccentTone, ToneStyle> = {
  sky: { bar: "bg-sky-500", chip: "bg-sky-100 text-sky-800", icon: "text-sky-600", dot: "#0284c7" },
  blue: { bar: "bg-blue-600", chip: "bg-blue-100 text-blue-800", icon: "text-blue-600", dot: "#2563eb" },
  cyan: { bar: "bg-cyan-500", chip: "bg-cyan-100 text-cyan-800", icon: "text-cyan-600", dot: "#0891b2" },
  purple: { bar: "bg-purple-500", chip: "bg-purple-100 text-purple-800", icon: "text-purple-600", dot: "#7c3aed" },
  violet: { bar: "bg-indigo-500", chip: "bg-indigo-100 text-indigo-800", icon: "text-indigo-600", dot: "#4f46e5" },
  emerald: { bar: "bg-emerald-500", chip: "bg-emerald-100 text-emerald-800", icon: "text-emerald-600", dot: "#059669" },
  amber: { bar: "bg-amber-500", chip: "bg-amber-100 text-amber-900", icon: "text-amber-600", dot: "#d97706" },
  red: { bar: "bg-red-500", chip: "bg-red-100 text-red-800", icon: "text-red-600", dot: "#dc2626" },
  slate: { bar: "bg-slate-200", chip: "bg-slate-100 text-slate-500", icon: "text-slate-400", dot: "#94a3b8" },
};
