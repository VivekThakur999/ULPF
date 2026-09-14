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

type Tab = "fields" | "security" | "parser" | "raw" | "correlated";

export default function EventDetail({ eventId, onClose }: { eventId: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ["log", eventId], queryFn: () => getLogDetail(eventId) });
  const [tab, setTab] = useState<Tab>("fields");
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
          <EventKpis event={q.data.event} correlatedCount={q.data.related_events.length} />

          <div className="mb-3">
            <Tabs<Tab>
              tabs={[
                { key: "fields", label: "Normalized Fields" },
                { key: "security", label: "Security & PII" },
                { key: "parser", label: "Parser & Pipeline" },
                { key: "raw", label: "Raw Log" },
                { key: "correlated", label: `Correlated Activity (${q.data.related_events.length})` },
              ]}
              value={tab}
              onChange={setTab}
            />
          </div>

          {tab === "fields" && <FieldsView e={q.data.event} />}

          {tab === "security" && (
            <div className="space-y-5 text-sm">
              <section>
                <SectionHeader title="Security" hint="Security Shield verdict + any detections raised on this record" />
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={q.data.raw_log?.security_verdict ?? "SAFE"} />
                  <span className="text-xs text-gray-500">
                    Screened before parsing — the verdict never changes after ingestion.
                  </span>
                </div>
                {q.data.security_events.length > 0 ? (
                  <div className="mt-2 space-y-1.5">
                    {q.data.security_events.map((s) => (
                      <div key={s.id} className="rounded-lg border border-sev-high/40 bg-sev-high/10 p-2 text-xs">
                        <b>{s.detection_type}</b> ({s.severity}) — {s.reason}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-gray-500">No security-shield detections on this record.</p>
                )}
              </section>

              <section>
                <SectionHeader title="PII Protection" hint={`Mode: ${q.data.event.pii_mode}`} />
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge tone={q.data.event.pii_protected ? "green" : "slate"}>
                    {q.data.event.pii_protected ? "Protected" : "Not protected"}
                  </Badge>
                  <Badge tone="slate">{q.data.pii_transformations.length} field(s) transformed</Badge>
                </div>
                {q.data.pii_transformations.length > 0 ? (
                  <ul className="space-y-1 text-xs text-gray-500">
                    {q.data.pii_transformations.map((t, i) => (
                      <li key={i}>
                        <span className="font-mono text-slate-700">{t.field}</span> ({t.kind}) →{" "}
                        <span className="font-mono text-brand-fg">{t.pseudonym}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-500">No identifiers on this record required pseudonymization.</p>
                )}
              </section>
            </div>
          )}

          {tab === "parser" && (
            <div className="space-y-5 text-sm">
              <section>
                <SectionHeader title="Parser" />
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <MiniStat label="Name" value={q.data.event.parser} />
                  <MiniStat label="Version" value={q.data.event.parser_version} />
                  <MiniStat label="Confidence" value={`${(q.data.event.confidence * 100).toFixed(0)}%`} />
                  <MiniStat label="Schema" value={q.data.event.schema_version} />
                  <MiniStat label="Template" value={q.data.event.template_id ?? "—"} mono />
                  {q.data.job && <MiniStat label="Detected format" value={q.data.job.detected_format} />}
                </div>
              </section>

              <section>
                <SectionHeader title="Pipeline" hint="Every stage this record passed through" />
                <ol className="space-y-2">
                  {q.data.pipeline.map((s, i) => (
                    <li key={s.stage} className="surface-2 p-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-2xs text-gray-500">{i + 1}</span>
                        <span className="font-medium text-slate-800">{STAGE_LABEL[s.stage] ?? s.stage}</span>
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
              </section>
            </div>
          )}

          {tab === "raw" && (
            <div className="space-y-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                {q.data.job && <Badge tone="blue">{q.data.job.detected_format}</Badge>}
                <span className="text-xs text-gray-500">
                  line {q.data.raw_log?.line_number} · {q.data.job?.filename}
                </span>
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-base-border bg-base-bg p-3 font-mono text-xs text-slate-800">
                {q.data.raw_log?.content ?? q.data.event.raw_log}
              </pre>
            </div>
          )}

          {tab === "correlated" && (
            <div className="space-y-1.5 text-sm">
              {q.data.related_events.length === 0 && (
                <p className="text-gray-500">No correlated events.</p>
              )}
              {q.data.related_events.map((e) => (
                <div key={e.id} className="surface-2 flex flex-wrap items-center gap-2 p-2 text-xs">
                  <span className="font-mono text-gray-500">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <Badge tone="slate">{e.source}</Badge>
                  <span className="text-slate-700">{e.event_type}</span>
                  <span className="text-slate-500">{e.host}</span>
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
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-base-border bg-base-bg/50 p-2.5 text-xs">
      <div className="flex items-center gap-1.5 rounded bg-slate-100 px-2 py-1 text-slate-600">
        <FileText className="h-3.5 w-3.5 text-slate-500" />
        Raw Log
      </div>
      <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
      <div className="flex items-center gap-1.5 rounded bg-blue-100 px-2 py-1 text-blue-800">
        {event.parser} <span className="text-blue-700/80">v{event.parser_version}</span>
      </div>
      <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
      {event.pii_mode !== "OFF" && (
        <>
          <div className="flex items-center gap-1.5 rounded bg-purple-100 px-2 py-1 text-purple-800">
            <ShieldCheck className="h-3.5 w-3.5" /> PII {event.pii_mode}
          </div>
          <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
        </>
      )}
      <div className="flex items-center gap-1.5 rounded bg-emerald-100 px-2 py-1 text-emerald-800">
        <Sparkles className="h-3.5 w-3.5" /> Universal Event
        <span className="text-emerald-700/80">schema {event.schema_version}</span>
      </div>
    </div>
  );
}

/** ULPF EVENT at-a-glance strip — severity / confidence / processing status / correlation, all real. */
function EventKpis({ event, correlatedCount }: { event: UniversalEvent; correlatedCount: number }) {
  return (
    <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <MiniStat label="Severity" value={<StatusPill status={event.severity ?? "info"} />} raw />
      <MiniStat label="Confidence" value={`${(event.confidence * 100).toFixed(0)}%`} />
      <MiniStat
        label="Processing"
        value={<StatusPill status={event.processing_status} dot={false} />}
        raw
      />
      <MiniStat label="Correlated" value={String(correlatedCount)} />
    </div>
  );
}

function MiniStat({
  label,
  value,
  mono,
  raw,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  raw?: boolean;
}) {
  return (
    <div className="surface-2 p-2.5">
      <div className="text-2xs uppercase tracking-wide text-gray-500">{label}</div>
      {raw ? (
        <div className="mt-1">{value}</div>
      ) : (
        <div className={`mt-0.5 truncate text-sm font-semibold text-slate-800 ${mono ? "font-mono text-xs" : ""}`}>
          {value}
        </div>
      )}
    </div>
  );
}

function FieldsView({ e }: { e: UniversalEvent }) {
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
      <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-base-border/50 py-1">
            <span className="text-gray-500">{k}</span>
            <span className="truncate text-right font-mono text-xs text-slate-800">
              {String(v)}
              {e.field_confidence[k] !== undefined && (
                <span className="ml-2 text-2xs text-slate-400">
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
