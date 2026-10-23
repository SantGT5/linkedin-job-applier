import { ApiError, api, errorMessage, setUnauthorizedHandler } from "./client";

afterEach(() => vi.restoreAllMocks());

test("sends cookies and parses JSON", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }));
  await expect(api("/api/health")).resolves.toEqual({ ok: true });
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "include" });
});

test("401 calls the unauthorized handler (redirect to login)", async () => {
  const onUnauthorized = vi.fn();
  setUnauthorizedHandler(onUnauthorized);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Not logged in" }), { status: 401 }));
  await expect(api("/api/settings")).rejects.toBeInstanceOf(ApiError);
  expect(onUnauthorized).toHaveBeenCalled();
});

test("422 keeps field errors", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: { field_errors: { desired_salary: "must be a whole number" } } }), { status: 422 }));
  const error = (await api("/api/settings/questions", { method: "PUT", body: {} }).catch((e: unknown) => e)) as ApiError;
  expect(error.status).toBe(422);
  expect(error.fieldErrors).toEqual({ desired_salary: "must be a whole number" });
});

test("a non-JSON error page becomes a readable message", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("<html><body>Bad Gateway</body></html>", { status: 502 }));
  const error = (await api("/api/history/applied").catch((e: unknown) => e)) as ApiError;
  expect(errorMessage(error)).toBe("The app isn't responding (error 502). Check `make logs`, or run `make up`.");
});
