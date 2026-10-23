import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockFetch, renderWithProviders } from "../test/utils";
import Questions from "./Questions";

afterEach(() => vi.restoreAllMocks());

const q = { id: 4, label: "Proficiency in German?", question_type: "select", options: ["None", "Basic", "Fluent"], job_id: "1", seen_count: 3, last_seen: "2026-10-22T10:00:00Z" };

test("answering a question saves it as a custom answer", async () => {
  let answered = false;
  const { calls } = mockFetch({
    "GET /api/questions/unanswered": () => ({ items: answered ? [] : [q], total: answered ? 0 : 1, page: 1, page_size: 25 }),
    "POST /api/questions/unanswered/4/answer": () => {
      answered = true;
      return { custom_answers: [{ match: q.label, answer: "None" }] };
    },
  });
  renderWithProviders(<Questions />, { route: "/questions" });
  expect(await screen.findByText("Proficiency in German?")).toBeInTheDocument();
  expect(screen.getByText("None, Basic, Fluent")).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Answer for Proficiency in German?"), "None");
  await userEvent.click(screen.getByRole("button", { name: "Save answer" }));
  await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ answer: "None" }));
  expect(await screen.findByText(/No unanswered questions/)).toBeInTheDocument();
});
