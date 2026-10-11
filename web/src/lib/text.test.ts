import { describe, expect, it } from "vitest";

import { joinTokens, normalize, splitCloze } from "./text";

describe("joinTokens", () => {
  it("adds spaces between words but not before punctuation", () => {
    expect(joinTokens(["Where", "did", "you", "go", "?"])).toBe("Where did you go?");
    expect(joinTokens(["Yes", ",", "I", "did", "."])).toBe("Yes, I did.");
  });

  it("handles empty input", () => {
    expect(joinTokens([])).toBe("");
  });
});

describe("normalize", () => {
  it("matches the API's forgiving comparison", () => {
    expect(normalize("  Didn’t   GO ")).toBe("didn't go");
  });
});

describe("splitCloze", () => {
  it("returns one more part than blanks", () => {
    expect(splitCloze("I ___ to ___ yesterday.")).toEqual(["I ", " to ", " yesterday."]);
  });
});
