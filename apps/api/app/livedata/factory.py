"""Live-data provider factory (Amendment A2 §7.1, §7.4; IMP-723).

``LIVE_DATA_PROVIDER`` chooses the providers: ``FAKE`` builds the offline SAMPLE fakes (local and
test only; refused in staging and production), ``LIVE`` builds the Nominatim, Overpass and
MediaWiki clients. They are built once per process. The places and RAG services take them through
the FastAPI dependencies ``get_geocoder``, ``get_places_provider`` and ``get_guide_provider``,
which tests replace with ``app.dependency_overrides``.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from app.core.config import ConfigError, Settings, get_settings
from app.livedata.providers.base import GeocodingProvider, GuideSourceProvider, PlacesProvider

# The scenario of the fakes the factory builds; tests that need another scenario construct a fake
# themselves or override the dependency.
DEFAULT_FAKE_SCENARIO: Final = "ok"
FAKE_REFUSED: Final = "LIVE_DATA_PROVIDER: FAKE is refused in staging and production"


@dataclass(frozen=True)
class LiveProviders:
    geocoder: GeocodingProvider
    places: PlacesProvider
    guides: GuideSourceProvider


def _build_fake(settings: Settings) -> LiveProviders:
    if settings.app_env not in ("local", "test"):
        raise ConfigError([FAKE_REFUSED])
    from app.livedata.providers.fake import FakeGeocoder, FakeGuides, FakePlaces

    return LiveProviders(
        geocoder=FakeGeocoder(DEFAULT_FAKE_SCENARIO, app_env=settings.app_env),
        places=FakePlaces(DEFAULT_FAKE_SCENARIO, app_env=settings.app_env),
        guides=FakeGuides(DEFAULT_FAKE_SCENARIO, app_env=settings.app_env),
    )


def _build_live(settings: Settings) -> LiveProviders:
    from app.livedata.providers.osm import NominatimGeocoder, OverpassPlaces
    from app.livedata.providers.wiki import MediaWikiGuides

    user_agent = settings.wiki_user_agent
    return LiveProviders(
        geocoder=NominatimGeocoder(
            settings.nominatim_base_url, settings.nominatim_timeout_s, user_agent
        ),
        places=OverpassPlaces(settings.overpass_base_url, settings.overpass_timeout_s, user_agent),
        guides=MediaWikiGuides(settings.mediawiki_timeout_s, user_agent),
    )


@lru_cache
def get_providers() -> LiveProviders:
    """The process's three providers, built from the settings on first use."""
    settings = get_settings()
    if settings.live_data_provider == "LIVE":
        return _build_live(settings)
    return _build_fake(settings)


def reset_cache() -> None:
    """Forget the built providers, so the next call reads the settings again (tests)."""
    get_providers.cache_clear()


def get_geocoder() -> GeocodingProvider:
    return get_providers().geocoder


def get_places_provider() -> PlacesProvider:
    return get_providers().places


def get_guide_provider() -> GuideSourceProvider:
    return get_providers().guides
