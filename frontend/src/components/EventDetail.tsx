import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, FileText, ShieldCheck, Sparkles } from "lucide-react";
import { getLogDetail, type UniversalEvent } from "@/services/endpoints";
import {
  Badge,
  Drawer,
  ErrorState,
  SectionHeader,
  Spinner,
  StatusPill,
  Tabs,
} from "@/components/ui";

const STAGE_LABEL: Record<string, string> = {
  security_shield: "Security Shield",
  format_detection: "Format Detection",
  parsing: "Parsing",
  cleaning: "Cleaning",
  field_extraction: "Field Extraction",
  pii_obfuscation: "PII Obfuscation",
  normalization: "Normalization",
  validation: "Validation",
};

type Tab = "universal" | "raw" | "pipeline" | "related";

export default function EventDetail({ eventId, onClose }: { eventId: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ["log", eventId], queryFn: () => getLogDetail(eventId) });
  const [tab, setTab] = useState<Tab>("universal");
  const ev = q.data?.event;

  return (
    <Drawer
      open
      onClose={onClose}
      width="max-w-2xl"
      title={ev ? `${ev.event_type ?? "event"} · ${ev.source}` : "Event"}
      subtitle={ev?.id}
      actions={
        ev && (
          <Link
            to={`/assistant?event=${ev.id}`}
            className="btn-ghost py-1.5 text-xs"
            onClick={onClose}
          >
            <Sparkles className="h-3.5 w-3.5" /> Explain with AI
          </Link>
        )
      }
    >
      {q.isLoading ? (
        <Spinner label="Loading event…" />
      ) : q.isError || !q.data ? (
        <ErrorState error={q.error ?? "Event not found"} onRetry={q.refetch} />
      ) : (
        <>
          <TransformFlow event={q.data.event} />

          <div className="mb-3">
            <Tabs<Tab>
              tabs={[
                { key: "universal", label: "Universal Event" },
                { key: "raw", label: "Raw Log" },
                { key: "pipeline", label: "Pipeline" },
                { key: "related", label: `Correlation (${q.data.related_events.length})` },
              ]}
              value={tab}
              onChange={setTab}
            />
          </div>

          {tab === "universal" && <UniversalView e={q.data.event} pii={q.data.pii_transformations} />}

          {tab === "raw" && (
            <div className="space-y-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={q.data.raw_log?.security_verdict ?? "SAFE"} />
                {q.data.job && <Badge tone="blue">{q.data.job.detected_format}</Badge>}
                <span className="text-xs text-gray-500">
                  line {q.data.raw_log?.line_number} · {q.data.job?.filename}
                </span>
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-base-border bg-base-bg p-3 font-mono text-xs text-gray-200">
                {q.data.raw_log?.content ?? q.data.event.raw_log}
              </pre>
              {q.data.security_events.length > 0 && (
                <div className="rounded-lg border border-sev-high/40 bg-sev-high/10 p-2 text-xs">
                  {q.data.security_events.map((s) => (
                    <div key={s.id}>
                      <b>{s.detection_type}</b> ({s.severity}) — {s.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "pipeline" && (
            <ol className="space-y-2 text-sm">
              {q.data.pipeline.map((s, i) => (
                <li key={s.stage} className="surface-2 p-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-2xs text-gray-500">{i + 1}</span>
                    <span className="font-medium text-gray-200">{STAGE_LABEL[s.stage] ?? s.stage}</span>
                    <StatusPill
                      status={s.status === "warn" ? "medium" : s.status === "error" ? "failed" : s.status === "skipped" ? "idle" : "ok"}
                      label={s.status}
                      dot={false}
                    />
                    <span className="text-xs text-gray-400">{s.summary}</span>
                  </div>
                  {s.transformations.length > 0 && (
                    <ul className="ml-6 mt-1 list-disc text-xs text-gray-400">
                      {s.transformations.map((t, j) => (
                        <li key={j}>{Object.entries(t).map(([k, v]) => `${k}=${v}`).join(" ")}</li>
                      ))}
                    </ul>
                  )}
                  {s.warnings.map((w, j) => (
                    <p key={j} className="ml-6 text-xs text-sev-medium">⚠ {w}</p>
                  ))}
                  {s.errors.map((w, j) => (
                    <p key={j} className="ml-6 text-xs text-sev-critical">✖ {w}</p>
                  ))}
                </li>
              ))}
            </ol>
          )}

          {tab === "related" && (
            <div className="space-y-1.5 text-sm">
              {q.data.related_events.length === 0 && (
                <p className="text-gray-500">No correlated events.</p>
              )}
              {q.data.related_events.map((e) => (
                <div key={e.id} className="surface-2 flex flex-wrap items-center gap-2 p-2 text-xs">
                  <span className="text-gray-500">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <Badge tone="slate">{e.source}</Badge>
                  <span className="text-gray-300">{e.event_type}</span>
                  <span className="text-gray-400">{e.host}</span>
                  <span className="ml-auto font-mono text-gray-500">{e.source_ip}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Drawer>
  );
}

/** Makes "raw log -> pipeline -> universal event" visually obvious at a glance. */
function TransformFlow({ event }: { event: UniversalEvent }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-base-border bg-base-bg/50 p-2.5 text-xs">
      <div className="flex items-center gap-1.5 rounded bg-white/5 px-2 py-1">
        <FileText className="h-3.5 w-3.5 text-gray-500" />
        Raw Log
      </div>
      <ArrowRight className="h-3.5 w-3.5 text-gray-700" />
      <div className="flex items-center gap-1.5 rounded bg-blue-500/10 px-2 py-1 text-blue-300">
        {event.parser} <span className="text-blue-500/70">v{event.parser_version}</span>
      </div>
      <ArrowRight className="h-3.5 w-3.5 text-gray-700" />
      {event.pii_mode !== "OFF" && (
        <>
          <div className="flex items-center gap-1.5 rounded bg-purple-500/10 px-2 py-1 text-purple-300">
            <ShieldCheck className="h-3.5 w-3.5" /> PII {event.pii_mode}
          </div>
          <ArrowRight className="h-3.5 w-3.5 text-gray-700" />
        </>
      )}
      <div className="flex items-center gap-1.5 rounded bg-emerald-500/10 px-2 py-1 text-emerald-300">
        <Sparkles className="h-3.5 w-3.5" /> Universal Event
        <span className="text-emerald-500/70">schema {event.schema_version}</span>
      </div>
      <span className="ml-auto text-gray-600">confidence {(event.confidence * 100).toFixed(0)}%</span>
    </div>
  );
}

function UniversalView({
  e,
  pii,
}: {
  e: UniversalEvent;
  pii: { field: string; kind: string; pseudonym: string }[];
}) {
  const rows: [string, unknown][] = Object.entries({
    timestamp: e.timestamp,
    source: e.source,
    host: e.host,
    event_type: e.event_type,
    severity: e.severity,
    username: e.username,
    email: e.email,
    source_ip: e.source_ip,
    destination_ip: e.destination_ip,
    source_port: e.source_port,
    destination_port: e.destination_port,
    protocol: e.protocol,
    action: e.action,
    status: e.status,
    process: e.process,
    service: e.service,
    url: e.url,
    http_method: e.http_method,
    response_code: e.response_code,
  }).filter(([, v]) => v !== null && v !== undefined && v !== "");

  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {e.severity && <StatusPill status={e.severity} />}
        <Badge tone="blue">{e.parser} v{e.parser_version}</Badge>
        <Badge tone="slate">schema {e.schema_version}</Badge>
        <Badge tone={e.pii_protected ? "green" : "slate"}>PII {e.pii_mode}</Badge>
        <Badge tone="slate">confidence {(e.confidence * 100).toFixed(0)}%</Badge>
      </div>

      <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-base-border/50 py-1">
            <span className="text-gray-500">{k}</span>
            <span className="truncate text-right font-mono text-xs text-gray-200">
              {String(v)}
              {e.field_confidence[k] !== undefined && (
                <span className="ml-2 text-2xs text-gray-600">
                  {(e.field_confidence[k] * 100).toFixed(0)}%
                </span>
              )}
            </span>
          </div>
        ))}
      </div>

      {e.message && (
        <div>
          <SectionHeader title="Message" />
          <p className="rounded-lg border border-base-border bg-base-bg p-2 text-xs">{e.message}</p>
        </div>
      )}

      {pii.length > 0 && (
        <div>
          <SectionHeader title="PII transformations" />
          <ul className="text-xs text-gray-400">
            {pii.map((t, i) => (
              <li key={i}>
                {t.field} ({t.kind}) → <span className="text-brand-fg">{t.pseudonym}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(e.extra).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-500">extra ({Object.keys(e.extra).length})</summary>
          <pre className="mt-1 overflow-x-auto rounded-lg border border-base-border bg-base-bg p-2">
            {JSON.stringify(e.extra, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
