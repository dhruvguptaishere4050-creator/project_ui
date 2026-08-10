import type { AuthSession } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// The access token is kept in memory only. The refresh token lives in an
// HttpOnly cookie the browser sends to /api/auth, so nothing persists a
// credential where injected scripts can read it.
let session: AuthSession | null = null;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return response.statusText;
  }
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response = await send(path, init);
  if (response.status === 401 && session) {
    // The access token is short lived; swap it for a fresh one and retry once.
    const renewed = await refreshSession();
    if (!renewed) throw new ApiError("Your session expired. Please sign in again.", 401);
    response = await send(path, init);
  }
  if (response.status === 401) {
    session = null;
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    body,
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  session = (await response.json()) as AuthSession;
  return session;
}

export async function refreshSession(): Promise<AuthSession | null> {
  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  session = response.ok ? ((await response.json()) as AuthSession) : null;
  return session;
}

export async function logout(): Promise<void> {
  session = null;
  await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
}
