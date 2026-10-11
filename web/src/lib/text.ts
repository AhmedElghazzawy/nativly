const NO_SPACE_BEFORE = new Set([".", ",", "!", "?", ";", ":", "'s", "n't"]);

/** Join reorder tokens into readable text: no space before punctuation or clitics. */
export function joinTokens(tokens: readonly string[]): string {
  return tokens.reduce(
    (text, token, i) => (i === 0 || NO_SPACE_BEFORE.has(token) ? text + token : `${text} ${token}`),
    "",
  );
}

/** Mirror of the API's answer normalization, for display only (the server decides correctness). */
export function normalize(text: string): string {
  return text
    .normalize("NFKC")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase();
}

/** Split cloze text on its ___ blanks. N blanks give N + 1 text parts. */
export function splitCloze(text: string): string[] {
  return text.split("___");
}
