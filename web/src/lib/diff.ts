export type DiffPart = { type: "same" | "removed" | "added"; text: string };

/**
 * Word-level diff of the learner's text against the corrected text (longest common
 * subsequence over whitespace-separated tokens). Texts here are short (< 1,000 words), so the
 * O(n·m) table is fine. Adjacent parts of the same type are merged for display.
 */
export function diffWords(original: string, corrected: string): DiffPart[] {
  const a = original.split(/\s+/).filter(Boolean);
  const b = corrected.split(/\s+/).filter(Boolean);
  const lcs: number[][] = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const parts: DiffPart[] = [];
  const push = (type: DiffPart["type"], word: string) => {
    const last = parts.at(-1);
    if (last && last.type === type) last.text += ` ${word}`;
    else parts.push({ type, text: word });
  };
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      push("same", a[i]);
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      push("removed", a[i++]);
    } else {
      push("added", b[j++]);
    }
  }
  while (i < a.length) push("removed", a[i++]);
  while (j < b.length) push("added", b[j++]);
  return parts;
}

/** Same rule as the API: words may contain apostrophes and hyphens. */
export function countWords(text: string): number {
  return text.match(/[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*/g)?.length ?? 0;
}
