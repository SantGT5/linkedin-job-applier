export type LogKind = "divider" | "heading" | "job" | "you" | "error" | "skip" | "success" | "ai" | "debug" | "plain";

// First match wins, so the more specific kinds come first.
const RULES: [LogKind, RegExp][] = [
  // Banner lines of older runs ("____", "####"); drawn as a rule.
  ["divider", /^\s*[-_#=@]{3,}\s*$/],
  ["you", /^\[(Waiting for you|You answered)\]/],
  ["job", /^Trying to Apply to /],
  ["heading", /^(>>>>|>->|====)/],
  ["debug", /^(Saved debug page|Search URL:|Filters on the results page:|Click was blocked)/],
  ["ai", /^AI job match score/],
  ["error", /^(Run failed|Traceback|\s+File ")|\b(failed|error|exception|couldn't|unable to|crashed|invalid)\b/i],
  ["skip", /^(Skipping|Already applied|Didn't|Stuck|Moving to the next)|\b(skipped|skipping|limit .* reached|answering randomly|not found)\b/i],
  ["success", /^(Successfully|Connected to|Login successful|Answered \d+ question|Found HR email)/i],
];

export function logKind(text: string): LogKind {
  return RULES.find(([, pattern]) => pattern.test(text))?.[0] ?? "plain";
}

/** Text classes per kind, readable on the log's light background. */
export const LOG_STYLE: Record<LogKind, string> = {
  divider: "",
  heading: "mt-2 font-semibold text-pine-dark",
  job: "mt-3 border-l-2 border-pine pl-2 font-semibold text-ink",
  you: "my-1 rounded bg-signal-soft px-2 py-0.5 font-medium text-warn",
  error: "text-danger",
  skip: "text-warn",
  success: "text-pine",
  ai: "text-info",
  debug: "text-muted opacity-80",
  plain: "text-ink",
};
