/**
 * Renders a mined template with its literal text as-is and each variable
 * position shown as a highlighted, typed chip (`<ip>`, `<value>`, …).
 */
export default function TemplatePattern({
  literals,
  separators,
  trailing,
  types,
  values,
}: {
  literals: (string | null)[];
  separators: string[];
  trailing: string;
  types: (string | null)[];
  /** optional: concrete variable values (in order) to show instead of the type */
  values?: string[];
}) {
  let vi = 0;
  return (
    <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded border border-base-border bg-base-bg p-3 font-mono text-xs leading-relaxed">
      {literals.map((lit, i) => {
        const sep = separators[i] ?? " ";
        if (lit !== null) {
          return (
            <span key={i}>
              {sep}
              {lit}
            </span>
          );
        }
        const t = types[i] ?? "value";
        const val = values ? values[vi++] : null;
        return (
          <span key={i}>
            {sep}
            <span className="rounded bg-amber-100 px-1 text-amber-900" title={`variable · ${t}`}>
              {val !== null ? val : `<${t}>`}
            </span>
          </span>
        );
      })}
      {trailing}
    </pre>
  );
}
