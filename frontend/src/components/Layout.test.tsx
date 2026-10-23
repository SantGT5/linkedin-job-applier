import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { mockFetch, renderWithProviders } from "../test/utils";
import Layout from "./Layout";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.title = "";
});

test("notifies once when the bot starts waiting and shows nav counts", async () => {
  const shown: string[] = [];
  class FakeNotification {
    static permission = "granted";
    constructor(title: string) {
      shown.push(title);
    }
  }
  vi.stubGlobal("Notification", FakeNotification);
  mockFetch({
    "GET /api/bot/status": { state: "waiting", run: null, prompt: { id: 5, title: "Help Needed", text: "x", buttons: ["Continue"] }, linkedin_session: { state: "logged_in", checked_at: null } },
    "GET /api/emails": { items: [], total: 3, page: 1, page_size: 1 },
    "GET /api/questions/unanswered": { items: [], total: 0, page: 1, page_size: 1 },
  });
  renderWithProviders(
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<p>home</p>} />
      </Route>
    </Routes>,
  );
  await waitFor(() => expect(shown).toEqual(["The bot needs you: Help Needed"]));
  expect(document.title).toContain("Needs you");
  expect(await screen.findByLabelText("3 to review")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "The bot needs you" })).toBeInTheDocument();
});
