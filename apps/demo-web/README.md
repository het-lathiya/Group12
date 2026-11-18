# Demo frontend (demo_test)

Alternative UI for the AI Travel Planner, built from the Stitch design and **connected to the staging API** (real Supabase sign-in, trips, AI generation, itinerary edits, costs, versions, saved places). Not the production app (`apps/web` is unchanged).

## How it talks to the backend

The browser only calls same-origin `/api/v1/...`, so the staging API's `ALLOWED_ORIGINS` needs no change:

- `npm run dev`: `next.config.ts` rewrites `/api/*` to the staging API.
- AWS Amplify: a 200 rewrite rule proxies `/api/*` to the staging API (see `deploy/aws-deploy.sh`).

Trip pages are prerendered once as `/trips/_/...`; the hosting rewrites every real trip id to it and the page reads the id from the address bar (`lib/session.tsx` → `useTripId`).

## Run locally

```bash
cd apps/demo-web
cp .env.example .env.local   # fill in the public STAGING_SUPABASE_* values from the repo variables
npm install
npm run dev                  # http://localhost:3000
```

## Deploy / turn off on AWS (account owner only)

```bash
./deploy/aws-deploy.sh       # builds out/, creates or updates the Amplify app, prints the URL
./deploy/aws-teardown.sh     # deletes the Amplify app (stops all cost)
```

Resources are tagged `Project=group12-demo_test`.

## Pages

`/`, `/sign-in`, `/sign-up`, `/dashboard`, `/profile`, `/trips/new`, and per trip: `generate`, `itinerary`, `explore`, `edit`, `costs`, `versions`, `summary`. The landing and sign-in visuals use sample photos from `lib/data.ts`; everything after sign-in comes from the API.
