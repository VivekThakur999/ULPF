import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import {
  getPrivacySettings,
  previewPseudonym,
  updatePrivacySettings,
  type PiiSettings,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { Badge, Card, ErrorState, PageHeader, Spinner } from "@/components/ui";

const MODES = [
  ["OFF", "No protection - raw identifiers stored as-is."],
  ["MASK", "Partial masking (192.168.x.x). Not reversible, not correlatable."],
  ["DETERMINISTIC_HASH", "Keyed HMAC pseudonyms (IP_7F82A1). Stable per scope - correlate without exposing the raw value."],
] as const;

export default function PrivacyPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole("ADMIN");
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["privacy"], queryFn: getPrivacySettings });
  const [draft, setDraft] = useState<PiiSettings | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (settings.data) setDraft(settings.data);
  }, [settings.data]);

  const save = useMutation({
    mutationFn: (body: Partial<PiiSettings>) => updatePrivacySettings(body),
    onSuccess: () => {
      setErr("");
      qc.invalidateQueries({ queryKey: ["privacy"] });
    },
    onError: (e) => setErr(apiError(e)),
  });

  if (settings.isLoading || !draft) return <Spinner />;
  if (settings.isError) return <ErrorState error={settings.error} onRetry={settings.refetch} />;

  const set = <K extends keyof PiiSettings>(k: K, v: PiiSettings[K]) =>
    setDraft({ ...draft, [k]: v });

  return (
    <div>
      <PageHeader
        eyebrow="System"
        title="Privacy Configuration"
        subtitle="Deterministic pseudonymization lets analysts correlate an IP or user across sources without seeing the raw identifier. This alone is not a GDPR-compliance claim."
      />

      {err && <div className="mb-4"><ErrorState error={err} /></div>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4 text-brand-fg" /> PII mode
          </h2>
          <div className="space-y-2">
            {MODES.map(([m, desc]) => (
              <label
                key={m}
                className={`flex cursor-pointer gap-3 rounded-md border p-3 text-sm ${
                  draft.mode === m ? "border-brand bg-brand/10" : "border-base-border"
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  className="mt-0.5"
                  disabled={!isAdmin}
                  checked={draft.mode === m}
                  onChange={() => set("mode", m as PiiSettings["mode"])}
                />
                <span>
                  <span className="font-medium">{m}</span>
                  <span className="block text-xs text-gray-400">{desc}</span>
                </span>
              </label>
            ))}
          </div>

          <h3 className="mb-2 mt-4 text-xs font-semibold uppercase text-gray-500">
            Protected identifiers
          </h3>
          {(["protect_ip", "protect_email", "protect_username", "protect_host"] as const).map((k) => (
            <label key={k} className="flex items-center gap-2 py-1 text-sm">
              <input
                type="checkbox"
                disabled={!isAdmin}
                checked={draft[k]}
                onChange={(e) => set(k, e.target.checked)}
              />
              {k.replace("protect_", "").replace("_", " ")}
            </label>
          ))}

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <label className="label">Scope</label>
              <input
                className="input"
                disabled={!isAdmin}
                value={draft.scope}
                onChange={(e) => set("scope", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Token length</label>
              <input
                type="number"
                className="input"
                min={4}
                max={16}
                disabled={!isAdmin}
                value={draft.token_length}
                onChange={(e) => set("token_length", Number(e.target.value))}
              />
            </div>
          </div>

          {isAdmin ? (
            <button
              className="btn-primary mt-4"
              disabled={save.isPending}
              onClick={() => save.mutate(draft)}
            >
              Save configuration
            </button>
          ) : (
            <p className="mt-4 text-xs text-gray-500">Read-only. ADMIN role required to change.</p>
          )}
        </Card>

        <PreviewPanel mode={draft.mode} />
      </div>
    </div>
  );
}

function PreviewPanel({ mode }: { mode: string }) {
  const [value, setValue] = useState("192.168.1.50");
  const [kind, setKind] = useState("ip");
  const preview = useQuery({
    queryKey: ["pii-preview", value, kind, mode],
    queryFn: () => previewPseudonym(value, kind),
    enabled: value.length > 0,
  });

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold">Live transformation preview</h2>
      <div className="grid grid-cols-3 gap-2">
        <input
          className="input col-span-2"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
          {["ip", "email", "username", "host"].map((k) => (
            <option key={k}>{k}</option>
          ))}
        </select>
      </div>
      {preview.data && (
        <div className="mt-4 space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-mono text-gray-400">{preview.data.input}</span>
            <span className="text-gray-600">→</span>
            <span className="font-mono text-brand-fg">{preview.data.output}</span>
            <Badge tone="slate">{preview.data.mode}</Badge>
          </div>
          <p className="text-xs text-gray-500">{preview.data.note}</p>
          <p className="text-xs text-gray-600">
            Run the same value again — under DETERMINISTIC_HASH you always get the same token,
            which is what makes cross-source correlation possible.
          </p>
        </div>
      )}
    </Card>
  );
}
