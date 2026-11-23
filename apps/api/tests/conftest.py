"""Shared pytest configuration: the provider socket guard (specification §13.1) and settings.

Tests never reach a provider. Unless a test is marked ``live``, any attempt to resolve or connect
to a host in ``PROVIDER_HOSTS`` raises ``ProviderNetworkBlockedError``. Mocked HTTP (respx) and
recorded responses never open a socket, so they are not affected.

The cached settings are cleared around every test, and ``clean_settings_env`` removes every
backend variable from the environment, so a test sees only the values it sets. A developer's local
``ORS_API_KEY`` never reaches a test that is not marked ``live`` (RUN-087).
"""

import os
import socket
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fixtures.auth import api_app, api_client, auth_user  # noqa: F401  # registers the auth fixtures
from fixtures.db import db_session, migrated_database_url  # noqa: F401  # registers the DB fixtures
from pydantic import SecretStr

from app.core import config
from app.core.config import Settings, get_settings
from app.routing import client as routing_client

# Provider API hosts the guard refuses. A pattern "*.example.org" matches example.org and every
# subdomain. Extension cards add their hosts here (§13.1: api.open-meteo.com, *.wikipedia.org,
# *.wikivoyage.org). Amendment A2 §11 (IMP-723) adds the live-data hosts: Nominatim, Overpass and
# the MediaWiki wikis; a configured mirror's host is added here too.
PROVIDER_HOSTS: tuple[str, ...] = (
    "generativelanguage.googleapis.com",  # Gemini API (google-genai)
    "api.openrouteservice.org",  # OpenRouteService
    "nominatim.openstreetmap.org",  # Nominatim (live-data geocoding)
    "overpass-api.de",  # Overpass API (live-data places)
    "*.wikivoyage.org",  # MediaWiki API, Wikivoyage
    "*.wikipedia.org",  # MediaWiki API, Wikipedia
)


class ProviderNetworkBlockedError(RuntimeError):
    """Raised when a test that is not marked ``live`` tries to reach a provider host.

    Not an ``OSError``: client code that falls back on network errors must not swallow it.
    """


def match_provider_host(host: object, patterns: Iterable[str] = PROVIDER_HOSTS) -> str | None:
    """Return the pattern in ``patterns`` that ``host`` matches, or None."""
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str):
        return None
    name = host.strip().rstrip(".").lower()
    for pattern in patterns:
        if pattern.startswith("*."):
            domain = pattern[2:]
            if name == domain or name.endswith("." + domain):
                return pattern
        elif name == pattern:
            return pattern
    return None


@dataclass(frozen=True)
class ProviderSocketGuard:
    """What the guard fixture yields, so tests can inspect it without importing this module."""

    active: bool
    hosts: tuple[str, ...]
    error: type[ProviderNetworkBlockedError]
    match: Callable[..., str | None]


def _refuse_provider_host(host: object, nodeid: str) -> None:
    pattern = match_provider_host(host)
    if pattern is not None:
        raise ProviderNetworkBlockedError(
            f"socket guard: {nodeid} tried to reach provider host {host!r} (matches {pattern!r}). "
            "Use the MOCK provider, recorded responses or respx, or mark the test 'live' "
            "(run only by make live-smoke)."
        )


@pytest.fixture(autouse=True)
def provider_socket_guard(request: pytest.FixtureRequest) -> Iterator[ProviderSocketGuard]:
    """Block provider hosts for every test that is not marked ``live``."""
    live = request.node.get_closest_marker("live") is not None
    guard = ProviderSocketGuard(
        active=not live,
        hosts=PROVIDER_HOSTS,
        error=ProviderNetworkBlockedError,
        match=match_provider_host,
    )
    if live:
        yield guard
        return

    nodeid = request.node.nodeid
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    # Name resolution: covers socket.create_connection, httpx/httpcore and asyncio, which all
    # resolve the host name through socket.getaddrinfo before connecting.
    def guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        _refuse_provider_host(host, nodeid)
        return real_getaddrinfo(host, *args, **kwargs)

    # A host name passed straight to connect() is resolved inside the C socket module.
    def guarded_connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and address:
            _refuse_provider_host(address[0], nodeid)
        real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if isinstance(address, tuple) and address:
            _refuse_provider_host(address[0], nodeid)
        return real_connect_ex(self, address)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
        patch.setattr(socket.socket, "connect", guarded_connect)
        patch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
        yield guard


@pytest.fixture(autouse=True)
def isolate_local_provider_keys(request: pytest.FixtureRequest) -> Iterator[None]:
    """Keep a developer's ``ORS_API_KEY`` out of every test that is not marked ``live``.

    A real key in the shell or in the untracked ``apps/api/.env`` would make the routing client
    call OpenRouteService, which the socket guard refuses, so results depended on the machine.
    Setting the variable to "" is not enough: ``env_ignore_empty`` then falls back to ``.env``.
    So the ambient variable is removed and the settings accessor returns an empty key, unless
    the test sets ``ORS_API_KEY`` itself. Live tests keep their real environment.
    """
    if request.node.get_closest_marker("live") is not None:
        yield
        return

    load_with_local_keys = config.load_settings

    def load_without_local_ors_key() -> Settings:
        settings = load_with_local_keys()
        if "ORS_API_KEY" in os.environ:  # set by the test itself after this fixture ran
            return settings
        return settings.model_copy(update={"ors_api_key": SecretStr("")})

    # A private context, not the shared monkeypatch fixture: sharing it would change the order in
    # which a test's own socket patches and the socket guard are undone.
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv("ORS_API_KEY", raising=False)
        # get_settings() looks load_settings up in its module at call time, so this reaches it.
        patch.setattr(config, "load_settings", load_without_local_ors_key)
        get_settings.cache_clear()
        # The routing client caches the key it was built with, so build it afresh too.
        routing_client.get_client.cache_clear()
        yield
    get_settings.cache_clear()
    routing_client.get_client.cache_clear()


# TC-490 (Amendment A2 §3.4, IMP-730): ANY_CITY_SUITE_ON=1 runs the existing suites once with the
# switch ON. FEATURES_DISABLED=!any_city_mode then reaches every Settings a test builds from the
# environment; a value a test passes itself still wins, and ``clean_settings_env`` still gives a
# test the empty environment it asks for. Unset (the default), nothing changes.
ANY_CITY_SUITE_ON: bool = os.environ.get("ANY_CITY_SUITE_ON") == "1"
ANY_CITY_ON_FEATURES = "!any_city_mode"


@pytest.fixture(autouse=True)
def any_city_suite_on() -> Iterator[None]:
    """With ``ANY_CITY_SUITE_ON=1``, the switch is ON for the test (TC-490 record only)."""
    if not ANY_CITY_SUITE_ON:
        yield
        return
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("FEATURES_DISABLED", ANY_CITY_ON_FEATURES)
        get_settings.cache_clear()
        yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Iterator[None]:
    """Let each test read the settings afresh."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def clean_settings_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Remove every backend variable (and GOOGLE_API_KEY) and stop reading ``.env``.

    Returns the monkeypatch, so the test sets only the variables it needs with ``setenv``.
    """
    for name in [*Settings.model_fields, "google_api_key"]:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    return monkeypatch
