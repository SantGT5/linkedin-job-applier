import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { HrEmail } from "../api/types";
import { mockFetch, renderWithProviders } from "../test/utils";
import Emails from "./Emails";

const row = (id: number, extra: Partial<HrEmail> = {}): HrEmail => ({
  id, email: `hr${id}@acme.com`, job_id: String(100 + id), title: "Senior Backend Engineer", company: "Acme",
  job_link: `https://www.linkedin.com/jobs/view/${100 + id}`, email_subject: null, status: "new",
  found_at: "2026-10-22T12:00:00Z", emailed_at: null, ...extra,
});
const page = (items: HrEmail[], total = items.length, pageNo = 1) => ({ items, total, page: pageNo, page_size: 25 });
const composed = {
  to: "hr1@acme.com",
  subject: "Senior Backend Engineer - Jane Doe",
  body_text: "Hi,\n\nI came across the Senior Backend Engineer (https://www.linkedin.com/jobs/view/101) role",
  body_html: 'Hi,<br><br>I came across the <a href="https://www.linkedin.com/jobs/view/101">Senior Backend Engineer</a> role',
};

let clipboardWrites: unknown[];
beforeEach(() => {
  clipboardWrites = [];
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn(async (t: string) => clipboardWrites.push(t)), write: vi.fn(async (items: unknown) => clipboardWrites.push(items)) },
  });
  vi.stubGlobal("ClipboardItem", class { constructor(public data: Record<string, Blob>) {} });
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function openCopy() {
  await userEvent.click(await screen.findByRole("button", { name: "Copy email to hr1@acme.com" }));
  return screen.findByRole("dialog", { name: "Email to hr1@acme.com" });
}

test("copy modal shows composed email", async () => {
  mockFetch({ "GET /api/emails": page([row(1)]), "GET /api/emails/1/compose": composed });
  renderWithProviders(<Emails />, { route: "/emails" });
  const dialog = await openCopy();
  expect(within(dialog).getByText("hr1@acme.com")).toBeInTheDocument();
  expect(within(dialog).getByText("Senior Backend Engineer - Jane Doe")).toBeInTheDocument();
  expect(within(dialog).getByRole("link", { name: "Senior Backend Engineer" })).toHaveAttribute("href", "https://www.linkedin.com/jobs/view/101");
  await userEvent.click(within(dialog).getByRole("button", { name: "Copy body" }));
  expect(navigator.clipboard.write).toHaveBeenCalled();
  await userEvent.click(within(dialog).getByRole("button", { name: "Copy subject" }));
  expect(clipboardWrites).toContain("Senior Backend Engineer - Jane Doe");
});

test("copy address button copies just the address", async () => {
  mockFetch({ "GET /api/emails": page([row(1)]) });
  renderWithProviders(<Emails />, { route: "/emails" });
  await userEvent.click(await screen.findByRole("button", { name: "Copy address hr1@acme.com" }));
  expect(clipboardWrites).toEqual(["hr1@acme.com"]);
});

test("confirm yes marks emailed and refreshes list", async () => {
  let listCalls = 0;
  const { calls } = mockFetch({
    "GET /api/emails": () => (listCalls++ === 0 ? page([row(1)]) : page([row(1, { status: "emailed", emailed_at: "2026-10-23T10:00:00Z" })])),
    "GET /api/emails/1/compose": composed,
    "POST /api/emails/1/mark-emailed": row(1, { status: "emailed" }),
  });
  renderWithProviders(<Emails />, { route: "/emails" });
  const dialog = await openCopy();
  await userEvent.click(within(dialog).getByRole("button", { name: "Close" }));
  const confirm = await screen.findByRole("alertdialog", { name: "Did you send it?" });
  await userEvent.click(within(confirm).getByRole("button", { name: "Yes, mark as emailed" }));
  await waitFor(() => expect(calls.some((c) => c.url === "/api/emails/1/mark-emailed")).toBe(true));
  expect(await within(screen.getByRole("table", { name: "HR emails" })).findByText("Emailed")).toBeInTheDocument();
});

test("confirm no leaves status new", async () => {
  const { calls } = mockFetch({ "GET /api/emails": page([row(1)]), "GET /api/emails/1/compose": composed });
  renderWithProviders(<Emails />, { route: "/emails" });
  await openCopy();
  await userEvent.keyboard("{Escape}");
  const confirm = await screen.findByRole("alertdialog", { name: "Did you send it?" });
  await userEvent.click(within(confirm).getByRole("button", { name: "No, not yet" }));
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  expect(calls.some((c) => c.url.includes("mark-emailed"))).toBe(false);
  expect(within(screen.getByRole("table", { name: "HR emails" })).getByText("New")).toBeInTheDocument();
});

test("filters update query string and refetch", async () => {
  const { calls } = mockFetch({ "GET /api/emails": page([row(1)]) });
  renderWithProviders(<Emails />, { route: "/emails" });
  await screen.findByText("hr1@acme.com");
  await userEvent.selectOptions(screen.getByLabelText("Status"), "emailed");
  await waitFor(() => expect(calls.at(-1)?.url).toContain("status=emailed"));
  await userEvent.type(screen.getByLabelText("Company"), "Acme");
  await waitFor(() => expect(calls.at(-1)?.url).toMatch(/company=Acme.*|status=emailed.*company=Acme/));
});

test("pagination moves pages", async () => {
  const { calls } = mockFetch({
    "GET /api/emails": (init: { url: string }) => (init.url.includes("page=2") ? page([row(26)], 30, 2) : page(Array.from({ length: 25 }, (_, i) => row(i + 1)), 30, 1)),
  });
  renderWithProviders(<Emails />, { route: "/emails" });
  expect(await screen.findByText("Page 1 of 2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Next page" }));
  expect(await screen.findByText("hr26@acme.com")).toBeInTheDocument();
  expect(calls.at(-1)?.url).toContain("page=2");
  expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
});

test("empty list explains where emails come from", async () => {
  mockFetch({ "GET /api/emails": page([]) });
  renderWithProviders(<Emails />, { route: "/emails" });
  expect(await screen.findByText(/No HR emails yet/)).toBeInTheDocument();
});
