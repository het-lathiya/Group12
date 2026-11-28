# Decision: hosted accounts, keys and email sender (IMP-113)

- Card: IMP-113 · Provision accounts, keys and email sender with named owners (US-004; NFR-013, NFR-037)
- Status: **template; outcome pending** (TO BE FILLED BY KIRTAN, JUNAID AND NIDHI)
- Parts:
  - section 1: accounts and secrets register (Kirtan, lead);
  - section 2: OpenRouteService key and email sender (Junaid);
  - section 3: Gemini key, model ID and data-use terms (Nidhi).
- Secrets register: [docs/secrets.md](../secrets.md)
- Open decisions touched: OD-04, OD-06, OD-14, OD-15 (specification §1.9 and Appendix B.3; `docs/spec/DECISION_REGISTER.md`, "Unresolved decisions")

Every field marked **TO BE FILLED BY &lt;member&gt;** is filled in by that member from the account itself.

**This file never holds a value.** That covers:

- key values;
- passwords;
- connection strings;
- login e-mail addresses;
- recovery codes;
- personal data.

Write only yes/no answers, roles, member names, dates and the facts the card asks for. Keys live in the team password manager and the hosting dashboards only (CLAUDE.md §6; [docs/secrets.md](../secrets.md)).

## 1. Accounts (Kirtan)

One row per hosted account (card step 1). Each account uses a team-owned login, never a member's personal address, and its credentials are kept in the team password manager (US-004 AC1).

| Account | Purpose | Owner role | Owner member | Team-owned login (yes/no) | Password-manager entry (yes/no) | Created on (YYYY-MM-DD) |
| --- | --- | --- | --- | --- | --- | --- |
| GitHub repository `het-lathiya/Group12` | Code, pull requests, CI, the GitHub Actions secret store for the deploy workflows | Repository owner; DevOps Engineer and Integration Lead for settings and secrets | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Vercel | Web app hosting: staging, production and pull-request previews (IMP-112) | DevOps Engineer and Integration Lead | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Render | API container hosting, staging and production (IMP-112) | DevOps Engineer and Integration Lead | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Supabase staging project | Hosted Postgres and Auth for staging (§4.5) | DevOps Engineer and Integration Lead; Database Engineer for the schema | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Supabase production project (OD-15: a second project, or the staging project after SG-7) | Hosted Postgres and Auth for production (IMP-801) | DevOps Engineer and Integration Lead | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Google AI Studio (Gemini) | `GEMINI_API_KEY` for staging, production and `make live-smoke` (section 3) | AI Engineer, Provider Layer | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| OpenRouteService | `ORS_API_KEY` for staging and production (section 2) | Backend and QA Engineer, Routing | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |
| Email sender (optional) | Sign-up confirmation e-mail for hosted Supabase Auth, if a sender other than the Supabase default is used (section 2) | Backend and QA Engineer, Routing (card part: Junaid) | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |

Record "not created" in "Created on" for the optional email sender if it is not used, and for the production project if OD-15 ends with one project.

**GitHub access for Render and Vercel.** Render and Vercel deploy from `het-lathiya/Group12` through their GitHub apps. Only the repository owner (het-lathiya) can approve that access. Whoever creates the Render and Vercel projects asks the repository owner to approve it.

### Supabase projects (OD-15, OD-06)

| Item | Result |
| --- | --- |
| OD-15: one or two Supabase projects (staging and production) | TO BE FILLED BY KIRTAN |
| Whether the plan in use allows two active projects, as the Supabase pages show it, with the date checked | TO BE FILLED BY KIRTAN |
| OD-06: hosted token verification mode (JWKS through `SUPABASE_JWKS_URL`, or HS256 through `SUPABASE_JWT_SECRET`; both are implemented, IMD-04). The OD-06 owner is Het | TO BE FILLED BY KIRTAN |
| Rows of [docs/secrets.md](../secrets.md) checked against the stores, with the date | TO BE FILLED BY KIRTAN |

## 2. OpenRouteService and email confirmation (Junaid)

### OpenRouteService key

| Item | Result |
| --- | --- |
| Key obtained (yes/no) | TO BE FILLED BY JUNAID |
| Plan or tier, as the OpenRouteService account page shows it | TO BE FILLED BY JUNAID |
| Limits shown for the endpoints the routing client uses (requests per minute and per day), copied as shown | TO BE FILLED BY JUNAID |
| Key stored in the password manager and the Render settings (yes/no) | TO BE FILLED BY JUNAID |
| Date obtained and limits read (YYYY-MM-DD) | TO BE FILLED BY JUNAID |

Without a key the routing client uses the distance estimate (§4.5: local and test run without one). The key value goes only into the password manager and the Render settings, never into this file.

### Email confirmation on staging (card step 4)

| Item | Result |
| --- | --- |
| Decision for the staging Supabase project: confirmation on or off | TO BE FILLED BY JUNAID |
| Reason for the decision | TO BE FILLED BY JUNAID |
| Sender of the confirmation e-mail: the Supabase default, or the optional sender of section 1 | TO BE FILLED BY JUNAID |
| Non-team sign-up test: date (YYYY-MM-DD) | TO BE FILLED BY JUNAID |
| Non-team sign-up test: result (confirmation e-mail received yes/no; the link opened the staging web app and signed in yes/no; or "not run: confirmation off") | TO BE FILLED BY JUNAID |

Record the test as "a non-team address" only. Do not write the address, the e-mail content or the link here.

**Dependency of IMP-109 on this setting.** IMP-109's no-enumeration behaviour depends on confirmation being on:

- With confirmation on, sign-up shows the same neutral notice for a new and an existing address.
- With confirmation off, a new address is signed in at once while an existing address gets the notice, so a sign-up reveals whether an address has an account.

The local stack has confirmation off (`docs/progress/parts/IMP-109-whole-task.md`, open issues). If the decision above is "off", record that consequence in the reason.

## 3. Gemini API key, model ID and data-use terms (Nidhi)

Card step 3 (OD-04, OD-14). Fill this in from the official Gemini pricing, terms and rate-limit pages as they read on the date below. The IMP-301 spike confirms the model and records the API style (OD-14) in `docs/decisions/gemini-setup.md`.

| Item | Result |
| --- | --- |
| Key obtained (yes/no) | Yes, held by the operator (Het). The staging copy goes into SSM `/group12/staging/GEMINI_API_KEY` when Kirtan builds staging; not yet confirmed |
| Tier: free or paid | Not yet stated |
| Data-use terms accepted: the name of the terms and what they say about the use of prompts and responses on this tier | TO BE FILLED BY NIDHI |
| Rate limits shown for the chosen model (requests per minute, tokens per minute, requests per day), copied as shown | TO BE FILLED BY NIDHI |
| Chosen `GEMINI_MODEL_ID` | `gemini-3.5-flash-lite` (Interactions API) |
| Chosen `GEMINI_EMBEDDING_MODEL_ID` | `gemini-embedding-2` (team choice) |
| Spending control for the billed key (NFR-037; §4.5 requires it in production): set yes/no, and where | TO BE FILLED BY NIDHI |
| Key stored in the password manager and the Render settings (yes/no) | TO BE FILLED BY NIDHI |
| Date the pages were read and the key created (YYYY-MM-DD) | Pages read: TO BE FILLED BY NIDHI. Key created: not yet stated |

The rules for `GEMINI_MODEL_ID` are in specification §8: one specific stable identifier, never a `-latest` alias or a preview identifier, stored exactly as configured.

Official pages read, one row each:

| Page title | URL | Read on (YYYY-MM-DD) |
| --- | --- | --- |
| TO BE FILLED BY NIDHI | TO BE FILLED BY NIDHI | TO BE FILLED BY NIDHI |

Add rows as needed.

**Where the key lives.** `GEMINI_API_KEY` lives only in the team password manager and the hosting dashboards (Render settings; CLAUDE.md §6, [docs/secrets.md](../secrets.md)):

- It never goes into the repository, pull-request CI, an issue or chat.
- A personal key for `make live-smoke` stays in the member's untracked `apps/api/.env`.
- Do not set `GOOGLE_API_KEY`.

## 4. Groq second provider (IMD-223, Nidhi; RUN-108)

Decision date and official pages read: **2026-11-28**. Use the **free tier**, one team-owned
account and one team key; no key or account rotation to bypass limits. Account creation, actual
dashboard limits, and hosted SSM provisioning are **not verified** in this run.

| Item | Recorded choice or evidence |
| --- | --- |
| Model ID | `openai/gpt-oss-20b`, listed as a production model with strict structured outputs |
| Order | Gemini primary → Gemini fallback model (IMD-222) → optional Groq → labelled rule-based plan (IMD-33) |
| Public free-plan limits shown | 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, 200,000 tokens/day for this model; organization limits, subject to the account's console |
| Rate-limit headers | `retry-after` (seconds on 429); `x-ratelimit-{limit,remaining,reset}-requests` concern daily requests, `x-ratelimit-{limit,remaining,reset}-tokens` concern tokens/minute. Adapter honors `retry-after` inside its time allowance |
| Embeddings | Gemini only, with lexical retrieval fallback (IMD-112); Groq does not change the vector space |
| Prompt compatibility | Same versioned prompts and Pydantic io-1/io-2. Only the adapter's wire schema removes defaults, closes objects and requires all properties; nullable unions remain. Other models use best-effort schema mode or JSON object mode as documented |
| Live verification | Recorded in `docs/progress/parts/IMD-223-groq-contract.md`; no account credential is recorded here |

The [Groq Services Agreement](https://console.groq.com/docs/legal/services-agreement), modified
22 June 2026, governs cloud use. Its §8 leaves inputs and outputs owned by the customer, grants
limited service-delivery rights, and limits use of customer-supplied training data to providing
the customer's service. This is a reading of the official terms; account acceptance is not verified.

[Your Data in GroqCloud](https://console.groq.com/docs/your-data) says usage metadata is retained,
and ordinary inference content is not retained by default. Reliability or abuse investigations
can retain content for up to 30 days, with legal exceptions. Organization admins can enable zero
data retention; that account setting is not verified. Retained content is stored in the US.
Only the existing redacted generation request is sent; no training or persistent features are enabled.

Other official pages read on 2026-11-28:
[models](https://console.groq.com/docs/models),
[structured outputs](https://console.groq.com/docs/structured-outputs),
[OpenAI compatibility](https://console.groq.com/docs/openai),
[chat-completion reference](https://console.groq.com/docs/api-reference),
[rate limits](https://console.groq.com/docs/rate-limits).
