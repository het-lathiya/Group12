# IMP-314 · guides part

- Run id: RUN-050 (grouped, IMD-121, with IMP-309)
- Owner: Krrish (Assassin-byte)
- Status: PR_OPEN
- Base commit: 1681b41
- Branch: feat/IMP-309-314-itinerary-guides
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-164, US-166; FR-136; NFR-040; IMD-111; TC-450
- Card steps built: 1, 2, 4 (for this part's files)

The guide content was written and reviewed by members. This run only copied the 15 files byte for byte from the operator's folder (`~/data_inputs/ahmedabad_guides/`) and ran the gate. No file was edited.

## Files

All in `data/guides/ahmedabad/`. Each sha256 matches the value taken from the source folder before the copy.

| File | sha256 |
| --- | --- |
| `accessibility.md` | `4cd767c5ee88400d17b0ca627ef9938e00444d7c9d7428b5214e5f8f6f543716` |
| `alcohol-and-the-dry-state.md` | `82b4b9868aedddb33d4eb06ff71976dce05c6c0f6f96ced4de6f85f9f2140653` |
| `day-trips.md` | `c480b5d09949b720352d535445c726e588920bb8114c36f96ce72238bc28d3de` |
| `eating-out.md` | `4257533aaf84fc6011d9a7d049817e525ab6c25517b030d7c0ff745a575ab490` |
| `food-culture.md` | `a13e02316bed47e99b84c9aa7a71f98e8fa1dc2d3f7a14b8bd89713c078c0071` |
| `getting-around.md` | `a683ac9bcc9d0f5199a50f8871b16d7408b693abcc8608a4282ea16f4cd3e843` |
| `health.md` | `0af4fbd744e6f73963b8e6b908c9ab18657e610abe933d453574872be227597b` |
| `heritage-walk-and-dress-code.md` | `9c0e6a37f3480daad33ed3e6fa5f487840748b7d22777cc162c39729f61067bd` |
| `kite-festival-uttarayan.md` | `c78e0112c7e6bea455a2d879e67810b64c3bd983fac0ed31752502abe04f37d2` |
| `navratri-and-garba.md` | `d6d50624e88e68ee212ad1544f41b1d80787f48f13b3cb099edb41fada45a129` |
| `neighbourhoods-and-areas.md` | `67e9384d7c3a78100844fed6c715f98e1e5f31ea432c3cf191fcc75f222be1a8` |
| `old-city-and-pols.md` | `0b720865a1b04226857348abdb31a597b6b751a803812f836b7b8d400a20ebbb` |
| `staying-safe.md` | `79277b70dbd70b85bc48c6e97e7fcfb87789e77afce7464ae3c8b90ed945f4d6` |
| `visiting-akshardham.md` | `c0f47497a756103a63e37599d46095097bcfdf478a87c32ddfc19c79bdd3410a` |
| `weather-and-seasons.md` | `c18399fd1df611789e248f22c934c35becbda2b02d73395b26be632f845dfa63` |

## Commands

On the compose database, with `DATABASE_URL` set to the §4.7 test default, `APP_ENV=test`, `AI_PROVIDER=MOCK` and `DB_AUTH_STUB=true`. `make seed` loads only the SAMPLE fixture by default, so `SEED_DIRS` added the destination.

| Command | Result |
| --- | --- |
| `make db-up`, `make db-bootstrap` | `Container group12-db-1 Healthy`; migrations applied |
| `make seed SEED_DIRS=data/places/ahmedabad` | `seed ahmedabad: places inserted 103, updated 0, unchanged 0, deactivated 0` |
| `make rag-index ARGS='--destination ahmedabad --check --strict'` | exit 0: `rag-index: documents=118 chunks=189 embedded=0 inactive=0 warnings=0 errors=0` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| 8 to 15 guide documents in `data/guides/ahmedabad/` | verified | 15 files |
| Every document passes the strict gate (TC-450, gate half) | verified | the line above, TC-450 |
| Each document is traced to its source by the reviewer (TC-450, review half) | not verified by this run | Malhar's review, recorded in `quality_report.md` and `IMP-314-review.md` |

## Blockers

None.

## Proposed decisions

None.

## Open issues

None.
