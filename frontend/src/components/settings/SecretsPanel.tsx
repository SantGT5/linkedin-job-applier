import { useQuery } from "@tanstack/react-query";
import { api, errorMessage } from "../../api/client";
import type { Secret } from "../../api/types";

export default function SecretsPanel() {
  const secrets = useQuery({ queryKey: ["secrets"], queryFn: () => api<Secret[]>("/api/settings/secrets") });
  return (
    <section className="panel p-5" aria-labelledby="secrets-heading">
      <h2 id="secrets-heading" className="text-lg font-semibold">
        Secrets
      </h2>
      <p className="mt-1 max-w-[70ch] text-sm text-muted">
        Passwords and API keys live only in the <code>.env</code> file, never in the app. To change one, edit .env and run{" "}
        <code>make up</code>.
      </p>
      {secrets.isPending && <p className="mt-4 text-sm text-muted">Loading…</p>}
      {secrets.isError && (
        <p role="alert" className="mt-4 text-sm text-danger">
          Couldn't load secrets. {errorMessage(secrets.error)}
        </p>
      )}
      {secrets.data && (
        <table aria-label="Secrets" className="mt-4 w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="py-2 font-medium">Secret</th>
              <th className="py-2 font-medium">In .env as</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {secrets.data.map((secret) => (
              <tr key={secret.env_var} className="border-t border-line">
                <td className="py-2">{secret.name}</td>
                <td className="py-2">
                  <code>{secret.env_var}</code>
                </td>
                <td className="py-2">
                  {secret.set ? (
                    <span className="text-pine">Set</span>
                  ) : (
                    <span className="font-medium text-danger">Not set</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
