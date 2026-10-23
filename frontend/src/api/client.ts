export class ApiError extends Error {
  status: number;
  detail: unknown;
  fieldErrors: Record<string, string>;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
    const errors = (detail as { field_errors?: Record<string, string> } | null)?.field_errors;
    this.fieldErrors = errors ?? {};
  }
}

let onUnauthorized: () => void = () => {
  if (!window.location.pathname.startsWith("/login")) window.location.assign("/login");
};

/** Called on any 401 except the login request itself (the app sends you to /login). */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

type Options = Omit<RequestInit, "body"> & { body?: unknown };

export async function api<T = unknown>(path: string, options: Options = {}): Promise<T> {
  const { body, headers, ...rest } = options;
  const init: RequestInit = { credentials: "include", ...rest, headers: { ...(headers as Record<string, string>) } };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["content-type"] = "application/json";
  }
  const response = await fetch(path, init);
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail ?? data;
    if (response.status === 401 && path !== "/api/auth/login") onUnauthorized();
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    // An HTML error page (nginx 502 while the api restarts), not an API message.
    if (typeof error.detail === "string" && error.detail.trimStart().startsWith("<"))
      return `The app isn't responding (error ${error.status}). Check \`make logs\`, or run \`make up\`.`;
    if (typeof error.detail === "string") return error.detail;
    if (error.status >= 500) return "The server had a problem. Check `make logs` and try again.";
    return error.message;
  }
  if (error instanceof TypeError) return "Can't reach the app. Is it running (`make up`)?";
  return "Something went wrong.";
}
