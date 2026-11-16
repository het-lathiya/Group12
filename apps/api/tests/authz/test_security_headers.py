"""CORS on the protected API prefix (IMP-702 step 4; TC-351; NFR-015, CHK-05; §6.1 CORS).

Only an origin listed in ALLOWED_ORIGINS gets Access-Control-Allow-Origin, on a preflight and on a
simple request; credentials are never allowed (bearer token). tests/api/test_health.py covers
/health; this file covers /api/v1, where the token travels. No database is reached: the token is
checked first and a preflight never reaches a route. Security response headers (TC-352) are not
asserted here: §6 and Amendment A1 §11 name no header list (PD-RUN-081-1).
"""

import pytest
from fastapi.testclient import TestClient
from fixtures.auth import auth_test_settings

from app.main import create_app

ALLOWED = "https://web.example.test"
OTHERS = ["https://evil.example", "https://web.example.test.evil.example", "null"]
ROUTE = "/api/v1/trips"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(auth_test_settings(allowed_origins=ALLOWED)))


def preflight(client: TestClient, origin: str) -> dict[str, str]:
    response = client.options(
        ROUTE,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    return dict(response.headers)


def test_tc_351_allowed_origin_gets_the_allow_headers(client: TestClient) -> None:
    headers = preflight(client, ALLOWED)
    assert headers["access-control-allow-origin"] == ALLOWED
    assert {"authorization", "content-type"} <= {
        h.strip().lower() for h in headers["access-control-allow-headers"].split(",")
    }
    assert "access-control-allow-credentials" not in headers

    simple = client.get(ROUTE, headers={"Origin": ALLOWED})  # no token: 401, still tagged
    assert simple.status_code == 401
    assert simple.headers["access-control-allow-origin"] == ALLOWED


@pytest.mark.parametrize("origin", OTHERS)
def test_tc_351_unknown_origin_gets_no_allow_header(client: TestClient, origin: str) -> None:
    assert "access-control-allow-origin" not in preflight(client, origin)
    simple = client.get(ROUTE, headers={"Origin": origin})
    assert simple.status_code == 401
    assert "access-control-allow-origin" not in simple.headers


def test_tc_351_a_method_outside_the_list_is_not_allowed(client: TestClient) -> None:
    response = client.options(
        ROUTE, headers={"Origin": ALLOWED, "Access-Control-Request-Method": "TRACE"}
    )
    assert response.status_code == 400
    assert "TRACE" not in response.headers.get("access-control-allow-methods", "")
