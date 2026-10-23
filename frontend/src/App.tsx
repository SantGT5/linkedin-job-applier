import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { setUnauthorizedHandler } from "./api/client";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import Dashboard from "./pages/Dashboard";
import Emails from "./pages/Emails";
import History from "./pages/History";
import Login from "./pages/Login";
import Questions from "./pages/Questions";
import Settings from "./pages/Settings";

export default function App() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear();
      navigate("/login", { replace: true });
    });
  }, [navigate, queryClient]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="settings" element={<Settings />} />
        <Route path="history" element={<History />} />
        <Route path="emails" element={<Emails />} />
        <Route path="questions" element={<Questions />} />
      </Route>
    </Routes>
  );
}
