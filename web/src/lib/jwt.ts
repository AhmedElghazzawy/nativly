/**
 * Reads the `exp` claim of a JWT without verifying it. Only used to decide *when* to refresh;
 * the API verifies every token, so trusting this value can never grant access.
 */
export function tokenExpiresAt(token: string): number | null {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const json = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as {
      exp?: unknown;
    };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** True when the token is missing, unreadable, or expires within `marginMs`. */
export function needsRefresh(token: string | undefined, now: number, marginMs = 60_000): boolean {
  if (!token) return true;
  const expiresAt = tokenExpiresAt(token);
  return expiresAt === null || expiresAt - now <= marginMs;
}
