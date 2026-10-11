import { describe, expect, it } from "vitest";

import { formatInterval } from "./format";

describe("formatInterval", () => {
  it.each([
    [30, "<1m"],
    [60, "1m"],
    [600, "10m"],
    [3 * 3600, "3h"],
    [86400, "1d"],
    [4 * 86400, "4d"],
    [60 * 86400, "2mo"],
    [365 * 86400, "1y"],
    [548 * 86400, "1.5y"],
  ])("%i seconds -> %s", (seconds, label) => {
    expect(formatInterval(seconds)).toBe(label);
  });
});
