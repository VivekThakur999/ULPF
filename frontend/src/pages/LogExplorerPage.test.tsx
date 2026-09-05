import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  searchLogs: vi.fn(),
  getLogDetail: vi.fn(),
}));

import { searchLogs, getLogDetail } from "@/services/endpoints";
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
    fireEvent.change(screen.getByPlaceholderText(/message \/ raw \/ host/), { target: { value: "admin" } });
    fireEvent.click(screen.getByRole("button", { name: /Search/ }));
    await waitFor(() => expect(screen.getByText("clear all")).toBeInTheDocument());
  });

  it("renders an empty state when nothing matches", async () => {
    (searchLogs as any).mockResolvedValue({ total: 0, items: [], limit: 50, offset: 0, note: null });
    renderWithProviders(<LogExplorerPage />);
    await waitFor(() => expect(screen.getByText("No events yet")).toBeInTheDocument());
  });
});
