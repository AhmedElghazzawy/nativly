import { describe, expect, it } from "vitest";

import { needsRefresh, tokenExpiresAt } from "./jwt";

function token(payload: object): string {
  const encode = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${encode({ alg: "HS256" })}.${encode(payload)}.signature`;
}

describe("tokenExpiresAt", () => {
  it("reads exp in milliseconds", () => {
    expect(tokenExpiresAt(token({ exp: 1_700_000_000 }))).toBe(1_700_000_000_000);
  });

  it.each(["", "not-a-jwt", "a.%%%.c", token({ sub: "x" })])("returns null for %j", (bad) => {
    expect(tokenExpiresAt(bad)).toBeNull();
  });
});

describe("needsRefresh", () => {
  const now = 1_700_000_000_000;

  it("is false for a token with time left", () => {
    expect(needsRefresh(token({ exp: now / 1000 + 600 }), now)).toBe(false);
  });

  it("is true inside the safety margin", () => {
    expect(needsRefresh(token({ exp: now / 1000 + 30 }), now)).toBe(true);
  });

  it("is true for missing or unreadable tokens", () => {
    expect(needsRefresh(undefined, now)).toBe(true);
    expect(needsRefresh("garbage", now)).toBe(true);
  });
});
