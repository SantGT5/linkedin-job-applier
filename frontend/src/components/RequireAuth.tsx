import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, api } from "../api/client";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const check = useQuery({ queryKey: ["auth-check"], queryFn: () => api("/api/auth/check"), retry: false, staleTime: 60_000 });
  if (check.isPending) {
    return <p className="p-8 text-muted" role="status">Loading…</p>;
  }
  if (check.error instanceof ApiError && check.error.status === 401) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
