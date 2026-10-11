import { expect, test, type Page } from "@playwright/test";

const SHOTS = process.env.SCREENSHOT_DIR;

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${test.info().project.name}-${name}.png`, fullPage: true });
}

async function signUp(page: Page) {
  const email = `e2e-words-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: /English A2/ }).click();
  await expect(page.getByRole("heading", { name: "Your course" })).toBeVisible();
}

test("a learner starts a word deck and does a daily review", async ({ page }) => {
  await signUp(page);
  await expect(page.getByText("Learn the words for this unit")).toBeVisible();
  await shot(page, "10-learn-banner");

  await page.getByRole("link", { name: "Words", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Word decks" })).toBeVisible();
  const deck = page.getByRole("listitem").filter({ hasText: "Past tense: everyday verbs" });
  await deck.getByRole("button", { name: "Study this deck" }).click();
  await expect(page.getByText("Studying", { exact: true })).toBeVisible();
  await shot(page, "11-words");

  await page.getByRole("link", { name: "Review", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Daily review" })).toBeVisible();
  await expect(page.getByText("New word", { exact: true })).toBeVisible();
  await expect(page.getByText("10 left")).toBeVisible(); // daily allowance of new words
  await shot(page, "12-review-front");

  // Mouse: reveal and rate the first card.
  await page.getByRole("button", { name: "Show answer" }).click();
  await expect(page.getByRole("group", { name: "How well did you remember?" })).toBeVisible();
  await shot(page, "13-review-back");
  await page.getByRole("button", { name: /^Easy/ }).click();
  await expect(page.getByText("9 left")).toBeVisible();

  // Keyboard: Space reveals, 4 rates "Easy" (graduates the word out of today's session).
  for (let left = 9; left > 0; left--) {
    await expect(page.getByText(`${left} left`)).toBeVisible();
    await page.keyboard.press("Space");
    await page.keyboard.press("4");
  }

  await expect(page.getByText("10 reviews done")).toBeVisible();
  await shot(page, "14-review-done");

  await page.getByRole("link", { name: "Words", exact: true }).click();
  await expect(page.getByText("10 of 30 words started")).toBeVisible();
});
