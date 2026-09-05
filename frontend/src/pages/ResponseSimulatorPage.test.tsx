import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  listAlerts: vi.fn(),
  getRecommendation: vi.fn(),
  runResponseSimulation: vi.fn(),
  listSimulations: vi.fn(),
}));

import {
  listAlerts,
  getRecommendation,
  runResponseSimulation,
  listSimulations,
} from "@/services/endpoints";
import ResponseSimulatorPage from "./ResponseSimulatorPage";

// stub useAuth -> analyst
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ hasRole: () => true, user: { role: "ANALYST" } }),
}));

const REC = {
  alert: {
    id: "a1", title: "Brute force", severity: "high", risk_score: 82, rule_key: "RULE_1",
    reason: "12 failed logins from IP_ABC", entity: { source_ip: "IP_ABC", type: "source_ip" },
    ts: new Date().toISOString(), status: "NEW",
  },
  recommendation: {
    category: "BRUTE_FORCE", available: true, label: "Block source IP",
    rationale: "12 failed authentications from IP_ABC across 2 sources.",
    actions: [
      { action: "BLOCK_SOURCE", target: "IP_ABC", port: 22, protocol: "TCP", detail: "deny future traffic", mode: "SIMULATION_ONLY" },
    ],
    evidence: {},
  },
  evidence: { counts: { auth_failures: 12, sources: 2 }, shield_verdicts: [] },
};

const SIM = {
  simulation: true,
  disclaimer: "SIMULATION ONLY - NO REAL NETWORK, HOST OR IDENTITY CHANGE WAS MADE.",
  audit_id: "abcdef123456",
  alert: REC.alert,
  recommendation: REC.recommendation,
  actions: REC.recommendation.actions,
  result: {
    simulation: true,
    disclaimer: "SIMULATION ONLY",
    no_real_change: true,
    primary: {
      kind: "virtual_firewall",
      target: "IP_ABC",
      before: [{ verdict: "ALLOW" }],
      after: [{ verdict: "WOULD BLOCK" }],
      expected_result: "Future TCP connections from IP_ABC to port 22 would be denied.",
      state_change: { before: "ALLOW", after: "WOULD BLOCK" },
      disclaimer: "SIMULATION ONLY",
    },
    all: [],
  },
  evidence: {},
};

beforeEach(() => {
  vi.clearAllMocks();
  (listAlerts as any).mockResolvedValue({ total: 1, items: [
    { id: "a1", title: "Brute force", severity: "high", risk_score: 82 },
  ] });
  (getRecommendation as any).mockResolvedValue(REC);
  (listSimulations as any).mockResolvedValue([]);
});

describe("ResponseSimulatorPage", () => {
  it("loads with a SIMULATION ONLY badge in the header", async () => {
    renderWithProviders(<ResponseSimulatorPage />);
    expect(screen.getByRole("heading", { name: "Response Simulator" })).toBeInTheDocument();
    expect(screen.getAllByText(/simulation only/i).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
  });

  it("shows the deterministic recommendation + evidence after selecting an alert", async () => {
    renderWithProviders(<ResponseSimulatorPage />, { route: "/response?alert=a1" });
    await waitFor(() => expect(screen.getByText("Block source IP")).toBeInTheDocument());
    expect(screen.getByText(/12 failed authentications from IP_ABC/)).toBeInTheDocument();
    expect(screen.getByText(/auth failures:/)).toBeInTheDocument();
    // the run button uses the safe label, never "Block" / "Execute" / "Apply"
    const btn = screen.getByRole("button", { name: /Run Simulation/ });
    expect(btn).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Block IP$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Execute/ })).not.toBeInTheDocument();
  });

  it("runs the simulation and shows the before/after with 'No real system was modified'", async () => {
    (runResponseSimulation as any).mockResolvedValue(SIM);
    renderWithProviders(<ResponseSimulatorPage />, { route: "/response?alert=a1" });
    fireEvent.click(await screen.findByRole("button", { name: /Run Simulation/ }));

    await waitFor(() => expect(screen.getByText("Simulation complete")).toBeInTheDocument());
    expect(screen.getByText("ALLOW")).toBeInTheDocument();
    expect(screen.getByText("WOULD BLOCK")).toBeInTheDocument();
    expect(screen.getByText("No real system was modified.")).toBeInTheDocument();
    expect(runResponseSimulation).toHaveBeenCalledWith("a1");
  });

  it("shows an error state when the simulation call fails", async () => {
    (runResponseSimulation as any).mockRejectedValue(new Error("nope"));
    renderWithProviders(<ResponseSimulatorPage />, { route: "/response?alert=a1" });
    fireEvent.click(await screen.findByRole("button", { name: /Run Simulation/ }));
    await waitFor(() => expect(screen.getByText(/nope/)).toBeInTheDocument());
  });

  it("handles an alert with no available recommendation", async () => {
    (getRecommendation as any).mockResolvedValue({
      ...REC,
      recommendation: { category: "NONE", available: false,
        label: "No automated response recommendation available.", rationale: "n/a", actions: [], evidence: {} },
    });
    renderWithProviders(<ResponseSimulatorPage />, { route: "/response?alert=a1" });
    await waitFor(() =>
      expect(screen.getByText("No automated response recommendation available.")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /Run Simulation/ })).not.toBeInTheDocument();
  });
});
