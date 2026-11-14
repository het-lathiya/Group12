# Provider spending and quota limit

- Owner: Kirtan
- Status: Awaiting validation
- Date: 14 November 2026

Application guards use RATE_LIMIT_PER_MIN, AI_DAILY_GENERATIONS_PER_USER and AI_DAILY_GENERATIONS_GLOBAL. AI_MAX_INPUT_TOKENS trims requests; AI_MAX_OUTPUT_TOKENS bounds provider output when configured. Explicit rule-based plans bypass daily generation caps.

The provider account owner must record the chosen account/project quota and spending limit at setup, including the model, console setting and verification date. No provider-side value is claimed before that validation. Application caps bound attempt counts and do not replace a provider-side spending limit.
