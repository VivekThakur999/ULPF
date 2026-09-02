import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import { Spinner } from "@/components/ui";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SourcesPage from "@/pages/SourcesPage";
import IngestionPage from "@/pages/IngestionPage";
import PrivacyPage from "@/pages/PrivacyPage";
import LogExplorerPage from "@/pages/LogExplorerPage";
import AlertsPage from "@/pages/AlertsPage";

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
        <Route path="compression" element={<PlaceholderRoute title="Compression" phase="Phase 18" />} />
        <Route path="response" element={<PlaceholderRoute title="Response Simulator" phase="Phase 20" />} />
        <Route path="assistant" element={<PlaceholderRoute title="AI Assistant" phase="Phase 19" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function PlaceholderRoute({ title, phase }: { title: string; phase: string }) {
  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">{title}</h1>
      <p className="text-sm text-gray-400">
        Planned for <span className="text-brand-fg">{phase}</span>. Navigation stub — no placeholder
        data is shown until that phase lands.
      </p>
    </div>
  );
}
