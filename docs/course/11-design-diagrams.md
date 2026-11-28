# 11 Design diagrams: activity and state

| Item | Value |
| --- | --- |
| Course document | 11 of the IT314 set ([index](README.md)), IMD-221 |
| Owner | Manal Patel |
| Built from | `apps/api/app/` and `apps/web/` at `77e52ba`; status values from migrations `0003`, `0004` and `0008` |
| Related | [03 System design](03-system-design.md) (sequence diagrams), [04 Object design](04-object-design.md) |

Activity diagrams are drawn as Mermaid flowcharts. Rounded nodes are start and end points, and diamonds are decisions.

## 1. Activity: create a trip, generate, edit, view costs

Screens: `/trips/new` (`TripWizard`), `/trips/{tripId}/generate`, `/trips/{tripId}/itinerary`, `/trips/{tripId}/costs`. Endpoints are named by their API IDs.

```mermaid
flowchart TD
    start([Signed-in traveller on /dashboard]) --> new[Open /trips/new]
    new --> details[Step Details: title, destination, dates, travellers, budget]
    details --> v1{Valid? trips/domain.py validate_trip}
    v1 -- no --> err1[422 VALIDATION_ERROR shown on the fields] --> details
    v1 -- yes --> draft[API-07 creates the trip with status draft]
    draft --> prefs[Step Preferences: interests, pace, budget priority, transport, notes]
    prefs --> mv[Step Must-visit places]
    mv --> save[API-14 saves preferences and must-visit places; status becomes ready]
    save --> review[Step Review]
    review --> gen[Open /generate; PrivacyNotice acknowledged once]
    gen --> start22[API-22 starts a generation, 202]
    start22 --> cap{Daily cap reached or a job already active?}
    cap -- yes --> e429[429 AI_QUOTA_REACHED or 409 GENERATION_IN_PROGRESS] --> stop1([Stop])
    cap -- no --> poll[GenerationProgress polls API-23]
    poll --> done{Generation status}
    done -- failed: quota or config_error --> offer[Offer Build without AI] --> rb[Rule-based plan saved] --> view
    done -- completed --> view[Itinerary page reads API-24]
    view --> labels[Fallback notice, warnings, AI and source labels shown]
    labels --> edit{Traveller edits?}
    edit -- move, retime, lock --> e26[API-26 with plan_revision]
    edit -- remove --> e27[API-27]
    edit -- add a place --> e25[API-25]
    edit -- replace --> e28[API-28 alternatives then API-29 replace]
    e26 --> tx
    e27 --> tx
    e25 --> tx
    e28 --> tx
    tx{plan_revision current and no generation active?}
    tx -- no --> stale[409 STALE_PLAN or GENERATION_IN_PROGRESS; StalePlanBanner asks to reload] --> view
    tx -- yes --> recalc[One transaction: recalculate times, gaps, costs; revalidate; plan_revision + 1] --> view
    edit -- no more edits --> costs[Open /costs: API-33 CostBreakdown, BudgetAlert]
    costs --> settings{Change budget settings?}
    settings -- yes --> e34[API-34 BudgetSettingsForm] --> costs
    settings -- no --> finish([Summary or versions])
```

Rules shown here come from the code:

- `TripWizard` saves each step before the next one opens. A saved draft reopens at its first incomplete step with `/trips/new?draft=<id>`.
- `trips/repository.py` `mark_preferences_saved` turns a `draft` into `ready` (IMD-25).
- Every edit goes through `itinerary/edits.py` `apply_edit` in one transaction.

## 2. Activity: any-city import (switch `any_city_mode` ON, A2)

```mermaid
flowchart TD
    s([Traveller types a city name in CitySearch]) --> q{2 to 100 characters after trimming?}
    q -- no --> e422[422 VALIDATION_ERROR] --> s
    q -- yes --> api76[API-76 search: cached Nominatim result or one throttled request]
    api76 --> up{Geocoder up and breaker closed?}
    up -- no --> e503[503 SERVICE_UNAVAILABLE] --> s
    up -- yes --> list[Up to 8 settlements shown with tier]
    list --> pick[Traveller picks one]
    pick --> cur{Already a curated destination?}
    cur -- yes --> trip[Continue the trip form with that destination]
    cur -- no --> api77[API-77 resolve osm_ref]
    api77 --> caps{Daily import caps reached?}
    caps -- yes --> e429[429 RATE_LIMITED] --> list
    caps -- no --> exists{Live destination exists?}
    exists -- "yes, completed and not expired, or running" --> r200[200 LiveDestinationOut] --> watch
    exists -- "yes, failed or expired" --> requeue[requeue_live_import, 202] --> job
    exists -- no --> insert[insert_live_destination, import queued, 202] --> job
    job[live_jobs.run_import: claim queued to running] --> fetch[PlacesProvider.fetch bbox]
    fetch --> ok1{Provider answered?}
    ok1 -- "no: timeout, 429, error" --> failed[import failed with a reason]
    ok1 -- yes --> norm[normalise, dedupe, cap]
    norm --> gate{evaluate_gate: at least LIVE_MIN_USABLE_PLACES usable?}
    gate -- no --> insuff[insufficient_data with nearby_city]
    gate -- yes --> store[store_live_places in one transaction]
    store --> guides[index_live_destination: MediaWiki guides into rag_chunks]
    guides --> complete[complete_live_import: is_active true, expires_at set]
    watch[ImportProgress polls API-78]
    complete --> watch
    failed --> watch
    insuff --> watch
    watch --> outcome{Import status}
    outcome -- completed --> trip
    outcome -- insufficient_data --> near[Message names a larger nearby city] --> s
    outcome -- failed --> retry[Error with retry] --> s
    trip --> e([Trip created; generation as in section 1])
```

If the guide source fails, the places are still stored and the import completes without guide documents (IMD-218). A failed refresh of an active live destination keeps its earlier places (IMD-217).

## 3. State: generation job (`ai_generations.status`)

Source: `app/generation/records.py` `TRANSITIONS`, enforced by `check_transition`. The check list is in migration `0004_ai_and_plan.sql`.

```mermaid
stateDiagram-v2
    [*] --> queued: API-22, API-30 or API-31 (202)
    queued --> running
    queued --> failed: reaper (older than 150 s)
    running --> validating: answer parsed (model or rule-based)
    running --> failed: provider_quota_exhausted, config_error, internal
    validating --> repairing: error findings remain
    validating --> completed
    validating --> failed: unresolved_validation
    repairing --> validating
    repairing --> completed
    repairing --> failed
    completed --> [*]
    failed --> [*]
```

| Field | Values (migration 0004) |
| --- | --- |
| `status` | `queued`, `running`, `validating`, `repairing`, `completed`, `failed` |
| `outcome` | `model`, `model_repaired`, `fallback_rule_based`, `failed` |
| `scope` | `full`, `day` (with `scope_day_number`), `edit` |
| `repair_attempts` | 0 or 1 (at most one model repair call) |

`ACTIVE_STATUSES` are `queued`, `running`, `validating` and `repairing`. While one is active, edits answer 409 `GENERATION_IN_PROGRESS`.

## 4. State: trip and draft (`trips.status`, `deleted_at`)

Source: `trips/schemas.py` `TripStatus`, `trips/repository.py` (`insert_trip`, `mark_preferences_saved`, `soft_delete`), `trips/service.py` `update_trip`, `duplicate_trip`, and `itinerary/repository.py` `mark_plan_saved`.

```mermaid
stateDiagram-v2
    [*] --> draft: API-07 create (TripWizard Details step)
    draft --> ready: API-14 preferences saved (mark_preferences_saved)
    draft --> ready: plan saved (mark_plan_saved)
    ready --> archived: API-11 status archived
    draft --> archived: API-11 status archived
    archived --> ready: API-11 status ready, trip has days
    archived --> draft: API-11 status ready, trip has no days
    draft --> deleted: API-12 (deleted_at set)
    ready --> deleted: API-12
    archived --> deleted: API-12
    deleted --> [*]: purge_deleted_trips
```

`deleted` is not a status value. It means `deleted_at` is set, and every trip query filters `deleted_at IS NULL`. API-13 creates a copy that is `ready` when the source has preferences, otherwise `draft` (IMD-25). An archived trip refuses changes (`ensure_not_archived`).

## 5. State: saved itinerary (plan revision and stale flag)

Source: `trips.plan_revision`, `trips.plan_stale`, `itinerary/repository.py` `bump_revision`, `mark_plan_saved`, and `trips/service.py` `update_trip` (FR-011).

```mermaid
stateDiagram-v2
    [*] --> no_plan: trip created (plan_revision 0)
    no_plan --> current: generation saved (plan_revision + 1)
    current --> current: edit API-25 to API-29 (plan_revision + 1)
    current --> stale: trip dates, travellers, budget or destination changed, or preferences saved (plan_stale true)
    stale --> current: regenerate API-30 or API-31 saved (plan_stale false)
    current --> current: version restored API-38 (plan_revision + 1)
```

An edit that sends an old `plan_revision` changes nothing and answers 409 `STALE_PLAN`. `itinerary_versions.reason` records why a snapshot was taken: `generation`, `regeneration`, `edit`, `restore`, `fallback` or `manual`.

## 6. State: live destination import (`destinations.import_status`, A2)

Source: migration `0008_live_destinations.sql`, `places/live_jobs.py`, `places/live_service.py` `_existing`, `places/repository.py` `requeue_live_import`.

```mermaid
stateDiagram-v2
    [*] --> queued: API-77 resolve (new settlement)
    queued --> running: claim_live_import
    queued --> failed: reaper, queued over 600 s
    running --> completed: gate passed, places stored
    running --> insufficient_data: too few usable places
    running --> failed: timeout, rate_limited, provider_unavailable, internal
    running --> failed: reaper, running over 360 s
    failed --> queued: API-77 again (requeue_live_import)
    completed --> queued: API-77 after expires_at (refresh)
    completed --> [*]
    insufficient_data --> [*]
```

A live destination stays `is_active = false` until its first import is `completed`. Before that, API-16 answers 404 for it.
