import { defineConfig, devices } from "@playwright/test";

import { FEATURE_NAMES, parseDisabledFeatures } from "./lib/flags";

// BASE_URL runs the specs against a deployment (make e2e BASE_URL=...); otherwise the dev server.
const baseURL = process.env.BASE_URL ?? "http://localhost:3000";

// The widths of US-122 and §7.9: phone, tablet, laptop and wide desktop; chromium-360 is TC-373.
const WIDTHS = [360, 768, 1280, 1920] as const;

// E2E-07, TC-371 (IMD-33): its own web app on 3001, built against its own API on 8001.
const PROVIDER_FAILURE_SPEC = /provider-failure\.spec\.ts$/;
const providerFailureURL =
  process.env.PROVIDER_FAILURE_BASE_URL ?? "http://localhost:3001";

// TC-372: the floor journey runs only when the API and the web build were started with the nine
// cut-list switches off (both variables are read by the servers, not by the specs). In CI that is
// the E2E workflow's features_disabled dispatch input (IMP-699).
const CUT_LIST = FEATURE_NAMES.slice(0, 9);
const floor = [
  process.env.FEATURES_DISABLED,
  process.env.NEXT_PUBLIC_FEATURES_DISABLED,
].every((raw) => {
  const off = parseDisabledFeatures(raw);
  return CUT_LIST.every((name) => off.has(name));
});

const desktop = devices["Desktop Chrome"];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // IMP-701: no retries, so a flaky test fails the run and is fixed instead of hidden.
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  projects: [
    ...WIDTHS.map((width) => ({
      name: `chromium-${width}`,
      testIgnore: PROVIDER_FAILURE_SPEC,
      use: {
        ...desktop,
        viewport: { width, height: width < 768 ? 800 : 900 },
      },
    })),
    {
      name: "provider-failure",
      testMatch: PROVIDER_FAILURE_SPEC,
      use: { ...desktop, baseURL: providerFailureURL },
    },
    ...(floor
      ? [
          {
            name: "floor-journey",
            testMatch: /journey\.spec\.ts$/,
            use: { ...desktop, viewport: { width: 1280, height: 900 } },
          },
        ]
      : []),
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: "npm run dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
