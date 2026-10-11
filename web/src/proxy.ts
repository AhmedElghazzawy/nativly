import { NextResponse, type NextRequest } from "next/server";

import { needsRefresh } from "@/lib/jwt";

// Kept in sync with lib/session.ts (proxy code shouldn't import server-only modules).
const ACCESS_COOKIE = "nativly_access";
const REFRESH_COOKIE = "nativly_refresh";
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const PROTECTED = ["/learn", "/lessons", "/progress", "/review", "/words"];
const AUTH_PAGES = ["/login", "/signup"];

/**
 * Keeps the session fresh: when the 15-minute access token is about to expire, swap the
 * refresh token for a new pair *before* the page renders (Server Components can't set cookies).
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  const isProtected = PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  const isAuthPage = AUTH_PAGES.includes(pathname);

  let tokens: Tokens | null = null;
  if (refresh && needsRefresh(access, Date.now())) {
    tokens = await refreshTokens(refresh);
  }
  const signedIn = Boolean(tokens) || (Boolean(access) && !needsRefresh(access, Date.now(), 0));

  if (isProtected && !signedIn) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    // Don't delete cookies here: a parallel response may have just stored a fresh pair.
    return NextResponse.redirect(login);
  }
  if (isAuthPage && signedIn) {
    return withTokens(NextResponse.redirect(new URL("/learn", request.url)), tokens);
  }
  if (!tokens) return NextResponse.next();

  // Let this request's Server Components see the new access token, and store both for later.
  request.cookies.set(ACCESS_COOKIE, tokens.access_token);
  return withTokens(NextResponse.next({ request: { headers: request.headers } }), tokens);
}

type Tokens = { access_token: string; refresh_token: string; expires_in: number };

// Prefetches and parallel navigations can all arrive with the same expiring session. Sending
// the same refresh token twice looks like token theft to the API (reuse detection revokes
// every session), so concurrent requests share one in-flight refresh. Entries live briefly.
const inFlight = new Map<string, Promise<Tokens | null>>();
const SHARE_WINDOW_MS = 30_000;

function refreshTokens(refreshToken: string): Promise<Tokens | null> {
  let pending = inFlight.get(refreshToken);
  if (!pending) {
    pending = requestRefresh(refreshToken);
    inFlight.set(refreshToken, pending);
    setTimeout(() => inFlight.delete(refreshToken), SHARE_WINDOW_MS);
  }
  return pending;
}

async function requestRefresh(refreshToken: string): Promise<Tokens | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    return response.ok ? ((await response.json()) as Tokens) : null;
  } catch {
    return null; // API unreachable: treat as signed out for this request
  }
}

function withTokens(response: NextResponse, tokens: Tokens | null) {
  if (!tokens) return response;
  const base = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
  };
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, { ...base, maxAge: tokens.expires_in });
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
    ...base,
    maxAge: 30 * 24 * 60 * 60,
  });
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|ico)$).*)"],
};
