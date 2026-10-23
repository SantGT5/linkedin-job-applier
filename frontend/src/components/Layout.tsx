import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Page, Prompt } from "../api/types";
import { useBotStatus } from "../api/useBotStatus";
import Icon, { type IconName } from "./Icon";

const NAV: { to: string; label: string; icon: IconName; count?: "emails" | "questions" }[] = [
  { to: "/", label: "Dashboard", icon: "dashboard" },
  { to: "/settings", label: "Settings", icon: "settings" },
  { to: "/history", label: "History", icon: "history" },
  { to: "/emails", label: "Emails", icon: "mail", count: "emails" },
  { to: "/questions", label: "Questions", icon: "question", count: "questions" },
];

function useCounts() {
  const emails = useQuery({
    queryKey: ["nav-count", "emails"],
    queryFn: () => api<Page<unknown>>("/api/emails?status=new&page_size=1"),
    refetchInterval: 30_000,
  });
  const questions = useQuery({
    queryKey: ["nav-count", "questions"],
    queryFn: () => api<Page<unknown>>("/api/questions/unanswered?page_size=1"),
    refetchInterval: 30_000,
  });
  return { emails: emails.data?.total ?? 0, questions: questions.data?.total ?? 0 };
}

/** A desktop notification and tab title when the bot starts waiting, whatever page is open. */
function useNeedsYouNotice(prompt: Prompt | null | undefined) {
  const lastId = useRef<number | null>(null);
  useEffect(() => {
    document.title = prompt ? "Needs you · Applier" : "Applier";
    if (!prompt || prompt.id === lastId.current) return;
    lastId.current = prompt.id;
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(`The bot needs you: ${prompt.title}`, { body: prompt.text.slice(0, 180), tag: "applier-prompt" });
    }
  }, [prompt]);
}

export default function Layout() {
  const navigate = useNavigate();
  const counts = useCounts();
  const status = useBotStatus();
  const waiting = status.data?.state === "waiting";
  useNeedsYouNotice(status.data?.prompt);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[200px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-5 py-4 lg:block">
          <p className="text-lg font-semibold tracking-tight">Applier</p>
          <p className="hidden text-[13px] text-muted lg:block">LinkedIn job bot</p>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-1 lg:flex-col lg:overflow-visible lg:pb-0">
          {NAV.map((item) => {
            const count = item.count ? counts[item.count] : 0;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex min-h-[40px] items-center gap-3 whitespace-nowrap rounded px-3 text-sm transition-colors duration-150 ${
                    isActive ? "bg-pine-soft font-semibold text-pine-dark" : "text-muted hover:bg-ground hover:text-ink"
                  }`
                }
              >
                <Icon name={item.icon} />
                <span className="flex-1">{item.label}</span>
                {item.to === "/" && waiting && (
                  <span className="h-2.5 w-2.5 rounded-full bg-signal" role="img" aria-label="The bot needs you" />
                )}
                {count > 0 && (
                  <span className="rounded-full bg-ground px-2 text-xs font-medium tabular-nums text-ink" aria-label={`${count} to review`}>
                    {count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
        <div className="hidden px-3 pb-4 lg:block">
          <button type="button" onClick={logout} className="btn-ghost w-full justify-start gap-3">
            <Icon name="logout" />
            Log out
          </button>
        </div>
      </aside>
      <main id="main" tabIndex={-1} className="min-w-0 px-4 py-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
