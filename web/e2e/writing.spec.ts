import { expect, test, type Page } from "@playwright/test";

// Runs against the demo AI provider (NATIVLY_AI_PROVIDER=fake) locally and in CI.
const SHOTS = process.env.SCREENSHOT_DIR;

async function shot(page: Page, name: string) {
  if (SHOTS)
    await page.screenshot({
      path: `${SHOTS}/${test.info().project.name}-${name}.png`,
      fullPage: true,
    });
}

async function next(page: Page) {
  await page.getByRole("button", { name: /Continue|Finish lesson/ }).click();
}

/** Options are styled labels around a visually hidden radio; click them like a user does. */
async function choose(page: Page, option: RegExp) {
  await page
    .locator("label")
    .filter({ has: page.getByRole("radio", { name: option }) })
    .click();
}

async function check(page: Page) {
  await page.getByRole("button", { name: "Check answer" }).click();
  await next(page);
}

test("a learner writes about their family and gets feedback", async ({ page }) => {
  const email = `e2e-writing-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: /English A1/ }).click();
  await page.getByRole("link", { name: /This is my family/ }).click();

  await next(page); // explanation
  await choose(page, /Her$/);
  await check(page);
  await page.getByLabel("Blank 1").fill("Our");
  await page.getByLabel("Blank 2").fill("Their");
  await check(page);
  await next(page); // explanation
  await page.getByText("His name is Paul.").click();
  await check(page);
  await choose(page, /grandmother$/);
  await check(page);
  const bank = page.getByLabel("Word bank");
  for (const word of ["Their", "children", "are", "at", "school", "."]) {
    await bank.getByRole("button", { name: word, exact: true }).click();
  }
  await check(page);

  // Writing step
  await expect(page.getByText("Write about your family.")).toBeVisible();
  const feedbackButton = page.getByRole("button", { name: "Get feedback" });
  await page.getByLabel("Your text").fill("This is my family.");
  await expect(feedbackButton).toBeDisabled(); // under the minimum word count
  await page
    .getByLabel("Your text")
    .fill(
      "This is my family. I have one brother and one sister. My brother is twelve and his name is " +
        "Sam. My sister's name is Lina. My parents are teachers and they live in Toronto.",
    );
  await expect(page.getByText(/^\d+ \/ 25–80 words$/)).toBeVisible();
  await shot(page, "20-writing");
  await feedbackButton.click();

  await expect(page.getByRole("heading", { name: "Corrected text" })).toBeVisible();
  await expect(page.getByText(/Demo mode/)).toBeVisible();
  await shot(page, "21-writing-feedback");
  await next(page);
  await expect(page.getByText("Lesson complete")).toBeVisible();
});
