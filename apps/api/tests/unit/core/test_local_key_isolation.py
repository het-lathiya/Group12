"""Tests never see a developer's local ORS_API_KEY (RUN-087).

The shared fixture ``isolate_local_provider_keys`` in tests/conftest.py removes the variable from
the environment and makes the settings accessor return an empty key, unless the test sets one.
Run with ``ORS_API_KEY=dummy-not-a-key make test-unit ARGS='-k local_key_isolation'`` to see the
override against a real shell value; the ``.env`` case is shown below with a temporary file.
"""

import os
from pathlib import Path

import pytest

from app.core.config import Settings, get_settings
from app.routing import client as routing_client

# Fake values: the tests assert that neither reaches the settings.
FILE_KEY = "ors-key-from-local-file-not-real"
TEST_KEY = "ors-key-set-by-test-not-real"


@pytest.fixture
def local_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A developer's untracked env file holding a real-looking ORS key."""
    path = tmp_path / "developer-local.env"
    path.write_text(f"ORS_API_KEY={FILE_KEY}\nORS_DAILY_ALLOWANCE=11\n", encoding="utf-8")
    monkeypatch.setitem(Settings.model_config, "env_file", str(path))
    get_settings.cache_clear()
    return path


def test_the_shell_variable_is_removed_for_a_non_live_test() -> None:
    assert "ORS_API_KEY" not in os.environ
    assert get_settings().ors_api_key.get_secret_value() == ""


def test_a_key_in_the_local_env_file_is_not_used(local_env_file: Path) -> None:
    settings = get_settings()
    assert settings.ors_api_key.get_secret_value() == ""
    # Only the key is overridden: the rest of the file still applies.
    assert settings.ors_daily_allowance == 11


def test_the_routing_client_is_built_without_the_local_key(local_env_file: Path) -> None:
    routing_client.get_client.cache_clear()
    try:
        assert routing_client.get_client()._api_key == ""
    finally:
        routing_client.get_client.cache_clear()


def test_a_key_the_test_sets_itself_is_kept(
    local_env_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ORS_API_KEY", TEST_KEY)
    get_settings.cache_clear()
    assert get_settings().ors_api_key.get_secret_value() == TEST_KEY
