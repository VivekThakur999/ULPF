import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import { CheckCircle2, Package, Plus, XCircle } from "lucide-react";
import {
  createParserPack,
  getParser,
  listParsers,
  parserVersions,
  testParser,
  validateParserPack,
  wasmStatus,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { Badge, Card, DataTable, ErrorState, PageHeader, SkeletonTable, Spinner, StatusPill } from "@/components/ui";

const KIND_TONE: Record<string, "green" | "blue" | "amber" | "slate"> = {
  builtin: "slate",
  pack: "blue",
  "db-pack": "blue",
  wasm: "amber",
  "wasm-poc": "amber",
  "db-wasm": "amber",
};

export default function ParserPacksPage() {
  const { hasRole } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const parsers = useQuery({ queryKey: ["parsers"], queryFn: listParsers });
  const wasm = useQuery({ queryKey: ["wasm-status"], queryFn: wasmStatus });

  return (
    <div>
      <PageHeader
        eyebrow="Pipeline"
        title="Parser Packs"
        subtitle="Built-in parsers (in code) + declarative YAML packs + sandboxed WASM parsers. Packs are pure data — no pack code is ever executed."
        actions={
          hasRole("ADMIN") && (
            <button className="btn-primary" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" /> New pack
            </button>
          )
        }
      />

      {wasm.data && (
        <Card className="mb-4">
          <div className="flex items-center gap-2 text-sm">
            <Package className="h-4 w-4 text-brand-fg" />
            <span className="font-medium text-gray-200">WASM sandbox</span>
            <StatusPill
              status={wasm.data.available ? "online" : "error"}
              label={wasm.data.available ? `available (${wasm.data.runtime})` : "unavailable"}
            />
          </div>
          {wasm.data.available && (
            <ul className="mt-2 grid gap-1 text-xs text-gray-400 sm:grid-cols-2">
              {wasm.data.isolation.map((i) => (
                <li key={i}>· {i}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {parsers.isLoading ? (
        <SkeletonTable rows={8} cols={5} />
      ) : parsers.isError ? (
        <ErrorState error={parsers.error} onRetry={parsers.refetch} />
      ) : (
        <DataTable>
          <thead>
            <tr>
              <th>Name</th>
              <th>Format</th>
              <th>Version</th>
              <th>Kind</th>
              <th className="text-right">Patterns</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {parsers.data!.map((p) => (
              <tr key={p.name} className="clickable" onClick={() => setSelected(p.name)}>
                <td className="font-medium text-gray-200">{p.name}</td>
                <td className="font-mono text-xs">{p.format}</td>
                <td className="tnum">{p.version}</td>
                <td>
                  <Badge tone={KIND_TONE[p.kind] ?? "slate"}>{p.kind}</Badge>
                </td>
                <td className="text-right tnum">{p.pattern_count ?? "—"}</td>
                <td className="max-w-sm truncate text-gray-400">{p.description}</td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}

      {selected && <ParserDrawer name={selected} onClose={() => setSelected(null)} />}
      {creating && <CreatePackDrawer onClose={() => setCreating(false)} />}
    </div>
  );
}

function ParserDrawer({ name, onClose }: { name: string; onClose: () => void }) {
  const detail = useQuery({ queryKey: ["parser", name], queryFn: () => getParser(name) });
  const versions = useQuery({
    queryKey: ["parser-versions", name],
    queryFn: () => parserVersions(name),
    retry: false,
  });
  const [sample, setSample] = useState("");
  const testM = useMutation({ mutationFn: () => testParser(name, sample) });

  return (
    <Drawer onClose={onClose}>
      {detail.isLoading || !detail.data ? (
        <Spinner />
      ) : (
        <>
          <h2 className="font-semibold">{detail.data.name}</h2>
          <p className="mb-3 text-xs text-gray-500">
            {detail.data.format} · v{detail.data.version} · {detail.data.kind}
          </p>

          {detail.data.limits && (
            <div className="mb-3 text-xs text-gray-400">
              <div className="label">Sandbox limits</div>
              fuel {detail.data.limits.fuel.toLocaleString()} · timeout {detail.data.limits.timeout_ms}ms ·
              mem {(detail.data.limits.max_memory_bytes / 1024 / 1024).toFixed(0)} MiB
            </div>
          )}

          {detail.data.tests && (
            <div className="mb-3">
              <div className="label">Embedded self-tests</div>
              <div className="flex items-center gap-2 text-sm">
                {detail.data.tests.passed === detail.data.tests.total && detail.data.tests.total > 0 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-amber-400" />
                )}
                {detail.data.tests.passed}/{detail.data.tests.total} passing
              </div>
              {detail.data.tests.results.map((r) => (
                <div key={r.index} className="mt-1 text-xs">
                  <span className={r.ok ? "text-emerald-400" : "text-sev-critical"}>
                    {r.ok ? "PASS" : "FAIL"}
                  </span>{" "}
                  <span className="font-mono text-gray-500">{r.input.slice(0, 70)}</span>
                  {!r.ok && (
                    <pre className="ml-6 text-[10px] text-amber-300">
                      {JSON.stringify(r.mismatches, null, 1)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mb-3">
            <div className="label">Parser test</div>
            <input
              className="input mb-2"
              placeholder="paste a sample line…"
              value={sample}
              onChange={(e) => setSample(e.target.value)}
            />
            <button
              className="btn-ghost"
              disabled={!sample || testM.isPending}
              onClick={() => testM.mutate()}
            >
              Run against this parser
            </button>
            {testM.data && (
              <div className="mt-2 rounded border border-base-border p-2 text-xs">
                <div className="mb-1 text-gray-400">
                  can_parse {(testM.data.can_parse * 100).toFixed(0)}% · confidence{" "}
                  {(testM.data.confidence * 100).toFixed(0)}%
                  {testM.data.partial && <span className="text-amber-400"> · partial</span>}
                </div>
                <pre className="overflow-x-auto">{JSON.stringify(testM.data.fields, null, 2)}</pre>
                {testM.data.errors.map((e, i) => (
                  <p key={i} className="text-sev-critical">✖ {e}</p>
                ))}
              </div>
            )}
          </div>

          {versions.data && (
            <div className="mb-3">
              <div className="label">Version history</div>
              {versions.data.versions.map((v) => (
                <div key={v.version} className="flex items-center gap-2 text-xs">
                  <span className="font-mono">{v.version}</span>
                  {v.is_active && <Badge tone="green">active</Badge>}
                  <span className="text-gray-500">{new Date(v.created_at).toLocaleString()}</span>
                  {v.tests_passed != null && (
                    <span className="text-gray-500">{v.tests_passed} tests ✓</span>
                  )}
                </div>
              ))}
            </div>
          )}
          {versions.isError && (
            <p className="mb-3 text-xs text-gray-600">
              Built-in parser — unversioned (versioning applies to packs).
            </p>
          )}

          {detail.data.definition && (
            <details>
              <summary className="cursor-pointer text-xs text-gray-500">definition (read-only)</summary>
              <pre className="mt-1 max-h-64 overflow-auto rounded bg-base-bg p-2 text-[10px]">
                {JSON.stringify(detail.data.definition, null, 2)}
              </pre>
            </details>
          )}
        </>
      )}
    </Drawer>
  );
}

const STARTER_YAML = `parser:
  name: my_custom
  version: 1.0.0
  format: MY_CUSTOM
  specificity: 5
  description: example pack
detect:
  hints:
    - 'MYAPP'
patterns:
  - '^MYAPP (?P<username>\\S+) from (?P<source_ip>\\S+) status=(?P<status>\\w+)$'
event_type:
  default: authentication_failure
tests:
  - input: 'MYAPP alice from 10.0.0.5 status=denied'
    expect: { username: alice, source_ip: 10.0.0.5, status: denied }
`;

function CreatePackDrawer({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [yamlText, setYamlText] = useState(STARTER_YAML);
  const [err, setErr] = useState("");
  const validate = useMutation({
    mutationFn: () => validateParserPack(yamlText),
    onError: (e) => setErr(apiError(e)),
  });
  const create = useMutation({
    mutationFn: () => createParserPack(yamlText),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["parsers"] });
      onClose();
    },
    onError: (e) => setErr(apiError(e)),
  });

  return (
    <Drawer onClose={onClose}>
      <h2 className="mb-1 font-semibold">New parser pack</h2>
      <p className="mb-3 text-xs text-gray-500">
        YAML only. On save it is validated, its embedded tests are run, and it is hot-registered.
        Set <code>parser.kind: wasm</code> + a <code>wat:</code> field for a sandboxed WASM parser.
      </p>
      <div className="rounded border border-base-border">
        <Editor
          height="300px"
          defaultLanguage="yaml"
          theme="vs-dark"
          value={yamlText}
          onChange={(v) => setYamlText(v ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 12, scrollBeyondLastLine: false }}
        />
      </div>
      {err && <div className="mt-2"><ErrorState error={err} /></div>}
      {validate.data && (
        <div className="mt-2 rounded border border-base-border p-2 text-xs">
          <span className={validate.data.valid ? "text-emerald-400" : "text-sev-critical"}>
            {validate.data.valid ? "VALID" : "INVALID"}
          </span>
          {validate.data.problems.map((p, i) => (
            <p key={i} className="text-sev-critical">✖ {p}</p>
          ))}
          <p className="text-gray-400">
            tests: {validate.data.tests.passed}/{validate.data.tests.total}
          </p>
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <button className="btn-ghost" onClick={() => { setErr(""); validate.mutate(); }}>
          Validate
        </button>
        <button
          className="btn-primary"
          disabled={create.isPending}
          onClick={() => { setErr(""); create.mutate(); }}
        >
          Save &amp; register
        </button>
      </div>
    </Drawer>
  );
}

function Drawer({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-[2px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="flex h-full w-full max-w-2xl animate-slide-in-right flex-col border-l border-base-border bg-base-panel shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-end border-b border-base-border px-5 py-3">
          <button className="btn-ghost py-1 text-xs" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}
