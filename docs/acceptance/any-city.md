# Any-city mode · acceptance sheet (IMP-733)

Card: IMP-733 (Amendment A2 §12 Batch C3, §13.3). Owner: Nidhi (documents); staging runs by Kirtan. Run: RUN-092, 23 November 2026.

- **State: pending.** No any-city scenario has run on staging. The staging window is Saturday 28 November 2026 (A2 §14), on the final candidate.
- Switch state at the release (CHK-26): **to be recorded at the cutoff** (27 November 2026 23:59 IST, IMD-215). If the switch is OFF, only ACC-23 applies.
- Supporting evidence (not a staging result):
  - E2E-10 `@live` (`apps/web/e2e/live-city.spec.ts`, TC-486, fake providers, MOCK);
  - the switch ON/OFF record [any-city-switch.md](../test-reports/any-city-switch.md) (TC-490);
  - [security-any-city.md](../test-reports/security-any-city.md) (TC-487, TC-488).

## Results

| ID | Scenario (A2 §13.3) | Staging result | Supporting local / CI coverage |
| --- | --- | --- | --- |
| ACC-20 | Switch ON: a signed-in user searches a pre-imported live city, creates a trip and gets an itinerary (Gemini, or rule-based when Gemini fails), with the "Live data" label, OpenStreetMap source badges, the attribution footer and "Price unknown" | pending (Kirtan staging window, 28 Nov) | `live-city.spec.ts` "E2E-10 TC-486: a live city from search to itinerary and costs, with live labels and attribution" (RUN-092 E2E dispatch, job `live`) |
| ACC-21 | A small town returns "not enough data" naming a larger nearby city; no 5xx and no blank screen | pending (Kirtan staging window, 28 Nov) | `live-city.spec.ts` "E2E-10 TC-486: a city with too few places shows the not-enough-data message with its nearby city" |
| ACC-22 | `MOCK_PROVIDER_SCENARIO=timeout` (IMD-33): a live city still gets the labelled rule-based plan | pending (Kirtan staging window, 28 Nov) | `apps/api/tests/api/test_live_generation.py` "test_live_generation_tc_480_provider_timeout_ends_in_the_labelled_rule_based_plan" (IMP-727) |
| ACC-23 | Switch OFF: the primary journey on Ahmedabad is unchanged, the city search is absent, and API-76 to API-79 answer 404 | pending (Kirtan staging window, 28 Nov) | the E2E job `e2e` (switch OFF); TC-461 (`test_any_city_contract.py`); TC-482 (`CitySearch.test.tsx`, `flags.default-off.test.ts`); TC-490 OFF lines |

## CHK-26 (release check)

| Item | Value |
| --- | --- |
| Switch state at the release | to be recorded at the cutoff (27 Nov 2026 23:59 IST) |
| Switch state of the release candidate (IMD-220, 25 Nov 2026) | staging: ON in the 28 Nov window; production: target ON at IMP-801 if the conditions of IMD-220 hold on staging, otherwise OFF ("built but disabled", IMD-215) |
| If ON: demo cities pre-imported (PD-AC-2) | pending; runbook [any-city-staging.md](../guides/any-city-staging.md) |
| If ON: ACC-20 to ACC-23 recorded | pending (table above) |
| If ON: attribution footer visible on every live page | pending (staging); supported by IMP-729 tests and E2E-10 |

When the staging run happens, each row gets the date, the tester, the provider (GEMINI or the MOCK scenario), pass or fail and, for a failure, a defect in [defects.md](../test-reports/defects.md).
