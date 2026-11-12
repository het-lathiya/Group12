# RUN-059 · fallback-wording part

- Run id: RUN-059 (grouped, with the RUN-059 addendum)
- Owner: Krrish (Assassin-byte)
- Status: PR open
- Base commit: 8c3997b
- Branch: chore/RUN-059-decisions-and-fixes
- Traces to: IMD-154 (PD-IMP-403-1), §7.5.6, §7.8; flaky web tests reported in RUN-060 and RUN-062 (IMP-409-move-controls open issues)

## Changed files

- `apps/web/components/generation/FallbackNotice.tsx`: the notice text is now exactly "Built by rules because the AI service was unavailable or its answer failed checks" (§7.8).
- `apps/web/tests/unit/generation/FallbackNotice.test.tsx`, `apps/web/tests/unit/itinerary/ItineraryPage.test.tsx`: the same string in their assertions. `grep -rn "failed checks" apps/web` (without `node_modules` and `.next`) now finds only the new wording, in these three files.
- `apps/web/tests/unit/generation/PrivacyNotice.test.tsx` (addendum): two changes, see "Flaky tests".
- `apps/web/tests/unit/trips/TripWizard.test.tsx` (addendum): TC-068 gets its own 15 s limit with the reason in a comment, see "Flaky tests".
- `docs/progress/parts/RUN-059-fallback-wording.md`: this record.

The TC-384 checklist in `IMP-412-whole-task.md` is not touched (Krrish's own review).

## Flaky tests: causes found

The machine during this run: 16 cores and 7 GB of memory (about 2 GB free), with load averages between 15 and 35. A filesystem-wide `bfs / -name pg_ctl` search started at 10:50, before this run and not by it, held I/O the whole time. It was left running because this run did not start it.

1. **PrivacyNotice, a real timing fault in the test.** Six cases waited for the exact text "Elapsed 0:00". The progress view counts real seconds (`setInterval` of 1 s in `GenerationProgress`), so that text holds only for the first second after the view mounts. A slow run that looks later never sees it. `GenerationProgress.test.tsx` fakes that interval; `PrivacyNotice.test.tsx` used real timers. Fix: wait for any elapsed value (`/^Elapsed \d+:\d{2}$/`). This is the progress view being up, which is what these cases need.
2. **PrivacyNotice, the case that failed in every loaded run: "shows the approved text and terms link…".** It is the file's first test. Its first `findByRole` heading query also pays for the first render: 345 ms alone, against 44 ms for the same query in the next test. Under load it passed the 1 s default of `findBy*` (failures at 1.4 s, 3.2 s and 8.4 s in the first loop). This cause is environment speed plus a one-time warm-up, not shared state or a missing await. Fix: the heading query gets 4 s, inside the test's 5 s limit, with the reason in a comment.
3. **TripWizard TC-068: environment speed, proven.** Alone it takes about 1.5 s. Timing each step: typing in `fillDetails` about 0.56 s, then the place search and its result about 0.39 s. There is no shared state (each test builds a new fake API, a new QueryClient and a new user-event instance), no fake timers and no missing await.
   - Switching user-event to `delay: null` changed nothing measurable (1568 ms against 1538 ms), so keystroke timers are not the cost. That change was reverted.
   - It hit 5 s only in runs where unrelated tests took 9 to 35 s; in one of them, `WarningsPanel` took 35.5 s.
   - Fix: a 15 s limit for this one test, with the reason in a comment. No retry and no skip.

**Not fixed (outside this part's files), reported.** `GenerationProgress.test.tsx` cascades: when its first test times out on a starved machine, the next tests fail in 10 to 30 ms, their render shows an empty `<div />` and `getByRole("button", { name: "Generate with AI" })` finds nothing. The likely cause is that the timed-out test keeps running and holds an open `act()` scope, which delays the next test's render. A fix belongs in that file.

## 10 runs of make test-web

On the final code, `for i in 1..10; make test-web`: **4 of 10 passed** (runs 1, 6, 8, 10).

| Run | Result | Slowest failing test | PrivacyNotice or TripWizard failures |
| --- | --- | --- | --- |
| 1 | 186 passed | none | none |
| 2 | 5 failed, 181 passed | 14392 ms | none (AuthForms, BudgetSettingsForm, AuthGuard) |
| 3 | 2 failed, 184 passed | 5413 ms | none (FallbackNotice, dashboard) |
| 4 | 28 failed, 158 passed | 48937 ms | 3 PrivacyNotice cases, alongside 8 other files |
| 5 | 9 failed, 177 passed | 25959 ms | TC-068 (15 s), TC-076, 1 PrivacyNotice case, alongside 6 other files |
| 6 | 186 passed | none | none |
| 7 | 2 failed, 184 passed | 5095 ms | none (FallbackNotice, dashboard) |
| 8 | 186 passed | none | none |
| 9 | 12 failed, 174 passed | 43384 ms | PrivacyNotice first case, alongside 5 other files |
| 10 | 186 passed | none | none |

Before these changes, in a first loop of 5 runs (only the wording change applied), the PrivacyNotice first case failed in 5 of 5. After them it failed in 2 of 10 (runs 4 and 9), and TC-068 in 1 of 10 (run 5). Each of those runs had unrelated tests over 25 s. The failures spread over almost every test file, which points to the starved machine, not to these two files. The loop does not prove the suite stable on this machine. It needs a run on a quiet machine or in CI, where the `unit` job runs `make test-web`.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-web ARGS='FallbackNotice'` | `Tests  9 passed (9)` |
| `npx vitest run tests/unit/generation/PrivacyNotice.test.tsx` | `Tests  8 passed (8)` |
| `npx vitest run tests/unit/trips/TripWizard.test.tsx` | `Tests  14 passed (14)` |
| `make test-web` × 10 (final code) | 4 of 10 passed (table above) |
| `npx prettier --check components tests` (apps/web) | clean |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| IMD-154: FallbackNotice shows the §7.8 text exactly; every copy changed | verified | `FallbackNotice.test.tsx`, `ItineraryPage.test.tsx`; grep |
| TC-068 stable | not verified on this machine | cause shown to be environment speed; explicit limit with reason; 1 failure in 10 loaded runs |
| PrivacyNotice failing case stable | not verified on this machine | real-timer race fixed; first-query budget raised with reason; 2 failures in 10 loaded runs, against 5 in 5 before |
| `make test-web` 10 runs recorded | verified | 4 of 10 passed |

## Blockers

None for the wording. Stability evidence needs a quiet machine or CI.

## Open issues

- `GenerationProgress.test.tsx` cascade after a timed-out first test (above).
- On machines with little free memory, `make test-web` runs one jsdom worker per core. The team may want a lower worker count for local runs, which is a Makefile or Vitest configuration change outside this part.

## Proposed decisions

None.
