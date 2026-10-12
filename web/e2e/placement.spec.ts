import { expect, test, type Page } from "@playwright/test";

const SHOTS = process.env.SCREENSHOT_DIR;

async function shot(page: Page, name: string) {
  if (SHOTS)
    await page.screenshot({
      path: `${SHOTS}/${test.info().project.name}-${name}.png`,
      fullPage: true,
    });
}

test("a new learner takes the placement test and starts the recommended course", async ({
  page,
}) => {
  const email = `e2e-placement-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.getByRole("link", { name: /Take the placement test/ }).click();
  await expect(page.getByRole("heading", { name: "Find your level" })).toBeVisible();
  await shot(page, "30-placement-intro");
  await page.getByRole("button", { name: "Start the test" }).click();

  for (let n = 1; n <= 18; n++) {
    await expect(page.getByText(`${n}/18`)).toBeVisible();
    if (n === 13) await shot(page, "31-placement-reading");
    // Always the first option: the result varies with the bank, the flow must not.
    await page.locator("form label").first().click();
    await page.getByRole("button", { name: "Next", exact: true }).click();
  }

  await expect(page.getByText("Your level", { exact: true })).toBeVisible();
  for (const skill of ["Grammar", "Vocabulary", "Reading"]) {
    await expect(page.getByText(skill, { exact: true })).toBeVisible();
  }
  await shot(page, "32-placement-result");

  await page.getByRole("link", { name: "Start your course" }).click();
  await expect(page.getByRole("heading", { name: "Your course" })).toBeVisible();
  // The recommended course is remembered: /learn now opens it directly.
  await page.getByRole("link", { name: "Learn", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your course" })).toBeVisible();
});
