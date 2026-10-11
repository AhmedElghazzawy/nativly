import "server-only";

import { redirect } from "next/navigation";

import { getAccessToken } from "@/lib/session";

export const API_URL = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`API ${status}: ${detail}`);
  }
}

function errorDetail(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const { detail } = body as { detail: unknown };
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{ msg: "..." }, ...]
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return "Something went wrong";
}

/** Call the API without credentials (register, login, refresh). */
export async function publicFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init.headers },
    cache: "no-store",
  });
  const body: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, errorDetail(body));
  return body as T;
}

/**
 * Call the API as the signed-in learner. The proxy refreshes tokens before requests reach
 * here, so a 401 means the session is really gone: send the learner to log in.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  if (!token) redirect("/login");
  try {
    return await publicFetch<T>(path, {
      ...init,
      headers: { authorization: `Bearer ${token}`, ...init.headers },
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
}
