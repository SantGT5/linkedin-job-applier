import type { BotStatus } from "../api/types";

const TEXT = { logged_in: "logged in", logged_out: "logged out", unknown: "not checked yet" } as const;

export default function SessionBadge({ session }: { session: BotStatus["linkedin_session"] }) {
  const loggedOut = session.state === "logged_out";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${
        loggedOut ? "border-danger bg-danger-soft text-danger" : "border-line bg-surface text-muted"
      }`}
      title={session.checked_at ? `Checked ${new Date(session.checked_at).toLocaleString()}` : undefined}
    >
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${session.state === "logged_in" ? "bg-pine" : loggedOut ? "bg-danger" : "bg-line"}`} />
      LinkedIn: {TEXT[session.state]}
    </span>
  );
}
