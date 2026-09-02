import type { Severity } from "@/types";

export const SEVERITY_ORDER: Severity[] = ["info", "low", "medium", "high", "critical"];

const CLASS: Record<Severity, string> = {
  info: "bg-slate-500/20 text-slate-300",
  low: "bg-sky-500/20 text-sky-300",
  medium: "bg-amber-500/20 text-amber-300",
  high: "bg-orange-500/20 text-orange-300",
  critical: "bg-red-500/20 text-red-300",
};

export function severityClass(sev: string | null | undefined): string {
  return CLASS[(sev ?? "info") as Severity] ?? CLASS.info;
}

export function riskBand(score: number): Severity {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 40) return "medium";
  if (score >= 15) return "low";
  return "info";
}
