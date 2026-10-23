import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockFetch, renderWithProviders } from "../test/utils";
import History from "./History";

afterEach(() => vi.restoreAllMocks());

const applied = { job_id: "100", title: "Go Developer", company: "Acme", work_location: "Remote", work_style: "Remote", date_applied: "2026-10-22T10:00:00", date_posted: null, job_link: "https://www.linkedin.com/jobs/view/100", external_job_link: "Easy Applied", hr_name: null, hr_link: null, resume: "Previous resume" };

test("applied tab lists jobs with link and export", async () => {
  mockFetch({ "GET /api/history/applied": { items: [applied], total: 1, page: 1, page_size: 25 } });
  renderWithProviders(<History />, { route: "/history" });
  expect(await screen.findByRole("link", { name: "Go Developer" })).toHaveAttribute("href", applied.job_link);
  expect(screen.getByRole("link", { name: "Export CSV of applied jobs" })).toHaveAttribute("href", "/api/export/applied.csv");
});

test("failed tab and search filter", async () => {
  const { calls } = mockFetch({
    "GET /api/history/applied": { items: [], total: 0, page: 1, page_size: 25 },
    "GET /api/history/failed": { items: [{ id: 1, job_id: "9", job_link: "https://l/9", date_tried: "2026-10-22T10:00:00", assumed_reason: "Found a Bad Word in About Job", external_job_link: "Skipped" }], total: 1, page: 1, page_size: 25 },
  });
  renderWithProviders(<History />, { route: "/history" });
  await userEvent.click(await screen.findByRole("tab", { name: "Failed or skipped" }));
  expect(await screen.findByText("Found a Bad Word in About Job")).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Search"), "bad");
  await waitFor(() => expect(calls.at(-1)?.url).toContain("/api/history/failed?"));
  await waitFor(() => expect(calls.at(-1)?.url).toContain("q=bad"));
});

test("delete selected applications", async () => {
  const { calls } = mockFetch({
    "GET /api/history/applied": { items: [applied, { ...applied, job_id: "101", title: "Rust Developer" }], total: 2, page: 1, page_size: 25 },
    "POST /api/history/applied/delete": { deleted: 1 },
  });
  renderWithProviders(<History />, { route: "/history" });
  await userEvent.click(await screen.findByRole("checkbox", { name: "Select Rust Developer" }));
  await userEvent.click(screen.getByRole("button", { name: "Delete selected" }));
  expect(screen.getByRole("alertdialog", { name: "Delete 1 application?" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Delete 1 application" }));
  await waitFor(() => expect(calls.find((c) => c.url === "/api/history/applied/delete")?.body).toEqual({ ids: ["101"] }));
});
