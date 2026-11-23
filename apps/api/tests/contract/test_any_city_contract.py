"""The any-city contract and the switch-OFF route set (IMP-722; TC-461; Amendment A2 §3.3, §3.4).

``contracts/openapi.any-city.v1.json`` is the contract of the app built with ``!any_city_mode``; it
must be current, and every path it adds to the switch-OFF contract must have an ``API-NN`` summary
and no forbidden path word. With the switch OFF the any-city paths answer 404 NOT_FOUND.

C1a narrowing (RUN-089): the router is still empty, so "exactly API-76 to API-79" is asserted by
IMP-725 in C1b, when the routes exist.
"""

import re
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.ai.factory import get_model_provider
from app.auth.deps import current_user, db_session
from app.auth.tokens import TokenClaims
from app.core.config import Settings
from app.main import create_app
from app.openapi_export import ANY_CITY_CONTRACT_FILE, CONTRACT_FILE, openapi_document, render

CONTRACTS = Path(__file__).resolve().parents[4] / "contracts"
V1 = "/api/v1"
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
# The words test_openapi_contract.py forbids in any path (§6.8 and the cut extensions).
FORBIDDEN_PATH_WORDS = re.compile(
    r"share|feedback|receipt|expense|proposal|transport-options|compare|packing|"
    r"trip-intake|weather|today|budget-fit|context|optimise|explanation|/why"
)
# A2 §5: the any-city paths, answered 404 while the switch is OFF.
ANY_CITY_REQUESTS = [
    ("GET", f"{V1}/destinations/search?q=liveton"),
    ("POST", f"{V1}/destinations/resolve"),
    ("GET", f"{V1}/destinations/{uuid.UUID(int=1)}/import"),
    ("GET", f"{V1}/destinations/{uuid.UUID(int=1)}"),
]


def _operations(document: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in document["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def test_any_city_contract_is_current() -> None:
    committed = (CONTRACTS / ANY_CITY_CONTRACT_FILE).read_text(encoding="utf-8")
    assert committed == render(any_city_mode=True), (
        "contracts/openapi.any-city.v1.json is stale; run make openapi"
    )


def test_any_city_contract_off_contract_is_unchanged() -> None:
    committed = (CONTRACTS / CONTRACT_FILE).read_text(encoding="utf-8")
    assert committed == render()


def test_any_city_contract_adds_only_api_nn_paths_without_forbidden_words() -> None:
    off = openapi_document()
    on = openapi_document(any_city_mode=True)
    assert _operations(off) <= _operations(on)
    added = _operations(on) - _operations(off)
    for method, path in added:
        operation = on["paths"][path][method.lower()]
        assert re.match(r"API-\d{2}\b", operation.get("summary", "")), f"{method} {path}"
    for path in on["paths"]:
        assert not FORBIDDEN_PATH_WORDS.search(path), path


@pytest.mark.parametrize(("method", "path"), ANY_CITY_REQUESTS)
def test_any_city_contract_switch_off_paths_answer_404(
    clean_settings_env: pytest.MonkeyPatch, method: str, path: str
) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        ai_provider="MOCK",
        database_url=SecretStr("postgresql+psycopg://t@db.invalid/t"),
    )
    app = create_app(settings)
    app.dependency_overrides[current_user] = lambda: TokenClaims(uuid.uuid4(), None)
    app.dependency_overrides[db_session] = lambda: None
    app.dependency_overrides[get_model_provider] = lambda: None
    body = {"osm_ref": "R9000001"} if method == "POST" else None
    response = TestClient(app).request(method, path, json=body)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
