import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import Placeholder from "@/components/Placeholder";
import AppLayout from "@/layouts/AppLayout";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SourcesPage from "@/pages/SourcesPage";
import IngestionPage from "@/pages/IngestionPage";
import PrivacyPage from "@/pages/PrivacyPage";

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
        <Route path="explorer" element={<Placeholder title="Log Explorer" phase="Phase 10" />} />
        <Route path="debugger" element={<Placeholder title="Pipeline Debugger" phase="Phase 15" />} />
        <Route path="alerts" element={<Placeholder title="Alerts" phase="Phase 13" />} />
        <Route path="analytics" element={<Placeholder title="Analytics" phase="Phase 14" />} />
        <Route path="parsers" element={<Placeholder title="Parser Packs" phase="Phase 16" />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="compression" element={<Placeholder title="Compression" phase="Phase 18" />} />
        <Route path="response" element={<Placeholder title="Response Simulator" phase="Phase 20" />} />
        <Route path="assistant" element={<Placeholder title="AI Assistant" phase="Phase 19" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
