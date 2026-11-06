import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // The production image runs .next/standalone (IMP-218, A1 §4.3).
  output: "standalone",
  // The root CLAUDE.md is the only instruction file; stop `next dev` from writing AGENTS.md.
  agentRules: false,
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
