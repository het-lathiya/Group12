-- Migration 0008_live_destinations (any-city mode, Amendment A2 §4.1; IMP-721). Live destination columns on destinations.
-- Source of truth for the schema (IMD-01). Executed by apps/api/migrations/versions/0008_live_destinations.py.
-- Only nullable or defaulted columns are added, so the migration is applied in every environment whatever the switch
-- any_city_mode (A2 §3.3). No new table, no column on places, no change to data_sources or to RLS: destinations keeps
-- the RLS and grants of 0005. Existing rows read data_tier = 'curated' from the default.
-- Writer: MOD-B04 (the places module) stays the only writer of destinations.

alter table public.destinations
  add column data_tier             text not null default 'curated'
                                   check (data_tier in ('curated','live')),
  add column provider              text
                                   check (provider in ('osm')),                       -- null for curated
  add column external_ref          text
                                   check (external_ref ~ '^[NWR][0-9]{1,12}$'),      -- Nominatim OSM reference, e.g. R1234567
  add column imported_at           timestamptz,                                       -- last successful import finished
  add column expires_at            timestamptz,                                       -- imported_at + LIVE_DATA_TTL_DAYS
  add column import_status         text
                                   check (import_status in ('queued','running','completed','insufficient_data','failed')),
  add column import_failure_reason text
                                   check (import_failure_reason in ('provider_unavailable','rate_limited','timeout','internal')),
  add column import_requested_by   uuid references public.profiles(id) on delete set null,  -- daily cap only; never returned
  add column import_started_at     timestamptz,                                       -- set when the job takes the row
  add column places_found          integer check (places_found >= 0),                 -- elements returned by Overpass
  add column places_usable         integer check (places_usable >= 0),                -- passed normalisation and dedupe
  add column nearby_city           text
                                   check (char_length(nearby_city) between 1 and 120);

-- A curated row carries no live fields; a live row carries provider, reference and import status and is never SAMPLE.
alter table public.destinations
  add constraint ck_destinations_tier check (
    (data_tier = 'curated' and provider is null and external_ref is null and import_status is null)
    or (data_tier = 'live' and provider is not null and external_ref is not null and import_status is not null
        and is_sample = false)
  );

-- A failure reason is set exactly when the import failed.
alter table public.destinations
  add constraint ck_destinations_failure check (
    import_status is null or ((import_status = 'failed') = (import_failure_reason is not null))
  );

-- nearby_city is set only with insufficient_data (A2 §4.1, §6.4).
alter table public.destinations
  add constraint ck_destinations_nearby_city check (
    nearby_city is null or import_status = 'insufficient_data'
  );

-- One row per OSM settlement: duplicate resolves meet the same row.
create unique index ux_destinations_provider_ref on public.destinations (provider, external_ref)
  where external_ref is not null;

-- The import reaper scans active imports only.
create index ix_destinations_import_active on public.destinations (import_status)
  where import_status in ('queued','running');

-- The per-user daily import cap.
create index ix_destinations_import_requester on public.destinations (import_requested_by, import_started_at)
  where import_requested_by is not null;
