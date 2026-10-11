import { expect, test, type Page } from "@playwright/test";

const SHOTS = process.env.SCREENSHOT_DIR;

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${test.info().project.name}-${name}.png`, fullPage: true });
}

async function check(page: Page) {
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByRole("status")).toBeVisible();
}

async function next(page: Page) {
  await page.getByRole("button", { name: /Continue|Finish lesson/ }).click();
}

test("a new learner signs up, completes lesson 1 and sees progress", async ({ page }) => {
  await page.goto("/");
  await shot(page, "01-home");
  await page.getByRole("link", { name: "Start learning free" }).click();

  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-password-123");
  await shot(page, "02-signup");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Your course" })).toBeVisible();
  await expect(page.getByText("Talking about the past")).toBeVisible();
  await shot(page, "03-learn");
  await page.getByRole("link", { name: /What I did yesterday/ }).click();

  // 1. Explanation
  await expect(page.getByRole("heading", { name: "Finished actions in the past" })).toBeVisible();
  await shot(page, "04-explain");
  await next(page);

  // 2. MCQ: answer wrong first to see a correction
  await page.getByText("visitted").click();
  await check(page);
  await expect(page.getByText("Not quite")).toBeVisible();
  await expect(page.getByText("Correct answer:")).toBeVisible();
  await shot(page, "05-mcq-wrong");
  await next(page);

  // 3. Cloze
  await page.getByLabel("Blank 1").fill("Lived");
  await page.getByLabel("Blank 2").fill("studied");
  await check(page);
  await expect(page.getByText("Correct!")).toBeVisible();
  await shot(page, "06-cloze-right");
  await next(page);

  // 4. Explanation, 5. MCQ
  await next(page);
  await page.getByText("I watched a film last night.").click();
  await check(page);
  await next(page);

  // 6. Cloze
  await page.getByLabel("Blank 1").fill("ago");
  await page.getByLabel("Blank 2").fill("last");
  await check(page);
  await next(page);

  // 7. Reorder
  const bank = page.getByLabel("Word bank");
  for (const word of ["She", "played", "tennis", "with", "her", "friends", "last", "weekend"]) {
    await bank.getByRole("button", { name: word, exact: true }).click();
  }
  await shot(page, "07-reorder");
  await check(page);
  await expect(page.getByText("Correct!")).toBeVisible();
  await next(page);

  // Summary: one wrong answer out of five exercises -> 80%
  await expect(page.getByText("Lesson complete")).toBeVisible();
  await expect(page.getByText("80%")).toBeVisible();
  await shot(page, "08-complete");

  await page.getByRole("link", { name: "See my progress" }).click();
  await expect(page.getByRole("heading", { name: "Your progress" })).toBeVisible();
  await expect(page.getByText("1 completed")).toBeVisible();
  await shot(page, "09-progress");

  await page.getByRole("link", { name: "Learn" }).click();
  await expect(page.getByLabel("Completed")).toBeVisible();
});

test("signed-out visitors are sent to log in and back", async ({ page }) => {
  await page.goto("/progress");
  await expect(page).toHaveURL(/\/login\?next=%2Fprogress/);
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("That email and password don't match.")).toBeVisible();
});
