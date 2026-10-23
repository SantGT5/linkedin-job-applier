import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { BotStatus } from "../api/types";
import { FakeEventSource } from "../test/eventsource";
import { mockFetch, renderWithProviders } from "../test/utils";
import Dashboard from "./Dashboard";

const run = { id: 7, status: "running", started_at: "2026-10-23T08:00:00Z", ended_at: null, error: null, applied_count: 2, failed_count: 1, skipped_count: 4 } as const;

function status(overrides: Partial<BotStatus> = {}): BotStatus {
  return { state: "running", run: { ...run }, prompt: null, linkedin_session: { state: "logged_in", checked_at: null }, ...overrides };
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("Start disabled while running", async () => {
  mockFetch({ "GET /api/bot/status": status() });
  renderWithProviders(<Dashboard />);
  expect(await screen.findByText("Running")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Stop" })).toBeEnabled();
  expect(screen.getByText("LinkedIn: logged in")).toBeInTheDocument();
});

test("Start enabled when idle and posts start", async () => {
  const { calls } = mockFetch({ "GET /api/bot/status": status({ state: "idle", run: null }), "POST /api/bot/start": { ...run, status: "queued" } });
  renderWithProviders(<Dashboard />);
  const start = await screen.findByRole("button", { name: "Start" });
  await waitFor(() => expect(start).toBeEnabled());
  expect(screen.getByRole("button", { name: "Stop" })).toBeDisabled();
  await userEvent.click(start);
  await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.url === "/api/bot/start")).toBe(true));
});

test("last failed run shows its error", async () => {
  mockFetch({ "GET /api/bot/status": status({ state: "idle", run: { ...run, status: "failed", error: "Bot exited with code 1.\nChrome failed" } }) });
  renderWithProviders(<Dashboard />);
  expect(await screen.findByText(/Chrome failed/)).toBeInTheDocument();
});

test("banner renders prompt buttons and posts answer", async () => {
  const prompt = { id: 3, title: "LinkedIn login needed", text: "Finish login in the live browser.", buttons: ["Done, continue", "Skip confirmation"] };
  const { calls } = mockFetch({
    "GET /api/bot/status": status({ state: "waiting", prompt }),
    "POST /api/bot/prompts/3/answer": { id: 3, answer: "Done, continue" },
  });
  renderWithProviders(<Dashboard />);
  const banner = await screen.findByRole("region", { name: "The bot needs you" });
  expect(banner).toHaveTextContent("LinkedIn login needed");
  expect(banner).toHaveTextContent("Finish login in the live browser.");
  expect(screen.getByRole("button", { name: "Skip confirmation" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Done, continue" }));
  await waitFor(() => expect(calls.find((c) => c.url === "/api/bot/prompts/3/answer")?.body).toEqual({ button: "Done, continue" }));
});

test("log lines append from stream", async () => {
  mockFetch({ "GET /api/bot/status": status() });
  renderWithProviders(<Dashboard />);
  await waitFor(() => expect(FakeEventSource.instances.length).toBeGreaterThan(0));
  const source = FakeEventSource.instances.at(-1)!;
  expect(source.url).toBe("/api/runs/7/logs/stream");
  act(() => {
    source.emit("Now searching for \"Software Engineer\"", "message", "1");
    source.emit("Found 25 jobs on page 1.", "message", "2");
  });
  const log = screen.getByRole("log");
  expect(log).toHaveTextContent('Now searching for "Software Engineer"');
  expect(log).toHaveTextContent("Found 25 jobs on page 1.");
  expect(screen.getByTitle("Live browser")).toHaveAttribute("src", expect.stringContaining("/novnc/vnc.html?autoconnect=1"));
});
