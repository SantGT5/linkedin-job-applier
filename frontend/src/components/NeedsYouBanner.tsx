import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "../api/client";
import type { Prompt } from "../api/types";
import { useToast } from "./Toast";

function primaryButton(buttons: string[]) {
  return buttons.find((b) => !/submit/i.test(b)) ?? null;
}

export default function NeedsYouBanner({ prompt }: { prompt: Prompt }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const answer = useMutation({
    mutationFn: (button: string) => api(`/api/bot/prompts/${prompt.id}/answer`, { method: "POST", body: { button } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bot-status"] }),
    onError: (e) => {
      toast(errorMessage(e), "error");
      void queryClient.invalidateQueries({ queryKey: ["bot-status"] });
    },
  });

  return (
    <section
      aria-label="The bot needs you"
      aria-live="assertive"
      className="rounded-lg border-2 border-signal bg-signal-soft px-5 py-4"
    >
      <h2 className="text-lg font-semibold">{prompt.title}</h2>
      <p className="mt-1 max-w-[75ch] whitespace-pre-line text-[15px]">{prompt.text.trim().replace(/\n{3,}/g, "\n\n")}</p>
      <p className="mt-2 text-sm text-muted">Do it in the live browser below, then choose:</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {prompt.buttons.map((button) => (
          <button
            key={button}
            type="button"
            // Submitting stays a deliberate, neutral choice; the safe default is primary.
            className={button === primaryButton(prompt.buttons) ? "btn-primary" : "btn-secondary"}
            disabled={answer.isPending}
            onClick={() => answer.mutate(button)}
          >
            {button}
          </button>
        ))}
      </div>
    </section>
  );
}
