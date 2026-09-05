import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Activity } from "lucide-react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import { Spinner } from "@/components/ui";
import ComingSoon from "@/components/ComingSoon";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SourcesPage from "@/pages/SourcesPage";
import IngestionPage from "@/pages/IngestionPage";
import PrivacyPage from "@/pages/PrivacyPage";
import LogExplorerPage from "@/pages/LogExplorerPage";
import AlertsPage from "@/pages/AlertsPage";
import TemplatesPage from "@/pages/TemplatesPage";
import CompressionPage from "@/pages/CompressionPage";
import AssistantPage from "@/pages/AssistantPage";

// Monaco-heavy pages are code-split so the main bundle stays lean.
const PipelineDebuggerPage = lazy(() => import("@/pages/PipelineDebuggerPage"));
const ParserPacksPage = lazy(() => import("@/pages/ParserPacksPage"));

const Lazy = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<div className="p-8"><Spinner /></div>}>{children}</Suspense>
);

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="ingestion" element={<IngestionPage />} />
        <Route path="explorer" element={<LogExplorerPage />} />
        <Route path="debugger" element={<Lazy><PipelineDebuggerPage /></Lazy>} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="analytics" element={<Navigate to="/" replace />} />
        <Route path="parsers" element={<Lazy><ParserPacksPage /></Lazy>} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="compression" element={<CompressionPage />} />
        <Route
          path="response"
          element={
            <ComingSoon
              title="Response Simulator"
              icon={Activity}
              checkpoint="Checkpoint 8"
              summary="Safe, clearly-labelled simulation of a recommended response action — never a live change."
              bullets={[
                "Take an alert's recommended_response and simulate it against a fake firewall/IAM target",
                "Every result is labelled SIMULATION ONLY — no real enforcement",
                "Full audit record of who simulated what, when, and against which alert",
              ]}
            />
          }
        />
        <Route path="assistant" element={<AssistantPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
