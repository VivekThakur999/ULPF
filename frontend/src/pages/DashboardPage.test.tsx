import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  analyticsOverview: vi.fn(),
  analyticsPipeline: vi.fn(),
  listAlerts: vi.fn(),
  searchLogs: vi.fn(),
  getLogDetail: vi.fn(),
}));

import { analyticsOverview, analyticsPipeline, listAlerts, searchLogs } from "@/services/endpoints";
import DashboardPage from "./DashboardPage";

const OVERVIEW = {
  cards: {
    total_logs: 1200,
    processed: 1100,
    invalid: 40,
    duplicates: 20,
    quarantined: 3,
    normalized_events: 1080,
    alerts: 2,
    avg_processing_rate: 340,
    peak_processing_rate: 900,
  },
  charts: {
    logs_by_source: [],
    logs_by_format: [],
    events_by_severity: [],
    events_by_type: [],
    events_over_time: [],
    processing_outcomes: [],
    pii_transformations: [],
    alerts_by_severity: [],
    risk_distribution: [],
  },
  processing_success_rate: 96,
  shield_events: 5,
  source_status: [{ name: "linux", category: "linux", adapter: "FILE", status: "RECEIVING", events_processed: 10, last_received: null, configured: true }],
  generated_at: new Date().toISOString(),
};

const PIPELINE = {
  nodes: [
    { key: "sources", label: "Log Sources", count: 1, status: "ok" as const, detail: { configured_sources: 1 } },
    { key: "alert", label: "Alerts", count: 2, status: "critical" as const, detail: { total: 2, new: 2 } },
  ],
  generated_at: new Date().toISOString(),
};

beforeEach(() => {
  vi.clearAllMocks();
  (analyticsOverview as any).mockResolvedValue(OVERVIEW);
  (analyticsPipeline as any).mockResolvedValue(PIPELINE);
  (listAlerts as any).mockResolvedValue({
    total: 1,
    items: [
      { id: "a1", status: "NEW", severity: "high", risk_breakdown: { band: "high" } },
    ],
  });
  (searchLogs as any).mockResolvedValue({ total: 0, items: [], limit: 12, offset: 0, note: null });
});

describe("DashboardPage (Command Center)", () => {
  it("renders the command center title and live KPI values", async () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /Command Center/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("1,100")).toBeInTheDocument()); // events processed
    expect(screen.getByText("Processing success")).toBeInTheDocument();
    expect(screen.getAllByText("96%").length).toBeGreaterThan(0);
  });

  it("renders the pipeline visualization from real node counts", async () => {
    renderWithProviders(<DashboardPage />);
    await waitFor(() => expect(screen.getByText("Log Sources")).toBeInTheDocument());
    expect(screen.getByText("Alerts")).toBeInTheDocument();
  });

  it("shows an intelligent empty state for the live event stream when there are no events", async () => {
    renderWithProviders(<DashboardPage />);
    await waitFor(() => expect(screen.getByText("No events yet")).toBeInTheDocument());
  });

  it("surfaces a retryable error state when analytics fails", async () => {
    (analyticsOverview as any).mockRejectedValue(new Error("backend boom"));
    renderWithProviders(<DashboardPage />);
    await waitFor(() => expect(screen.getByText(/backend boom/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Retry/ })).toBeInTheDocument();
  });
});
