import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import Login from "./Login";

afterEach(() => vi.restoreAllMocks());

function setup(routes: Parameters<typeof mockFetch>[0]) {
  const mocks = mockFetch(routes);
  renderWithProviders(
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<h1>Dashboard page</h1>} />
    </Routes>,
    { route: "/login" },
  );
  return mocks;
}

test("Login shows error on 401", async () => {
  setup({ "POST /api/auth/login": () => jsonResponse({ detail: "Wrong password" }, 401) });
  await userEvent.type(screen.getByLabelText("Password"), "nope");
  await userEvent.click(screen.getByRole("button", { name: "Log in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Wrong password");
  expect(screen.getByLabelText("Password")).toHaveAttribute("aria-invalid", "true");
});

test("redirects to dashboard after login", async () => {
  const { calls } = setup({ "POST /api/auth/login": null });
  await userEvent.type(screen.getByLabelText("Password"), "secret");
  await userEvent.keyboard("{Enter}");
  expect(await screen.findByRole("heading", { name: "Dashboard page" })).toBeInTheDocument();
  expect(calls[0].body).toEqual({ password: "secret" });
});
