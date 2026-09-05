import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  aiStatus: vi.fn(),
  aiExplain: vi.fn(),
  listAlerts: vi.fn(),
  searchLogs: vi.fn(),
}));

import { aiStatus, aiExplain, listAlerts, searchLogs } from "@/services/endpoints";
import AssistantPage from "./AssistantPage";
import AIExplanation from "@/components/AIExplanation";

const STATUS = {
  provider: "LOCAL OFFLINE EXPLAINER",
  offline: true,
  model: null,
  available: true,
  fallback_active: false,
  note: "Deterministic local offline explainer. No model, no network.",
};

const EXPLAIN_EVENT = {
  kind: "event" as const,
  generated_at: new Date().toISOString(),
  provider: "LOCAL OFFLINE EXPLAINER",
  offline: true,
  model: null,
  evidence: {
    event: { id: "e1", event_type: "authentication_failure", source: "linux", source_ip: "IP_ABC", severity: "high" },
    parser: { name: "linux_auth", version: "1.0.0" },
    raw_log: "Sep  2 09:02:11 db-02 sshd[1]: Failed password for admin from 1.2.3.4 port 22 ssh2",
  },
  explanation: {
    provider: "LOCAL OFFLINE EXPLAINER",
    offline: true,
    model: null,
    summary: "This is a authentication failure from the linux source.",
    important_fields: [{ field: "source_ip", value: "IP_ABC", note: "originating address" }],
    why_it_matters: "A login attempt failed.",
    detection_context: "This event did not itself trigger an alert.",
    related_activity: "3 related events across 1 source.",
    suggested_steps: ["Confirm whether the source IP is expected."],
    disclaimer: "AI explanations are advisory only and do not determine security decisions.",
    fallback_from: null,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  (aiStatus as any).mockResolvedValue(STATUS);
  (searchLogs as any).mockResolvedValue({ total: 1, items: [
    { id: "e1", source: "linux", event_type: "authentication_failure", host: "db-02", source_ip: "IP_ABC" },
  ], limit: 15, offset: 0, note: null });
  (listAlerts as any).mockResolvedValue({ total: 0, items: [] });
});

describe("AssistantPage", () => {
  it("loads and shows the local offline provider status", async () => {
    renderWithProviders(<AssistantPage />);
    expect(screen.getByRole("heading", { name: "AI Log Assistant" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/LOCAL OFFLINE EXPLAINER/).length).toBeGreaterThan(0));
    expect(screen.getByText(/No model, no network/)).toBeInTheDocument();
  });

  it("lets the analyst pick an event and shows the explanation with an evidence boundary", async () => {
    (aiExplain as any).mockResolvedValue(EXPLAIN_EVENT);
    renderWithProviders(<AssistantPage />);

    const row = await screen.findByRole("button", { name: /authentication_failure/ });
    fireEvent.click(row);
    fireEvent.click(screen.getByRole("button", { name: /Explain/ }));

    await waitFor(() => expect(screen.getByText("ULPF Evidence")).toBeInTheDocument());
    expect(screen.getByText("AI Explanation")).toBeInTheDocument();
    expect(screen.getByText(/This is a authentication failure/)).toBeInTheDocument();
    expect(screen.getByText(/advisory only/)).toBeInTheDocument();
    expect(aiExplain).toHaveBeenCalledWith({ kind: "event", event_id: "e1" });
  });

  it("shows an error state when explain fails", async () => {
    (aiExplain as any).mockRejectedValue(new Error("boom"));
    renderWithProviders(<AssistantPage />);
    fireEvent.click(await screen.findByRole("button", { name: /authentication_failure/ }));
    fireEvent.click(screen.getByRole("button", { name: /Explain/ }));
    await waitFor(() => expect(screen.getByText(/boom/)).toBeInTheDocument());
  });

  it("labels pasted logs as untrusted", async () => {
    renderWithProviders(<AssistantPage />);
    fireEvent.click(screen.getByRole("button", { name: "Paste Log" }));
    expect(screen.getByText("UNTRUSTED LOG INPUT")).toBeInTheDocument();
  });

  it("auto-runs when deep-linked with ?alert=", async () => {
    (listAlerts as any).mockResolvedValue({ total: 1, items: [
      { id: "a1", title: "Brute force", severity: "high", risk_score: 80, risk_breakdown: { band: "high", factors: [] } },
    ] });
    (aiExplain as any).mockResolvedValue({ ...EXPLAIN_EVENT, kind: "alert",
      evidence: { alert: { title: "Brute force", severity: "high", risk_score: 80, status: "NEW",
        rule_key: "RULE_1", reason: "many failures", risk_breakdown: { band: "high", factors: [] } } } });
    renderWithProviders(<AssistantPage />, { route: "/assistant?alert=a1" });
    await waitFor(() => expect(aiExplain).toHaveBeenCalledWith({ kind: "alert", alert_id: "a1" }));
  });
});

describe("AIExplanation evidence boundary", () => {
  it("keeps ULPF evidence and AI explanation in separate sections", () => {
    renderWithProviders(<AIExplanation data={EXPLAIN_EVENT as any} />);
    const evidence = screen.getByText("ULPF Evidence").closest("section")!;
    const ai = screen.getByText("AI Explanation").closest("section")!;
    expect(evidence).not.toBe(ai);
    // the AI summary text is only inside the AI section
    expect(ai).toHaveTextContent(/This is a authentication failure/);
    expect(evidence).not.toHaveTextContent(/This is a authentication failure/);
  });
});
