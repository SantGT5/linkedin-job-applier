import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, errorMessage } from "../api/client";

export default function Login() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/auth/login", { method: "POST", body: { password } });
      navigate("/", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? "Wrong password" : errorMessage(e));
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="panel w-full max-w-sm p-8" noValidate>
        <h1 className="text-2xl font-semibold tracking-tight">Applier</h1>
        <p className="mt-1 text-sm text-muted">Your LinkedIn job bot. Log in to watch and steer it.</p>
        <label htmlFor="password" className="label mt-6">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          autoFocus
          className="field"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={error ? "login-error" : "login-help"}
        />
        {error ? (
          <p id="login-error" role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        ) : (
          <p id="login-help" className="help">
            It's UI_PASSWORD in your .env file.
          </p>
        )}
        <button type="submit" className="btn-primary mt-6 w-full" disabled={busy || !password}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
    </main>
  );
}
