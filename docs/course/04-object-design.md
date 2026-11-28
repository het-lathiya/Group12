# 04 Object design

| Item | Value |
| --- | --- |
| Course document | 04 of the IT314 set ([index](README.md)), IMD-221 |
| Owner | Manal Patel |
| Built from | `apps/api/app/` at `77e52ba` (every class and function name below is in that code) |
| Related | [03 System design](03-system-design.md), [11 Design diagrams](11-design-diagrams.md), [srs.md §9](../srs.md) (columns, constraints, indexes) |

## 1. How to read the diagrams

The backend is Python, and most routers, services and repositories are **modules of functions**, not classes. The diagrams show such a module as a class with the stereotype `<<module>>`. Its "methods" are the module's public functions. Real classes (Pydantic schemas, SQLAlchemy models, dataclasses, Protocols) are shown with their real names. Python `Protocol` classes are shown as `<<interface>>`.

Arrows: `..>` means "calls or uses", `--|>` means "implements or inherits", and `-->` means "holds a reference to".

## 2. Key interfaces

### 2.1 ModelProvider and its adapters (MOD-B05)

`ModelProvider` (`app/ai/providers/base.py`) is the only way the system talks to a model (CLAUDE.md §8). `app/ai/factory.py` is the only module that imports a concrete adapter.

```mermaid
classDiagram
    class ModelProvider {
        <<interface>>
        +name ProviderName
        +embedding_model_id str
        +generate_itinerary(request) ProviderResult
        +modify_itinerary(request) ProviderResult
        +embed_texts(texts, purpose, titles) EmbeddingResult
        +health_check() HealthStatus
        +get_model_metadata() ModelMetadata
    }
    class GeminiProvider {
        +generation_settings()
        +generate_itinerary(request)
        +embed_texts(texts, purpose, titles)
    }
    class MockProvider {
        +scenario
        +generate_itinerary(request)
        +embed_texts(texts, purpose, titles)
    }
    class FineTunedProvider {
        +generate_itinerary(request)
        +embed_texts(texts, purpose, titles)
    }
    class factory {
        <<module>>
        +get_provider() ModelProvider
        +get_model_provider()
        +breaker_for(provider) CircuitBreaker
        +reset_provider_cache()
        +startup_provider()
    }
    class CircuitBreaker {
        +open_reason
        +state()
        +record_success()
        +record_failure(reason)
    }
    class ProviderResult~T~ {
        +output T
        +usage UsageMetadata
        +finish_reason
        +latency_ms int
        +provider_request_id
        +notes list
    }
    class EmbeddingResult {
        +vectors list
        +model_id str
        +usage UsageMetadata
        +latency_ms int
    }
    class ProviderError
    class ProviderTimeout
    class ProviderRateLimited
    class ProviderQuotaExhausted
    class ProviderConfigError
    class ProviderInvalidOutput
    ModelProvider <|.. GeminiProvider
    ModelProvider <|.. MockProvider
    ModelProvider <|.. FineTunedProvider
    factory ..> GeminiProvider : builds when AI_PROVIDER=GEMINI
    factory ..> MockProvider : builds when MOCK
    factory ..> FineTunedProvider : builds when FINETUNED_MODEL
    factory --> CircuitBreaker
    ModelProvider ..> ProviderResult
    ModelProvider ..> EmbeddingResult
    ProviderError <|-- ProviderTimeout
    ProviderError <|-- ProviderRateLimited
    ProviderError <|-- ProviderQuotaExhausted
    ProviderError <|-- ProviderConfigError
    ProviderError <|-- ProviderInvalidOutput
```

The other error types in `app/ai/errors.py` are `ProviderUnavailable`, `ProviderAuthError` and `ProviderBadRequest`. Each carries a `failure_reason` from the `ai_generations` check list (IMP-110). The shared contracts are in `app/schemas/ai.py`: `GenerationRequest` (gr-1), `GroundedGenerationRequest` (gr-2), `ItineraryOutput` (io-1), `GroundedItineraryOutput` (io-2), `ContextPassage`, `ShortlistPlace` and `ModificationRequest`.

### 2.2 Live-data providers (MOD-B19, Amendment A2)

```mermaid
classDiagram
    class GeocodingProvider {
        <<interface>>
        +search(q) list~GeoCandidate~
        +lookup(osm_ref) GeoPlace
    }
    class PlacesProvider {
        <<interface>>
        +fetch(bbox) list~OsmElement~
        +largest_city_near(lat, lon, radius_km) str
    }
    class GuideSourceProvider {
        <<interface>>
        +fetch(name, lat, lon) list~WikiSection~
    }
    class NominatimGeocoder
    class OverpassPlaces
    class MediaWikiGuides
    class FakeGeocoder
    class FakePlaces
    class FakeGuides
    class GuardedGeocoder {
        +search(q)
        +lookup(osm_ref)
    }
    class GuardedPlaces {
        +fetch(bbox)
        +largest_city_near(lat, lon, radius_km)
    }
    class GuardedGuides {
        +fetch(name, lat, lon)
    }
    class Throttle {
        +slot()
    }
    class LiveProviders {
        +geocoder GeocodingProvider
        +places PlacesProvider
        +guides GuideSourceProvider
    }
    class livedata_factory {
        <<module>>
        +get_providers() LiveProviders
        +get_geocoder()
        +get_places_provider()
        +get_guide_provider()
        +reset_cache()
    }
    GeocodingProvider <|.. NominatimGeocoder
    GeocodingProvider <|.. FakeGeocoder
    GeocodingProvider <|.. GuardedGeocoder
    PlacesProvider <|.. OverpassPlaces
    PlacesProvider <|.. FakePlaces
    PlacesProvider <|.. GuardedPlaces
    GuideSourceProvider <|.. MediaWikiGuides
    GuideSourceProvider <|.. FakeGuides
    GuideSourceProvider <|.. GuardedGuides
    GuardedGeocoder --> GeocodingProvider : inner
    GuardedPlaces --> PlacesProvider : inner
    GuardedGuides --> GuideSourceProvider : inner
    GuardedGeocoder --> Throttle
    GuardedPlaces --> Throttle
    GuardedGuides --> Throttle
    livedata_factory ..> LiveProviders : LIVE_DATA_PROVIDER = LIVE or FAKE
```

The data classes in `app/livedata/providers/base.py` are `BBox`, `GeoCandidate`, `GeoPlace`, `OsmElement` and `WikiSection`. The errors are `LiveDataError`, `LiveDataUnavailable`, `LiveDataRateLimited` and `LiveDataTimeout`. The fakes are refused outside `APP_ENV` local and test (`_build_fake` raises `ConfigError`).

### 2.3 Other interfaces

| Interface | File | Used by |
| --- | --- | --- |
| `Located`, `RoutablePlace` (Protocols) | `app/routing/service.py` | `RoutingService.travel`, `travel_time` |
| `RankablePlace`, `Rankable` (Protocols) | `app/generation/ranking.py` | `rank`, `rank_shortlist` over generation and alternatives candidates |
| `PricedPlace` (Protocol) | `app/budget/engine.py` | `item_cost`, `compute_costs` |
| `Planner` (Protocol) | `app/evaluation/run.py` | `RuleBasedPlanner` and provider runs of the evaluation harness |
| `SigningKeySource` | `app/auth/tokens.py` | `TokenVerifier` (JWKS or HS256) |

## 3. Class diagrams per backend module

### 3.1 core and auth (MOD-B01, MOD-B02)

```mermaid
classDiagram
    class Settings {
        +app_env
        +ai_provider
        +features_disabled
        +live_data_provider
    }
    class config {
        <<module>>
        +load_settings() Settings
        +get_settings() Settings
        +check_settings(settings)
    }
    class DomainError
    class Unauthenticated
    class NotFound
    class StalePlan
    class GenerationInProgress
    class RateLimited
    class QuotaReached
    class ServiceUnavailable
    class ValidationFailed
    class InvalidEdit
    class auth_router {
        <<module>>
        +get_me()
        +update_me()
    }
    class auth_service {
        <<module>>
        +get_or_create_profile()
        +get_profile()
        +update_profile()
        +ai_notice_acknowledged()
    }
    class auth_repository {
        <<module>>
        +insert_if_absent()
        +mirror_auth_user()
        +get()
        +update_profile()
    }
    class deps {
        <<module>>
        +verified_claims()
        +db_session()
        +current_user()
    }
    class TokenVerifier {
        +verify(token) TokenClaims
    }
    class TokenClaims
    class Profile_schema["Profile (auth/schemas.py)"]
    class ProfilePatch
    class Profile_orm["Profile (db/models/profiles.py)"]
    DomainError <|-- Unauthenticated
    DomainError <|-- NotFound
    DomainError <|-- StalePlan
    DomainError <|-- GenerationInProgress
    DomainError <|-- RateLimited
    DomainError <|-- QuotaReached
    DomainError <|-- ServiceUnavailable
    DomainError <|-- ValidationFailed
    DomainError <|-- InvalidEdit
    config ..> Settings
    deps ..> TokenVerifier
    TokenVerifier ..> TokenClaims
    auth_router ..> deps
    auth_router ..> auth_service
    auth_service ..> auth_repository
    auth_repository ..> Profile_orm
    auth_router ..> Profile_schema
    auth_router ..> ProfilePatch
```

`app/core/errors.py` also defines `Conflict`, `Internal` and `EndpointNotImplemented`. `register_error_handlers` maps every `DomainError` to the error envelope (`ErrorEnvelope` in `app/schemas/common.py`).

### 3.2 trips (MOD-B03)

```mermaid
classDiagram
    class trips_router {
        <<module>>
        +create_trip()
        +list_trips()
        +get_trip()
        +update_trip()
        +delete_trip()
        +duplicate_trip()
        +save_preferences()
        +get_preferences()
        +save_place()
        +unsave_place()
        +list_saved_places()
    }
    class trips_service {
        <<module>>
        +create_trip()
        +get_trip()
        +update_trip()
        +list_trips()
        +save_preferences()
        +delete_trip()
        +duplicate_trip()
        +purge_deleted_trips()
        +ensure_not_archived()
    }
    class trips_domain {
        <<module>>
        +validate_trip()
        +validate_dates()
        +validate_budget()
        +validate_destination()
        +plan_affected()
    }
    class preference_mapping {
        <<module>>
        +map_preferences() MappedPreferences
        +field_effects()
    }
    class trips_repository {
        <<module>>
        +insert_trip()
        +get_owned()
        +list_owned()
        +upsert_preferences()
        +replace_must_visit()
        +mark_preferences_saved()
        +soft_delete()
        +insert_copy()
        +purge_deleted()
    }
    class TripIn
    class TripPatch
    class TripOut
    class TripStatus {
        <<enumeration>>
        DRAFT
        READY
        ARCHIVED
    }
    class PreferencesIn
    class PreferencesOut
    class TripDraft
    class MappedPreferences {
        +HardFilters
        +RankingWeights
        +PaceLimits
    }
    class Trip {
        +id
        +user_id
        +destination_id
        +status
        +plan_revision
        +plan_stale
        +deleted_at
    }
    class TripPreferences
    class TripPlace {
        +relation
    }
    trips_router ..> trips_service
    trips_service ..> trips_domain
    trips_service ..> trips_repository
    trips_service ..> preference_mapping
    trips_domain ..> TripDraft
    preference_mapping ..> MappedPreferences
    trips_repository ..> Trip
    trips_repository ..> TripPreferences
    trips_repository ..> TripPlace
    trips_router ..> TripIn
    trips_router ..> TripPatch
    trips_router ..> TripOut
    trips_router ..> PreferencesIn
    trips_router ..> PreferencesOut
    TripOut --> TripStatus
```

### 3.3 places, curated and live (MOD-B04)

```mermaid
classDiagram
    class places_router {
        <<module>>
        +list_destinations()
        +search_places()
        +get_place()
    }
    class live_router {
        <<module>>
        +search_cities()
        +resolve_city()
        +get_import_status()
        +get_destination()
    }
    class places_service {
        <<module>>
        +list_destinations()
        +search_places()
        +get_place()
        +ensure_data_source()
        +claim_live_import()
        +store_live_places()
        +record_live_insufficient_data()
        +complete_live_import()
        +fail_live_import()
        +reap_stale_live_imports()
    }
    class live_service {
        <<module>>
        +search()
        +resolve() ResolveResult
        +import_state()
        +destination_detail()
    }
    class live_jobs {
        <<module>>
        +submit()
        +run_import()
        +reap_imports_forever()
    }
    class import_pipeline {
        <<module>>
        +read_destination()
        +prepare()
        +load() LoadReport
        +run()
    }
    class quality_gate {
        <<module>>
        +check() GateResult
    }
    class places_repository {
        <<module>>
        +search_places(filters PlaceFilters)
        +active_place_detail()
        +upsert_places()
        +deactivate_places_except()
        +claim_live_import()
        +finish_live_import()
        +insert_live_destination()
    }
    class Destination_orm["Destination (ORM)"]
    class Place
    class DataSource
    class PlaceOpeningHours
    class PlaceOut
    class PlaceSummary
    class CitySearchOut
    class CityCandidate
    class ResolveCityIn
    class LiveDestinationOut
    class ImportState
    class DestinationDetailOut
    class Attribution
    places_router ..> places_service
    live_router ..> live_service
    live_service ..> live_jobs
    live_jobs ..> places_service
    places_service ..> places_repository
    import_pipeline ..> quality_gate
    places_repository ..> Destination_orm
    places_repository ..> Place
    places_repository ..> DataSource
    places_repository ..> PlaceOpeningHours
    places_router ..> PlaceOut
    places_router ..> PlaceSummary
    live_router ..> CitySearchOut
    CitySearchOut --> CityCandidate
    live_router ..> ResolveCityIn
    live_router ..> LiveDestinationOut
    LiveDestinationOut --> ImportState
    live_router ..> DestinationDetailOut
    DestinationDetailOut --> Attribution
```

`app/places/vocabulary.py` holds the enumerations `Category`, `OfferedCategory`, `Tag`, `SuitabilityFlag` and `VerificationStatus`. `app/places/live_import.py` is the import CLI (`main`, `import_destination`, `CannotImportError`).

### 3.4 generation (MOD-B06)

```mermaid
classDiagram
    class generation_router {
        <<module>>
        +start_generation()
        +get_generation()
        +regenerate_day()
        +regenerate_itinerary()
    }
    class generation_service {
        <<module>>
        +check_daily_cap()
        +start_generation()
        +start_regeneration()
        +get_generation()
    }
    class jobs {
        <<module>>
        +submit()
        +run()
        +reap_forever()
    }
    class pipeline {
        <<module>>
        +run(job)
        +assess()
        +repair_call()
        +run_fallback()
        +save()
        +recalculate()
    }
    class Job
    class Assessed {
        +usable()
        +errors_remain()
    }
    class request_builder {
        <<module>>
        +build()
        +build_generation_request()
        +ground()
        +quote_notes()
    }
    class retrieval {
        <<module>>
        +retrieve_candidates()
        +semantic_retrieval()
        +ranked_shortlist()
        +apply_filters()
    }
    class ranking {
        <<module>>
        +build_context() RankingContext
        +score() ScoreParts
        +rank()
        +rank_shortlist() Shortlist
    }
    class fallback_planner {
        <<module>>
        +plan_rule_based()
    }
    class records {
        <<module>>
        +check_transition()
        +request_hash()
        +usage_columns()
    }
    class outcomes {
        <<module>>
        +resolve() Outcome
        +resolve_open_breaker()
    }
    class generation_repository {
        <<module>>
        +create_queued()
        +mark_running()
        +mark_validating()
        +mark_repairing()
        +complete()
        +fail()
        +fail_stale()
        +daily_usage()
    }
    class GenerationStartIn
    class RegenerateIn
    class GenerationOut
    class AiGeneration {
        +status
        +outcome
        +failure_reason
        +scope
        +retrieval_mode
    }
    generation_router ..> generation_service
    generation_service ..> generation_repository
    generation_service ..> jobs
    jobs ..> pipeline
    pipeline --> Job
    pipeline ..> Assessed
    pipeline ..> request_builder
    pipeline ..> retrieval
    pipeline ..> fallback_planner
    pipeline ..> outcomes
    retrieval ..> ranking
    generation_repository ..> records
    generation_repository ..> AiGeneration
    generation_router ..> GenerationStartIn
    generation_router ..> RegenerateIn
    generation_router ..> GenerationOut
```

Also in the module: `grouping.py` (`group_days`), `schedule.py` (`recalculate`, `SchedulablePlace`, `Routing`), `presets.py` (`pace_limits`, `meal_slots`) and `samples.py` (`list_samples`, `load_sample`).

### 3.5 validation and budget (MOD-B07, MOD-B09)

```mermaid
classDiagram
    class output_check {
        <<module>>
        +check_output() OutputCheckResult
        +apply_limits()
    }
    class validator {
        <<module>>
        +validate() list~Finding~
        +summary() ValidationSummary
    }
    class rules {
        <<module>>
        +overlap()
        +transfer_too_short()
        +must_visit_missing()
        +unknown_place()
        +outside_trip_dates()
        +opening_hours()
        +day_length()
        +budget_conflicts()
    }
    class repair {
        <<module>>
        +repair() Repaired
        +scope_for() RepairScope
    }
    class ValidationContext
    class PlanDay
    class PlanItem
    class Finding
    class ValidationSummary
    class validation_router {
        <<module>>
        +validate_itinerary()
    }
    class budget_router {
        <<module>>
        +get_costs()
        +update_budget_settings()
    }
    class budget_service {
        <<module>>
        +get_costs()
        +update_budget_settings()
    }
    class engine {
        <<module>>
        +compute_costs(inputs) CostSummary
        +item_cost()
        +to_minor()
        +half_up()
    }
    class budget_repository {
        <<module>>
        +get_settings()
        +upsert_settings()
        +save_settings()
    }
    class CostSummaryOut
    class BudgetSettingsPatch
    class BudgetSettings
    validator ..> rules
    rules ..> ValidationContext
    rules ..> PlanDay
    PlanDay --> PlanItem
    validator ..> Finding
    validator ..> ValidationSummary
    repair ..> validator
    budget_router ..> budget_service
    budget_service ..> engine
    budget_service ..> budget_repository
    budget_repository ..> BudgetSettings
    budget_router ..> CostSummaryOut
    budget_router ..> BudgetSettingsPatch
```

### 3.6 itinerary (MOD-B08)

```mermaid
classDiagram
    class itinerary_router {
        <<module>>
        +latest_itinerary()
        +get_itinerary()
        +add_item()
        +update_item()
        +delete_item()
        +list_alternatives()
        +replace_item()
        +trip_summary()
        +list_versions()
        +create_version()
        +restore_version()
    }
    class itinerary_service {
        <<module>>
        +save_generated_plan() SavedPlan
        +save_regenerated_plan()
        +get_itinerary()
        +revalidate()
        +trip_summary()
        +cost_summary()
    }
    class edits {
        <<module>>
        +apply_edit()
        +patch_item()
        +remove_item()
        +add_item()
        +alternatives()
        +replace_item()
    }
    class versions {
        <<module>>
        +snapshot_current()
        +snapshot_before_regeneration()
        +list_versions()
        +save_named()
        +restore()
    }
    class itinerary_repository {
        <<module>>
        +lock_trip()
        +replace_plan()
        +insert_warnings()
        +bump_revision()
        +generation_active()
        +insert_version()
    }
    class Move
    class Retime
    class Remove
    class Add
    class Lock
    class Replace
    class Restore
    class ItineraryOut
    class EditResultOut
    class ItemPatchIn
    class ItemAddIn
    class ReplaceIn
    class VersionOut
    class SourceRef
    class ItineraryDay
    class ItineraryItem
    class ItineraryWarning
    class ItineraryVersion
    itinerary_router ..> itinerary_service
    itinerary_router ..> edits
    itinerary_router ..> versions
    edits ..> itinerary_service : revalidate
    edits ..> itinerary_repository
    versions ..> itinerary_repository
    itinerary_service ..> itinerary_repository
    edits ..> Move
    edits ..> Retime
    edits ..> Remove
    edits ..> Add
    edits ..> Lock
    edits ..> Replace
    versions ..> Restore
    itinerary_repository ..> ItineraryDay
    itinerary_repository ..> ItineraryItem
    itinerary_repository ..> ItineraryWarning
    itinerary_repository ..> ItineraryVersion
    itinerary_router ..> ItineraryOut
    itinerary_router ..> EditResultOut
    itinerary_router ..> ItemPatchIn
    itinerary_router ..> ItemAddIn
    itinerary_router ..> ReplaceIn
    itinerary_router ..> VersionOut
    ItineraryOut ..> SourceRef
```

### 3.7 rag, routing and evaluation (MOD-B18, MOD-B10, MOD-B15)

```mermaid
classDiagram
    class rag_service {
        <<module>>
        +index() IndexReport
        +retrieve() RetrievalResult
        +resolve_sources()
        +index_live_destination() LiveIndexReport
        +embed_destinations()
    }
    class rag_repository {
        <<module>>
        +save_document()
        +pending_chunks()
        +store_embeddings()
        +best_place_chunks()
        +top_guide_chunks()
        +source_rows()
    }
    class chunker {
        <<module>>
        +chunk_guide() list~Chunk~
    }
    class documents {
        <<module>>
        +place_document() CorpusDocument
        +guide_document() CorpusDocument
    }
    class guides {
        <<module>>
        +check_guide() list~GuideFinding~
    }
    class mmr {
        <<module>>
        +select()
    }
    class live_guides {
        <<module>>
        +build_guides() LiveGuideBuild
        +cap_guides()
    }
    class RetrievalContext
    class RagDocument
    class RagChunk
    class RoutingService {
        +travel()
    }
    class OrsClient {
        +route() Route
    }
    class RouteCacheRepository {
        +get()
        +upsert()
    }
    class estimate {
        <<module>>
        +estimate() TravelEstimate
        +haversine_m()
    }
    class RouteCache
    class evaluation_run {
        <<module>>
        +evaluate()
        +evaluate_retrieval()
        +score_case()
    }
    class RuleBasedPlanner
    rag_service ..> rag_repository
    rag_service ..> documents
    rag_service ..> chunker
    rag_service ..> guides
    rag_service ..> mmr
    rag_service ..> live_guides
    rag_service ..> RetrievalContext
    rag_repository ..> RagDocument
    rag_repository ..> RagChunk
    RagDocument "1" --> "many" RagChunk
    RoutingService --> RouteCacheRepository
    RoutingService --> OrsClient
    RoutingService ..> estimate : when ORS is unavailable
    RouteCacheRepository ..> RouteCache
    evaluation_run ..> RuleBasedPlanner
```

## 4. ORM models (`app/db/models/`)

One file per owning module (IMP-106). Column names are the SQL column names.

```mermaid
classDiagram
    class Profile {
        id
        display_name
        home_country
        preferred_currency
        ai_notice_ack_at
        default_preferences
    }
    class Trip {
        id
        user_id
        destination_id
        title
        status
        start_date
        end_date
        num_days
        plan_revision
        plan_stale
        deleted_at
    }
    class TripPreferences {
        trip_id
        interests
        pace
        budget_priority
        transport_pref
        notes
    }
    class TripPlace {
        trip_id
        place_id
        relation
    }
    class Destination {
        id
        slug
        data_tier
        provider
        external_ref
        import_status
        is_active
    }
    class Place {
        id
        destination_id
        source_id
        category
        price_label
        hours_label
        is_active
    }
    class DataSource {
        id
        name
        licence
        attribution_text
    }
    class PlaceOpeningHours {
        place_id
        weekday
        open_time
        close_time
    }
    class BudgetSettings {
        trip_id
        transport_allowance_per_day
        stay_budget_per_night
        contingency_pct
    }
    class AiGeneration {
        id
        trip_id
        provider
        scope
        status
        outcome
        failure_reason
    }
    class ItineraryDay {
        id
        trip_id
        day_number
        source_generation_id
    }
    class ItineraryItem {
        id
        day_id
        place_id
        start_time
        origin
        is_locked
        cost_label
        source_chunk_ids
    }
    class ItineraryWarning {
        code
        severity
        plan_revision
    }
    class ItineraryVersion {
        version_no
        reason
        snapshot
    }
    class RouteCache {
        from_place_id
        to_place_id
        mode
        travel_source
    }
    class RagDocument {
        doc_key
        kind
        destination_id
    }
    class RagChunk {
        document_id
        chunk_index
        embedding
        embedding_model_id
    }
    Profile "1" --> "many" Trip
    Destination "1" --> "many" Trip
    Destination "1" --> "many" Place
    DataSource "1" --> "many" Place
    Place "1" --> "many" PlaceOpeningHours
    Trip "1" --> "0..1" TripPreferences
    Trip "1" --> "many" TripPlace
    Trip "1" --> "0..1" BudgetSettings
    Trip "1" --> "many" AiGeneration
    Trip "1" --> "many" ItineraryDay
    ItineraryDay "1" --> "many" ItineraryItem
    Trip "1" --> "many" ItineraryWarning
    Trip "1" --> "many" ItineraryVersion
    Destination "1" --> "many" RagDocument
    RagDocument "1" --> "many" RagChunk
```

All models inherit `Base` (`app/db/models/base.py`). The full column list, constraints and indexes are in [srs.md §9](../srs.md).

## 5. Design patterns used

| Pattern | Where in the code | Why |
| --- | --- | --- |
| Strategy, adapter | `ModelProvider` with `GeminiProvider`, `MockProvider`, `FineTunedProvider`; the three live-data Protocols with OSM, MediaWiki and fake implementations | The pipeline does not change when the provider changes (US-034, IMP-110) |
| Factory | `app/ai/factory.py` `get_provider`; `app/livedata/factory.py` `get_providers` | Only the factory imports a concrete adapter (import-linter contract 3) |
| Decorator or proxy | `GuardedGeocoder`, `GuardedPlaces`, `GuardedGuides` wrap an `inner` provider with `Throttle` and `CircuitBreaker` | Spacing and breakers without changing the adapters (A2 §7.3) |
| Circuit breaker | `app/ai/breaker.py` `CircuitBreaker` | Stops calls after consecutive failures (IMD-146, A2 §7.1) |
| Repository | every `repository.py`; `RouteCacheRepository` | SQL stays out of services and routers; every owned query takes `user_id` |
| Unit of work | `app/db/session.py` `transaction()` | One transaction per edit and per generation save (CLAUDE.md §7) |
| State machine | `app/generation/records.py` `TRANSITIONS`, `check_transition` | Only allowed generation status changes, see [11 Design diagrams](11-design-diagrams.md) |
| Command | `app/itinerary/edits.py` `Move`, `Retime`, `Remove`, `Add`, `Lock`, `Replace`, `LockAndEdit`, `Restore` passed to `apply_edit` | One edit path that recalculates and revalidates |
| Dependency injection | FastAPI `Depends`: `current_user`, `db_session`, `get_model_provider`, `get_submit`, `get_providers` | Tests override providers and job runners |
| Template registry | `app/ai/prompts/registry.py` `PromptTemplate`, `load`, `load_all` | Versioned prompts (`v1` to `v4`), one active by `PROMPT_TEMPLATE_VERSION` |
| Middleware | `app/core/request_id.py` `RequestIdMiddleware` | A request ID on every log line and error |
| Test double (fake) | `MockProvider` scenarios, `FakeGeocoder`, `FakePlaces`, `FakeGuides` | Tests never call Gemini or the live services |
