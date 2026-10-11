"use server";

import { redirect } from "next/navigation";

import { ApiError, publicFetch } from "@/lib/api";
import { clearTokens, saveTokens } from "@/lib/session";
import type { TokenPair } from "@/lib/types";

export type AuthState = { error?: string; email?: string };

function credentials(formData: FormData) {
  return {
    email: String(formData.get("email") ?? "").trim(),
    password: String(formData.get("password") ?? ""),
  };
}

/** Only allow same-site relative paths, so `?next=` can't redirect off-site. */
function safeNext(formData: FormData): string {
  const next = String(formData.get("next") ?? "");
  return next.startsWith("/") && !next.startsWith("//") ? next : "/learn";
}

async function logIn(email: string, password: string): Promise<void> {
  const tokens = await publicFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  await saveTokens(tokens);
}

export async function login(_: AuthState, formData: FormData): Promise<AuthState> {
  const { email, password } = credentials(formData);
  try {
    await logIn(email, password);
  } catch (error) {
    if (error instanceof ApiError && [401, 422].includes(error.status)) {
      return { error: "That email and password don't match.", email };
    }
    return { error: "We couldn't reach the server. Please try again.", email };
  }
  redirect(safeNext(formData));
}

export async function signup(_: AuthState, formData: FormData): Promise<AuthState> {
  const { email, password } = credentials(formData);
  if (password.length < 8) {
    return { error: "Use at least 8 characters for your password.", email };
  }
  try {
    await publicFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await logIn(email, password);
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      return { error: "There's already an account with this email. Try logging in.", email };
    }
    if (error instanceof ApiError && error.status === 422) {
      return { error: "Please enter a valid email address.", email };
    }
    return { error: "We couldn't reach the server. Please try again.", email };
  }
  redirect("/learn");
}

export async function logout(): Promise<void> {
  const refresh = await clearTokens();
  if (refresh) {
    // Best effort: revoke server-side too. The cookies are already gone either way.
    await publicFetch("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => undefined);
  }
  redirect("/");
}
