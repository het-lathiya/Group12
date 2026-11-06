# IMP-218 · web-image part

- Run id: RUN-042
- Owner: Manasvi
- Card lead: Junaid
- Status: **implemented; the image is verified locally. Its deployment on AWS is verified after merge**
- Base commit: `2c66e14`
- Traces to: US-002, US-163; NFR-015, NFR-035; TC-338, TC-355, TC-434

## Changed files

- `apps/web/next.config.ts` (modified): `output: "standalone"`.
- `apps/web/Dockerfile` (created). A multi-stage build on `node:22-slim`:
  - The build stage runs `npm ci` and `next build`, with the four `NEXT_PUBLIC_*` values and `BUILD_VERSION` as build arguments.
  - The runtime stage copies `.next/standalone`, `.next/static` and `public`, and runs `node server.js` as the non-root user `node` with `PORT=3000` and `HOSTNAME=0.0.0.0`.
- `apps/web/.dockerignore` (created): `node_modules`, `.next`, env files, tests and test output.
- `.dockerignore` at the repository root (created): the card's list, plus `**/__pycache__`, `graphify-out` and `data/fixtures`.
- `docker-compose.yml` (modified): the `web` service. The build arguments default to public local values.

## Commands run

| Command | Result line |
| --- | --- |
| `docker build -t group12-web:imp218 ... apps/web` | `naming to docker.io/library/group12-web:imp218 done`; image size `426MB` |
| `docker run` of the image, then `curl` | `GET / 200`, `GET /sign-in 200`, `GET /dashboard 200`, `GET /no-such-page 404`, a `/_next/static/chunks/` CSS file `200 text/css`, a `public/` file `200` |
| `id` in the container | `uid=1000(node) gid=1000(node) groups=1000(node)` |
| `docker compose up -d api web`, `make smoke URL=http://localhost:8000` | `4 passed, 1 skipped in 0.13s` |
| `make smoke URL=http://localhost:8000 ARGS='--web-origin http://localhost:3000'` | `5 passed in 0.06s` |
| `curl` of the web service under compose | `web / 200` |
| Scan of the image file system for `.env` files | `count: 0` |
| Scan of `/app` for key-like values (Google API keys, Supabase secret keys, JWTs, AWS keys, private keys, connection strings with a password, `*_KEY=` and `SECRET=` lines) | `matches: 0` |
| `next build` with the CI placeholders, then a scan of `.next/static` and `.next/standalone` | `✓ Generating static pages using 12 workers (11/11)`; no key value and no `.env` file. The one hit, in a library chunk, is supabase-js's own `e.startsWith("sb_secret_")` prefix check, with no value |
| `make lint` | `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 85 source files`; `✓ Types generated successfully` |
| `make test` | web `Tests  80 passed (80)`; the full list is in the deploy-workflows record |

The anon-key placeholder appears in the client bundle, which shows the build arguments reach it.

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| The web bundle contains only `NEXT_PUBLIC_*` values, and the image contains no secret and no `.env` file (TC-355, TC-434 repository half) | verified | The image and bundle scans above |
| `docker compose up api web` serves both images, and `make smoke URL=http://localhost:8000` passes (NFR-035, TC-338) | verified | The compose run above |
| Standalone build, `.next/static` and `public` copied, non-root user, `PORT=3000`, `HOSTNAME=0.0.0.0` (A1 §4.3, §8.3) | verified | The container checks above |
| The staging web page loads from the deployed image (US-002 AC1, TC-437) | not verified | Needs AWS; verified from the first deploy run after merge (IMP-299) |

## Narrowed changes

None in this part.

## Blockers

None.

## Proposed decisions

- **PD-IMP-218-1 (owner of the root `.dockerignore`):** the card lists this file under Junaid; the run prompt places it in this part. The run prompt was followed. Proposed: update the card.
- **PD-IMP-218-2 (`data/fixtures` kept out):** the root `.dockerignore` also excludes `data/fixtures`, so the API image takes `data/` with one `COPY` and SAMPLE data never reaches a deployed image.

## Open issues

- `BUILD_VERSION` is set in the web image but nothing reads it yet, as the card asks.
- The image is 426MB, most of it the `node:22-slim` base and the traced `node_modules`.
