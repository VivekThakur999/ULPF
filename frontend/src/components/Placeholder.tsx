import type { ReactNode } from "react";

/**
 * Honest placeholder for pages implemented in a later phase.
 * We never render fake data or fake controls - this states plainly that the
 * feature is under construction.
 */
export default function Placeholder({
  title,
  phase,
  children,
}: {
  title: string;
  phase: string;
  children?: ReactNode;
}) {
  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">{title}</h1>
      <p className="mb-6 text-sm text-gray-400">
        Planned for <span className="text-brand-fg">{phase}</span>. This screen is a
        navigation stub until that phase lands - no placeholder data is shown.
      </p>
      {children}
    </div>
  );
}
