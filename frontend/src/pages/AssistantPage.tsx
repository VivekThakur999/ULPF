import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Sparkles } from "lucide-react";
import {
  aiExplain,
  aiStatus,
  listAlerts,
  searchLogs,
  type AIExplainResponse,
} from "@/services/endpoints";
import { apiError } from "@/services/api";
import { Badge, Card, ErrorState, PageHeader, Spinner } from "@/components/ui";
import AIExplanation from "@/components/AIExplanation";

type Mode = "event" | "alert" | "raw";

export default function AssistantPage() {
  const [params, setParams] = useSearchParams();
  const [mode, setMode] = useState<Mode>(
    params.get("alert") ? "alert" : params.get("event") ? "event" : "event",
  );
  const [eventQuery, setEventQuery] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<string | null>(params.get("event"));
  const [selectedAlert, setSelectedAlert] = useState<string | null>(params.get("alert"));
  const [rawText, setRawText] = useState("");
  const [result, setResult] = useState<AIExplainResponse | null>(null);
  const [err, setErr] = useState("");

  const status = useQuery({ queryKey: ["ai-status"], queryFn: aiStatus });

  const events = useQuery({
    queryKey: ["ai-events", eventQuery],
    queryFn: () => searchLogs({ text: eventQuery || undefined, limit: 15 }),
    enabled: mode === "event",
  });
  const alerts = useQuery({
    queryKey: ["ai-alerts"],
    queryFn: () => listAlerts(),
    enabled: mode === "alert",
  });

  const explain = useMutation({
    mutationFn: () => {
      if (mode === "event" && selectedEvent) return aiExplain({ kind: "event", event_id: selectedEvent });
      if (mode === "alert" && selectedAlert) return aiExplain({ kind: "alert", alert_id: selectedAlert });
      if (mode === "raw" && rawText.trim()) return aiExplain({ kind: "raw", text: rawText });
      return Promise.reject(new Error("Pick an event/alert or paste a log first"));
    },
    onSuccess: (r) => {
      setErr("");
      setResult(r);
    },
    onError: (e) => setErr(apiError(e)),
  });

  // deep-link auto-run
  useEffect(() => {
    if ((params.get("event") || params.get("alert")) && !result && !explain.isPending) {
      explain.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setModeAndClear = (m: Mode) => {
    setMode(m);
    setResult(null);
    setErr("");
    setParams({});
  };

  return (
    <div>
      <PageHeader
        title="AI Log Assistant"
        subtitle="Local, evidence-grounded explanations for ULPF events and alerts. AI describes ULPF's deterministic findings — it never changes them."
        actions={
          status.data && (
            <Badge tone={status.data.offline ? "green" : "amber"}>
              {status.data.provider}
              {status.data.fallback_active ? " (fallback)" : ""}
            </Badge>
          )
        }
      />

      {status.data && (
        <p className="mb-4 text-xs text-gray-500">{status.data.note}</p>
      )}

      <Card className="mb-4">
        <div className="mb-3 flex gap-2 border-b border-base-border text-sm">
          {(["event", "alert", "raw"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setModeAndClear(m)}
              className={`px-3 py-1.5 ${mode === m ? "border-b-2 border-brand text-brand-fg" : "text-gray-400"}`}
            >
              {m === "event" ? "Select Event" : m === "alert" ? "Select Alert" : "Paste Log"}
            </button>
          ))}
        </div>

        {mode === "event" && (
          <div>
            <input
              className="input mb-2"
              placeholder="search events (message, host, IP, user)…"
              value={eventQuery}
              onChange={(e) => setEventQuery(e.target.value)}
            />
            {events.isLoading ? (
              <Spinner />
            ) : events.isError ? (
              <ErrorState error={events.error} onRetry={events.refetch} />
            ) : (
              <div className="max-h-56 overflow-y-auto rounded border border-base-border">
                {(events.data?.items ?? []).map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => setSelectedEvent(ev.id)}
                    className={`flex w-full items-center gap-2 border-b border-base-border/50 px-2 py-1.5 text-left text-xs last:border-0 hover:bg-white/5 ${
                      selectedEvent === ev.id ? "bg-brand/10" : ""
                    }`}
                  >
                    <Badge tone="slate">{ev.source}</Badge>
                    <span>{ev.event_type ?? "event"}</span>
                    <span className="text-gray-500">{ev.host}</span>
                    <span className="ml-auto font-mono text-gray-500">{ev.source_ip}</span>
                  </button>
                ))}
                {(events.data?.items ?? []).length === 0 && (
                  <p className="p-3 text-xs text-gray-500">No events — ingest logs first.</p>
                )}
              </div>
            )}
          </div>
        )}

        {mode === "alert" && (
          <div>
            {alerts.isLoading ? (
              <Spinner />
            ) : alerts.isError ? (
              <ErrorState error={alerts.error} onRetry={alerts.refetch} />
            ) : (
              <select
                className="input"
                value={selectedAlert ?? ""}
                onChange={(e) => setSelectedAlert(e.target.value || null)}
              >
                <option value="">Select an alert…</option>
                {(alerts.data?.items ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    [{a.severity}] {a.title} — risk {Math.round(a.risk_score)}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {mode === "raw" && (
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Badge tone="amber">UNTRUSTED LOG INPUT</Badge>
              <span className="text-xs text-gray-500">not stored · treated strictly as data</span>
            </div>
            <textarea
              className="input h-28 font-mono text-xs"
              placeholder="paste one raw log line…"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
          </div>
        )}

        <button
          className="btn-primary mt-3"
          disabled={
            explain.isPending ||
            (mode === "event" && !selectedEvent) ||
            (mode === "alert" && !selectedAlert) ||
            (mode === "raw" && !rawText.trim())
          }
          onClick={() => explain.mutate()}
        >
          <Sparkles className={`h-4 w-4 ${explain.isPending ? "animate-pulse" : ""}`} />
          Explain
        </button>
      </Card>

      {err && <div className="mb-4"><ErrorState error={err} /></div>}
      {explain.isPending && <Spinner label="Generating explanation…" />}
      {result && !explain.isPending && <AIExplanation data={result} />}
      {!result && !explain.isPending && !err && (
        <p className="text-sm text-gray-500">
          Choose an event or alert (or paste a log) and click <b>Explain</b> to see the
          ULPF evidence alongside a local, advisory explanation.
        </p>
      )}
    </div>
  );
}
