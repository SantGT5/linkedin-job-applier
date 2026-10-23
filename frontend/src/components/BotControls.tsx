import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "../api/client";
import type { BotStatus } from "../api/types";
import SessionBadge from "./SessionBadge";
import { useToast } from "./Toast";

const STATE_LABEL: Record<BotStatus["state"], string> = {
  idle: "Idle",
  queued: "Starting",
  running: "Running",
  waiting: "Waiting for you",
  stopping: "Stopping",
};

const RUN_END: Record<string, string> = { finished: "finished", failed: "failed", stopped: "was stopped" };

export default function BotControls({ status }: { status: BotStatus }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["bot-status"] });
  const start = useMutation({
    mutationFn: () => api("/api/bot/start", { method: "POST" }),
    onMutate: () => {
      // Ask once, on a click, so "Bot needs you" can notify while you're in another tab.
      if ("Notification" in window && Notification.permission === "default") void Notification.requestPermission();
    },
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), "error"),
  });
  const stop = useMutation({
    mutationFn: () => api("/api/bot/stop", { method: "POST" }),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), "error"),
  });

  const { state, run } = status;
  const idle = state === "idle";
  const ended = idle && run && RUN_END[run.status];

  return (
    <section aria-label="Bot" className="panel flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className={`h-3 w-3 rounded-full ${state === "waiting" ? "bg-signal" : idle ? "bg-line" : "bg-pine"} ${
            state === "running" ? "motion-safe:animate-pulse" : ""
          }`}
        />
        <div>
          <p className="text-lg font-semibold leading-tight">{STATE_LABEL[state]}</p>
          {run && (
            <p className="text-sm text-muted">
              Run {run.id}
              {ended ? ` ${RUN_END[run.status]}` : ""} · {run.applied_count} applied, {run.failed_count} failed, {run.skipped_count} skipped
            </p>
          )}
        </div>
      </div>
      <SessionBadge session={status.linkedin_session} />
      <div className="ml-auto flex gap-2">
        <button type="button" className="btn-primary" disabled={!idle || start.isPending} onClick={() => start.mutate()}>
          Start
        </button>
        <button type="button" className="btn-secondary" disabled={idle || state === "stopping" || stop.isPending} onClick={() => stop.mutate()}>
          Stop
        </button>
      </div>
      {idle && run?.status === "failed" && run.error && (
        <div role="alert" className="w-full rounded border border-danger bg-danger-soft px-4 py-3 text-sm text-danger">
          <p className="font-medium">The last run failed.</p>
          <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[13px]">{run.error}</pre>
        </div>
      )}
    </section>
  );
}
