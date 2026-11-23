"""The default-off switch any_city_mode and its start-up rules (IMP-722; TC-460, TC-462; A2 §3.1, §7.2).

``!any_city_mode`` in FEATURES_DISABLED turns the switch ON; an empty value or any list without the
token keeps it OFF, and an explicit ``any_city_mode`` wins. Every other switch behaves as before.
In staging and production with the switch ON, start-up refuses the FAKE live-data provider and a
LIVE provider without an identifying WIKI_USER_AGENT.
"""

import pytest

from app.core.config import ConfigError, Settings, check_settings, load_settings
from app.core.flags import DEFAULT_OFF, is_enabled, parse_features_disabled

LOCAL_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres"
NINE_CUT_NAMES = (
    "ranking_explain,nl_intake,day_explain,optimise_order,rain_swap,today_view,"
    "budget_fit,context_cards,packing"
)
USER_AGENT = "AITravelPlanner/1.0 (contact: team@example.test)"


@pytest.fixture
def env(clean_settings_env: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    clean_settings_env.setenv("DATABASE_URL", LOCAL_DATABASE_URL)
    return clean_settings_env


def _settings(features_disabled: str) -> Settings:
    return Settings(_env_file=None, features_disabled=features_disabled)


def _staging_gemini(env: pytest.MonkeyPatch, app_env: str = "staging") -> None:
    env.setenv("APP_ENV", app_env)
    env.setenv("AI_PROVIDER", "GEMINI")
    env.setenv("GEMINI_API_KEY", "test-gemini-key-not-real")
    env.setenv("GEMINI_MODEL_ID", "test-model-id")
    env.setenv("GEMINI_EMBEDDING_MODEL_ID", "gemini-embedding-2")


def _problems(env: pytest.MonkeyPatch) -> list[str]:
    try:
        check_settings(load_settings(), {})
    except ConfigError as exc:
        return exc.problems
    return []


def test_any_city_switch_is_a_default_off_name() -> None:
    assert frozenset({"any_city_mode"}) == DEFAULT_OFF


@pytest.mark.parametrize(
    "value",
    ["", "versions", NINE_CUT_NAMES, "any_city_mode", "!any_city_mode,any_city_mode", "!versions"],
)
def test_any_city_switch_tc_460_off_without_the_token(value: str) -> None:
    assert not is_enabled(_settings(value), "any_city_mode")


@pytest.mark.parametrize(
    "value", ["!any_city_mode", "versions,!any_city_mode", " !Any_City_Mode , packing"]
)
def test_any_city_switch_tc_460_on_with_the_token(value: str) -> None:
    assert is_enabled(_settings(value), "any_city_mode")
    assert is_enabled(_settings(value), "ANY_CITY_MODE")


def test_any_city_switch_tc_460_other_switches_unchanged() -> None:
    assert parse_features_disabled("versions,!any_city_mode") == {"versions", "!any_city_mode"}
    on = _settings("versions,!any_city_mode")
    assert not is_enabled(on, "versions")
    assert is_enabled(on, "packing")
    # An empty value still enables every ordinary switch (IMD-11).
    empty = _settings("")
    assert is_enabled(empty, "versions")
    assert is_enabled(empty, "packing")


def test_any_city_switch_settings_defaults(env: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    assert settings.live_data_provider == "FAKE"
    assert settings.nominatim_base_url == "https://nominatim.openstreetmap.org"
    assert settings.overpass_base_url == "https://overpass-api.de/api/interpreter"
    assert settings.nominatim_timeout_s == 10
    assert settings.overpass_timeout_s == 90
    assert settings.mediawiki_timeout_s == 10
    assert settings.live_min_usable_places == 40
    assert settings.live_data_ttl_days == 30
    assert settings.live_daily_imports_per_user == 5
    assert settings.live_daily_imports_global == 50
    assert settings.wiki_user_agent == ""


@pytest.mark.parametrize("name", ["NOMINATIM_BASE_URL", "OVERPASS_BASE_URL"])
def test_any_city_switch_base_urls_are_https_only(env: pytest.MonkeyPatch, name: str) -> None:
    env.setenv(name, "http://mirror.example.test")
    with pytest.raises(ConfigError) as caught:
        load_settings()
    assert any(name in problem for problem in caught.value.problems)
    assert "mirror.example.test" not in str(caught.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LIVE_DATA_PROVIDER", "REAL"),
        ("NOMINATIM_TIMEOUT_S", "0"),
        ("OVERPASS_TIMEOUT_S", "-1"),
        ("MEDIAWIKI_TIMEOUT_S", "0"),
        ("LIVE_MIN_USABLE_PLACES", "0"),
        ("LIVE_DATA_TTL_DAYS", "0"),
        ("LIVE_DAILY_IMPORTS_PER_USER", "0"),
        ("LIVE_DAILY_IMPORTS_GLOBAL", "0"),
    ],
)
def test_any_city_switch_settings_ranges(env: pytest.MonkeyPatch, name: str, value: str) -> None:
    env.setenv(name, value)
    with pytest.raises(ConfigError) as caught:
        load_settings()
    assert any(name in problem for problem in caught.value.problems)


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_any_city_switch_tc_462_fake_is_refused_when_deployed_and_on(
    env: pytest.MonkeyPatch, app_env: str
) -> None:
    _staging_gemini(env, app_env)
    env.setenv("FEATURES_DISABLED", "!any_city_mode")
    problems = _problems(env)
    assert any(problem.startswith("LIVE_DATA_PROVIDER") for problem in problems)


@pytest.mark.parametrize("user_agent", [None, "  ", "<AITravelPlanner/1.0 (contact: team email)>"])
@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_any_city_switch_tc_462_live_needs_a_user_agent(
    env: pytest.MonkeyPatch, app_env: str, user_agent: str | None
) -> None:
    _staging_gemini(env, app_env)
    env.setenv("FEATURES_DISABLED", "!any_city_mode")
    env.setenv("LIVE_DATA_PROVIDER", "LIVE")
    if user_agent is not None:
        env.setenv("WIKI_USER_AGENT", user_agent)
    problems = _problems(env)
    assert any(problem.startswith("WIKI_USER_AGENT") for problem in problems)
    assert not any(problem.startswith("LIVE_DATA_PROVIDER") for problem in problems)


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_any_city_switch_tc_462_live_with_a_user_agent_starts(
    env: pytest.MonkeyPatch, app_env: str
) -> None:
    _staging_gemini(env, app_env)
    env.setenv("FEATURES_DISABLED", "!any_city_mode")
    env.setenv("LIVE_DATA_PROVIDER", "LIVE")
    env.setenv("WIKI_USER_AGENT", USER_AGENT)
    assert _problems(env) == []


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_any_city_switch_tc_462_off_switch_keeps_start_up_unchanged(
    env: pytest.MonkeyPatch, app_env: str
) -> None:
    _staging_gemini(env, app_env)
    # FAKE is the default and WIKI_USER_AGENT is empty: neither matters with the switch OFF.
    assert _problems(env) == []
    env.setenv("FEATURES_DISABLED", "any_city_mode,!any_city_mode")
    assert _problems(env) == []


@pytest.mark.parametrize("app_env", ["local", "test"])
def test_any_city_switch_tc_462_fake_is_allowed_locally(
    env: pytest.MonkeyPatch, app_env: str
) -> None:
    env.setenv("APP_ENV", app_env)
    env.setenv("FEATURES_DISABLED", "!any_city_mode")
    assert _problems(env) == []
