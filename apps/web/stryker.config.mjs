/** Mutation experiments use pure modules and their existing unit tests, without a server. */
const config = {
  $schema: "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  testRunner: "vitest",
  plugins: ["@stryker-mutator/vitest-runner"],
  mutate: ["lib/format.ts", "lib/auth/redirect.ts"],
  vitest: { configFile: "vitest.config.ts", related: true },
  coverageAnalysis: "perTest",
  reporters: ["clear-text", "json"],
  jsonReporter: { fileName: "reports/mutation/mutation.json" },
  concurrency: 2,
  timeoutMS: 5000,
  timeoutFactor: 2,
  thresholds: { high: 80, low: 60, break: 0 },
  tempDirName: ".stryker-tmp",
};

export default config;
