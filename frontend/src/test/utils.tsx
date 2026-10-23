import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "../components/Toast";

type Handler = (init: RequestInit & { url: string; body?: unknown }) => unknown | Response;
export type Routes = Record<string, Handler | unknown>;

/** Mocks fetch: keys are "METHOD /path" (query string ignored unless the key has one). */
export function mockFetch(routes: Routes) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
    calls.push({ method, url, body });
    const path = url.split("?")[0];
    const handler = routes[`${method} ${url}`] ?? routes[`${method} ${path}`];
    if (handler === undefined) return new Response(JSON.stringify({ detail: `no mock for ${method} ${url}` }), { status: 404 });
    const result = typeof handler === "function" ? (handler as Handler)({ ...init, url, body }) : handler;
    if (result instanceof Response) return result;
    return result === null ? new Response(null, { status: 204 }) : new Response(JSON.stringify(result), { status: 200 });
  });
  return { fetchMock, calls };
}

export function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status });
}

export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
