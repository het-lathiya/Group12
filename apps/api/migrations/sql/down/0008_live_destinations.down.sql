-- Down migration 0008_live_destinations. Used by the CI round trip on plain PostgreSQL; production migrations are forward only.
drop index if exists public.ix_destinations_import_requester;
drop index if exists public.ix_destinations_import_active;
drop index if exists public.ux_destinations_provider_ref;
alter table public.destinations drop constraint if exists ck_destinations_nearby_city;
alter table public.destinations drop constraint if exists ck_destinations_failure;
alter table public.destinations drop constraint if exists ck_destinations_tier;
alter table public.destinations
  drop column if exists nearby_city,
  drop column if exists places_usable,
  drop column if exists places_found,
  drop column if exists import_started_at,
  drop column if exists import_requested_by,
  drop column if exists import_failure_reason,
  drop column if exists import_status,
  drop column if exists expires_at,
  drop column if exists imported_at,
  drop column if exists external_ref,
  drop column if exists provider,
  drop column if exists data_tier;
