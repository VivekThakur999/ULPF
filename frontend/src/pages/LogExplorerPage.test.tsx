import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  searchLogs: vi.fn(),
  getLogDetail: vi.fn(),
  logStats: vi.fn(),
}));

import { searchLogs, getLogDetail, logStats } from "@/services/endpoints";
import LogExplorerPage from "./LogExplorerPage";

const EVENT = {
  id: "e1",
  source: "linux",
  event_type: "authentication_failure",
  host: "db-02",
  username: "USER_1",
  email: null,
  source_ip: "IP_ABC",
  severity: "high",
  parser: "linux_auth",
  timestamp: new Date().toISOString(),
  processing_status: "ok",
};

beforeEach(() => {
  vi.clearAllMocks();
  (searchLogs as any).mockResolvedValue({ total: 1, items: [EVENT], limit: 50, offset: 0, note: null });
  (logStats as any).mockResolvedValue({
    total_events: 1,
    facets: {
      source: [{ value: "linux", count: 1 }],
      host: [{ value: "db-02", count: 1 }],
      event_type: [{ value: "authentication_failure", count: 1 }],
      severity: [{ value: "high", count: 1 }],
      parser: [{ value: "linux_auth", count: 1 }],
      processing_status: [{ value: "ok", count: 1 }],
    },
    timeseries: [],
  });
  (getLogDetail as any).mockResolvedValue({
    event: { ...EVENT, raw_log: "raw line", parser_version: "1.0.0", schema_version: "1.0", pii_mode: "DETERMINISTIC_HASH", pii_protected: true, confidence: 0.9, field_confidence: {}, extra: {}, message: "auth failure" },
    raw_log: { id: "r1", line_number: 1, content: "raw line", status: "PROCESSED", security_verdict: "SAFE", processing_errors: [] },
    job: { id: "j1", filename: "auth.log", detected_format: "LINUX_SYSLOG", source_name: "linux" },
    pipeline: [],
    pii_transformations: [],
    related_events: [],
    security_events: [],
  });
});

describe("LogExplorerPage", () => {
  it("renders the investigation console with a dense event row", async () => {
    renderWithProviders(<LogExplorerPage />);
    expect(screen.getByRole("heading", { name: "Log Explorer" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("authentication_failure")).toBeInTheDocument());
    expect(screen.getByText("IP_ABC")).toBeInTheDocument();
  });

  it("opens the event investigation drawer on row click", async () => {
    renderWithProviders(<LogExplorerPage />);
    fireEvent.click(await screen.findByText("authentication_failure"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(await screen.findByText("auth failure")).toBeInTheDocument();
    expect(screen.getByText("authentication_failure · linux")).toBeInTheDocument();
  });

  it("shows active filter chips and clears them", async () => {
    renderWithProviders(<LogExplorerPage />);
    fireEvent.change(screen.getByPlaceholderText(/search message, raw log, host/), { target: { value: "admin" } });
    fireEvent.click(screen.getByRole("button", { name: /Search/ }));
    await waitFor(() => expect(screen.getByText("clear all")).toBeInTheDocument());
  });

  it("renders an empty state when nothing matches", async () => {
    (searchLogs as any).mockResolvedValue({ total: 0, items: [], limit: 50, offset: 0, note: null });
    renderWithProviders(<LogExplorerPage />);
    await waitFor(() => expect(screen.getByText("No events yet")).toBeInTheDocument());
  });

  it("populates the severity facet from real /logs/stats counts and filters on selection", async () => {
    renderWithProviders(<LogExplorerPage />);
    const severitySelect = (await screen.findByLabelText("Severity")) as HTMLSelectElement;
    await waitFor(() =>
      expect(severitySelect.querySelector('option[value="high"]')?.textContent).toBe("high (1)"),
    );
    fireEvent.change(severitySelect, { target: { value: "high" } });
    await waitFor(() => expect(searchLogs).toHaveBeenLastCalledWith(expect.objectContaining({ severity: "high" })));
  });

  it("organizes the investigation drawer into Security & PII and Parser & Pipeline tabs", async () => {
    renderWithProviders(<LogExplorerPage />);
    fireEvent.click(await screen.findByText("authentication_failure"));
    const dialog = await screen.findByRole("dialog");

    fireEvent.click(await within(dialog).findByRole("button", { name: "Security & PII" }));
    expect(await within(dialog).findByText("Protected")).toBeInTheDocument();
    expect(within(dialog).getByText("PII Protection")).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Parser & Pipeline" }));
    expect(await within(dialog).findByText("Name")).toBeInTheDocument();
    expect(within(dialog).getAllByText("linux_auth").length).toBeGreaterThan(0);
  });
});
