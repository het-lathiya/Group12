# Demo frontend (test only)

Clickable UI demo of the AI Travel Planner, built from the Stitch design. **All data is mock** (`lib/data.ts`); nothing calls the API yet. This is not the production web app (`apps/web`).

## Run locally

```bash
cd apps/demo-web
npm install
npm run dev        # http://localhost:3000
```

## Static build

```bash
npm run build      # writes static files to out/
```

`out/` can be hosted on any static host (S3 + CloudFront, Netlify, Amplify).

## Pages

`/`, `/sign-in`, `/sign-up`, `/dashboard`, `/profile`, `/trips/new`, and for each mock trip (`rajasthan-winter`, `goa-ny`, `kerala`): `itinerary`, `explore`, `edit`, `generate`, `costs`, `versions`, `summary`.
