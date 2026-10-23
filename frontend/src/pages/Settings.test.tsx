import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SchemaField } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import Settings from "./Settings";

const f = (section: string, key: string, type: SchemaField["type"], extra: Partial<SchemaField> = {}): SchemaField => ({
  section, key, type, default: null, options: null, help: `Help for ${key}`, min: null, max: null, ...extra,
});

const SCHEMA: SchemaField[] = [
  f("personals", "first_name", "str"),
  f("questions", "desired_salary", "int", { min: 0 }),
  f("questions", "custom_answers", "answers"),
  f("search", "date_posted", "enum", { options: ["", "Any time", "Past week", "Past 24 hours"] }),
  f("search", "on_site", "multi_enum", { options: ["On-site", "Remote", "Hybrid"] }),
  f("search", "search_terms", "list"),
  f("search", "easy_apply_only", "bool"),
  f("email", "my_name", "str"),
  f("email", "phone_number", "str"),
  f("email", "linkedin_profile", "str"),
  f("email", "subject_template", "str"),
  f("email", "body_template", "text"),
];
const VALUES = {
  personals: { first_name: "Ada" },
  questions: { desired_salary: 120000, custom_answers: [{ match: "German", answer: "None" }] },
  search: { date_posted: "Past 24 hours", on_site: ["Remote"], search_terms: ["Backend Engineer", "Go Developer"], easy_apply_only: true },
  settings: {}, ai: {},
  email: { my_name: "Ada", phone_number: "", linkedin_profile: "", subject_template: "{job_title} - {my_name}", body_template: "Hi" },
};

function setup(extra: Parameters<typeof mockFetch>[0] = {}) {
  const mocks = mockFetch({
    "GET /api/settings/schema": SCHEMA,
    "GET /api/settings": VALUES,
    "GET /api/settings/secrets": [
      { name: "Claude API key", env_var: "CLAUDE_API_KEY", set: true },
      { name: "GLM API key", env_var: "GLM_API_KEY", set: false },
    ],
    "GET /api/resume": { exists: false },
    "POST /api/emails/preview": { to: "hr@example.com", subject: "S", body_text: "B", body_html: "B" },
    ...extra,
  });
  renderWithProviders(<Settings />, { route: "/settings" });
  return mocks;
}

afterEach(() => vi.restoreAllMocks());

test("renders enum as select with schema options", async () => {
  setup();
  await userEvent.click(await screen.findByRole("tab", { name: "Search" }));
  const select = screen.getByLabelText("Date posted");
  expect(select.tagName).toBe("SELECT");
  expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual(["Not set", "Any time", "Past week", "Past 24 hours"]);
  expect(select).toHaveValue("Past 24 hours");
  expect(screen.getByRole("checkbox", { name: "Remote" })).toBeChecked();
  expect(screen.getByLabelText("Search terms")).toHaveValue("Backend Engineer\nGo Developer");
  expect(screen.getByRole("switch", { name: "Easy Apply only" })).toBeChecked();
});

test("saves only changed fields and confirms next run", async () => {
  const { calls } = setup({ "PUT /api/settings/search": { ...VALUES.search, search_terms: ["Rust Developer"] } });
  await userEvent.click(await screen.findByRole("tab", { name: "Search" }));
  const terms = screen.getByLabelText("Search terms");
  await userEvent.clear(terms);
  await userEvent.type(terms, "Rust Developer");
  await userEvent.click(screen.getByRole("button", { name: "Save search" }));
  await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ search_terms: ["Rust Developer"] }));
  expect(await screen.findByText("Saved. Used on the next run.")).toBeInTheDocument();
});

test("shows field error from 422", async () => {
  setup({ "PUT /api/settings/questions": () => jsonResponse({ detail: { field_errors: { desired_salary: "must be a whole number" } } }, 422) });
  await userEvent.click(await screen.findByRole("tab", { name: "Questions" }));
  const salary = screen.getByLabelText("Desired salary");
  await userEvent.clear(salary);
  await userEvent.type(salary, "abc");
  await userEvent.click(screen.getByRole("button", { name: "Save questions" }));
  expect(await screen.findByText("must be a whole number")).toBeInTheDocument();
  expect(salary).toHaveAttribute("aria-invalid", "true");
  expect(salary).toHaveAccessibleDescription(expect.stringContaining("must be a whole number"));
});

test("custom answers can be added and removed", async () => {
  const { calls } = setup({ "PUT /api/settings/questions": VALUES.questions });
  await userEvent.click(await screen.findByRole("tab", { name: "Questions" }));
  await userEvent.click(screen.getByRole("button", { name: "Add answer" }));
  const matches = screen.getAllByLabelText("When the question contains");
  await userEvent.type(matches[1], "visa");
  await userEvent.type(screen.getAllByLabelText("Answer")[1], "No");
  await userEvent.click(screen.getByRole("button", { name: "Remove answer for German" }));
  await userEvent.click(screen.getByRole("button", { name: "Save questions" }));
  await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ custom_answers: [{ match: "visa", answer: "No" }] }));
});

test("secrets panel never shows values", async () => {
  setup();
  await userEvent.click(await screen.findByRole("tab", { name: "Secrets & resume" }));
  const panel = await screen.findByRole("table", { name: "Secrets" });
  expect(within(panel).getByText("CLAUDE_API_KEY")).toBeInTheDocument();
  expect(within(panel).getByText("Set")).toBeInTheDocument();
  expect(within(panel).getByText("Not set")).toBeInTheDocument();
  expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  expect(screen.getByText(/edit \.env/i)).toBeInTheDocument();
});

test("exports settings as applier-settings.json", async () => {
  const exported = { version: 1, ...VALUES };
  const { calls } = setup({ "GET /api/settings/export": exported });
  const blobs: Blob[] = [];
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn((b: Blob) => (blobs.push(b), "blob:settings")), revokeObjectURL: vi.fn() }));
  const clicked: HTMLAnchorElement[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicked.push(this);
  });
  await userEvent.click(await screen.findByRole("button", { name: "Export settings" }));
  await waitFor(() => expect(clicked).toHaveLength(1));
  expect(calls.some((c) => c.method === "GET" && c.url === "/api/settings/export")).toBe(true);
  expect(clicked[0].download).toBe("applier-settings.json");
  const text = await new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blobs[0]);
  });
  expect(JSON.parse(text)).toEqual(exported);
});

test("imports a settings file and reloads the form", async () => {
  let gets = 0;
  const imported = { ...VALUES, personals: { first_name: "Grace" } };
  const { calls } = setup({
    "GET /api/settings": () => (++gets === 1 ? VALUES : imported),
    "POST /api/settings/import": imported,
  });
  expect(await screen.findByLabelText("First name")).toHaveValue("Ada");
  const file = new File([JSON.stringify({ version: 1, ...imported })], "applier-settings.json", { type: "application/json" });
  await userEvent.upload(screen.getByLabelText("Import settings"), file);
  expect(await screen.findByText("Imported. Used on the next run.")).toBeInTheDocument();
  const post = calls.find((c) => c.method === "POST" && c.url === "/api/settings/import");
  expect((post?.body as FormData).get("file")).toBeInstanceOf(File);
  await waitFor(() => expect(screen.getByLabelText("First name")).toHaveValue("Grace"));
});

test("import errors list every bad field and nothing is saved", async () => {
  setup({
    "POST /api/settings/import": () =>
      jsonResponse({ detail: { field_errors: { "questions.desired_salary": "must be a whole number", version: "must be 1" } } }, 422),
  });
  const file = new File(["{}"], "settings.json", { type: "application/json" });
  await userEvent.upload(await screen.findByLabelText("Import settings"), file);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Nothing was imported");
  expect(within(alert).getByText(/Questions › Desired salary/)).toHaveTextContent("must be a whole number");
  expect(within(alert).getByText(/version/)).toHaveTextContent("must be 1");
  await userEvent.click(within(alert).getByRole("button", { name: "Dismiss" }));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("email preview sends phone number and LinkedIn profile", async () => {
  const { calls } = setup();
  await userEvent.click(await screen.findByRole("tab", { name: "Email" }));
  await userEvent.type(screen.getByLabelText("Phone number"), "+1 555 0100");
  await userEvent.type(screen.getByLabelText("LinkedIn profile"), "linkedin.com/in/janedoe");
  await waitFor(
    () =>
      expect(calls.filter((c) => c.url === "/api/emails/preview").at(-1)?.body).toMatchObject({
        phone_number: "+1 555 0100",
        linkedin_profile: "linkedin.com/in/janedoe",
      }),
    { timeout: 2000 },
  );
});
