import { defineConfig, devices } from "@playwright/test";

// Runs against an already running stack: API (with content imported) + this app.
// Locally: start both, then `npm run e2e`. BASE_URL defaults to the local Next server.
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  // Remote runs hit free-tier instances (0.1 CPU, Argon2 hashing): allow slower responses.
  expect: { timeout: process.env.BASE_URL ? 20_000 : 5_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
