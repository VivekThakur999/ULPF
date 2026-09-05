import type { Severity } from "@/types";
import { riskKey, statusStyle } from "@/lib/status";

export const SEVERITY_ORDER: Severity[] = ["info", "low", "medium", "high", "critical"];

/** Tailwind classes for a severity badge (routes through the central status map). */
export function severityClass(sev: string | null | undefined): string {
  return statusStyle(sev ?? "info").badge;
}

export function riskBand(score: number): Severity {
  return riskKey(score) as Severity;
}
