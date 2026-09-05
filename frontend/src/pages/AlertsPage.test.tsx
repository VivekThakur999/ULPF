import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  listAlerts: vi.fn(),
  runDetection: vi.fn(),
  getAlert: vi.fn(),
  updateAlert: vi.fn(),
  getLogDetail: vi.fn(),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ hasRole: () => true, user: { role: "ANALYST" } }),
}));

import { listAlerts, getAlert } from "@/services/endpoints";
import AlertsPage from "./AlertsPage";

const ALERT = {
  id: "a1",
  ts: new Date().toISOString(),
  title: "Multiple failed logins from IP_ABC",
  severity: "high",
  risk_score: 82,
  source: "linux",
  rule_key: "RULE_1",
  description: "brute force",
  reason: "12 failed logins from IP_ABC",
  risk_breakdown: { score: 82, band: "high", summary: "elevated", factors: [{ factor: "repeated_failures", points: 35, detail: "12 failures" }] },
  entity: { source_ip: "IP_ABC", type: "source_ip" },
  related_event_ids: ["e1", "e2"],
  affected_hosts: ["db-02"],
  recommended_response: { action: "BLOCK", label: "Block source IP", target: {}, auto_execute: false, note: "sim only", urgency: "high" },
  status: "NEW",
  resolution_note: "",
  updated_at: new Date().toISOString(),
};

beforeEach(() => {
  vi.clearAllMocks();
  (listAlerts as any).mockResolvedValue({ total: 1, items: [ALERT] });
  (getAlert as any).mockResolvedValue({
    alert: ALERT,
    timeline: [
      { ts: new Date().toISOString(), event_id: "e1", source: "linux", host: "db-02", event_type: "auth_fail", action: null, status: null, severity: "high", summary: "failed password" },
    ],
    related_events: [],
    correlation: {},
  });
});

describe("AlertsPage (SOC queue)", () => {
  it("renders the alert queue with summary KPIs", async () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByRole("heading", { name: "Security Alerts" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Multiple failed logins from IP_ABC")).toBeInTheDocument());
    expect(screen.getByText("Investigating")).toBeInTheDocument(); // KPI label
  });

  it("opens the alert investigation drawer with the correlation chain and risk meter", async () => {
    renderWithProviders(<AlertsPage />);
    fireEvent.click(await screen.findByText("Multiple failed logins from IP_ABC"));
    expect(await screen.findByText("Why this triggered")).toBeInTheDocument();
    expect(await screen.findByText(/RULE_1 triggered/)).toBeInTheDocument();
    expect(await screen.findByText("repeated failures")).toBeInTheDocument();
  });

  it("shows an empty state when there are no alerts", async () => {
    (listAlerts as any).mockResolvedValue({ total: 0, items: [] });
    renderWithProviders(<AlertsPage />);
    await waitFor(() => expect(screen.getByText("No alerts")).toBeInTheDocument());
  });
});
