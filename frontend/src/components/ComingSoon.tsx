import type { LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/ui";

/**
 * Honest "not built yet" screen for features on the roadmap. Never shows
 * fabricated data or fake interactivity - just what the feature will do and
 * which checkpoint delivers it.
 */
export default function ComingSoon({
  title,
  icon: Icon,
  checkpoint,
  summary,
  bullets,
}: {
  title: string;
  icon: LucideIcon;
  checkpoint: string;
  summary: string;
  bullets: string[];
}) {
  return (
    <div>
      <PageHeader title={title} subtitle={summary} />
      <div className="flex flex-col items-center rounded-lg border border-dashed border-base-border p-10 text-center">
        <Icon className="mb-3 h-8 w-8 text-gray-600" />
        <p className="text-sm font-medium text-gray-300">Planned for {checkpoint}</p>
        <p className="mt-1 max-w-md text-xs text-gray-500">
          This screen is a navigation stub — no placeholder data or simulated activity is shown
          until that checkpoint lands.
        </p>
        <ul className="mt-4 space-y-1.5 text-left text-xs text-gray-400">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-gray-600" />
              {b}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
