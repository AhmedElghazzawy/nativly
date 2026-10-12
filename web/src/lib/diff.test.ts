import { describe, expect, it } from "vitest";

import { countWords, diffWords } from "./diff";

describe("diffWords", () => {
  it("marks replaced words as removed then added", () => {
    expect(diffWords("Yesterday I go to the park", "Yesterday I went to the park")).toEqual([
      { type: "same", text: "Yesterday I" },
      { type: "removed", text: "go" },
      { type: "added", text: "went" },
      { type: "same", text: "to the park" },
    ]);
  });

  it("handles insertions and deletions at the edges", () => {
    expect(diffWords("went to park", "I went to the park.")).toEqual([
      { type: "added", text: "I" },
      { type: "same", text: "went to" },
      { type: "removed", text: "park" },
      { type: "added", text: "the park." },
    ]);
  });

  it("returns one same part for identical text and nothing for empty text", () => {
    expect(diffWords("All good here.", "All good here.")).toEqual([
      { type: "same", text: "All good here." },
    ]);
    expect(diffWords("", "")).toEqual([]);
  });
});

describe("countWords", () => {
  it("matches the API's word count", () => {
    expect(countWords("I don’t know, it's well-known: 25 years.")).toBe(7);
    expect(countWords("   ")).toBe(0);
  });
});
