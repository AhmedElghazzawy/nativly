import "server-only";

import { cookies } from "next/headers";

import type { TokenPair } from "@/lib/types";

// Tokens live only in httpOnly cookies set by the Next.js server, so browser JavaScript
// (and any injected script) can never read them. See docs/decisions/0002.
export const ACCESS_COOKIE = "nativly_access";
export const REFRESH_COOKIE = "nativly_refresh";

const REFRESH_MAX_AGE = 30 * 24 * 60 * 60; // matches the API's refresh token lifetime

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

/** Only callable from Server Actions and Route Handlers (Next.js forbids setting cookies elsewhere). */
export async function saveTokens(tokens: TokenPair): Promise<void> {
  const jar = await cookies();
  jar.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(tokens.expires_in));
  jar.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE));
}

export async function clearTokens(): Promise<string | undefined> {
  const jar = await cookies();
  const refresh = jar.get(REFRESH_COOKIE)?.value;
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
  return refresh;
}

export async function getAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}
