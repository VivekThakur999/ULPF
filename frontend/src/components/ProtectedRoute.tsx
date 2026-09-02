import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import type { Role } from "@/types";

export default function ProtectedRoute({
  children,
  role,
}: {
  children: ReactNode;
  role?: Role;
}) {
  const { user, loading, hasRole } = useAuth();
  const loc = useLocation();

  if (loading) {
    return <div className="p-8 text-sm text-gray-400">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  if (role && !hasRole(role)) {
    return (
      <div className="p-8">
        <h2 className="text-lg font-semibold text-sev-high">Access denied</h2>
        <p className="text-sm text-gray-400">
          This page requires the {role} role. You are signed in as {user.role}.
        </p>
      </div>
    );
  }
  return <>{children}</>;
}
