"""Token verification (§6.2, IMD-04; IMP-108: TC-057, TC-347). No database and no network."""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends, FastAPI
from fixtures.auth import (
    TEST_JWT_SECRET,
    auth_test_settings,
    bearer,
    client_for,
    make_token,
)

from app.auth import deps
from app.auth.tokens import TokenClaims, TokenVerifier, jwks_client, verifier_for
from app.core.errors import ServiceUnavailable, Unauthenticated
from app.core.request_id import RequestIdMiddleware, user_hash
from app.main import create_app

USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000108")
# A different test-only secret: a token signed with it is "tampered" from the server's view.
OTHER_SECRET = TEST_JWT_SECRET[::-1]


def verify(token: str, verifier: TokenVerifier | None = None) -> TokenClaims:
    verifier = verifier or TokenVerifier(jwt_secret=TEST_JWT_SECRET)
    return asyncio.run(verifier.verify(token))


def tampered(token: str) -> str:
    header, payload, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    return f"{header}.{payload}.{flipped}"


# ---------- HS256 (the default and the test mode) ----------


def test_tc_057_a_valid_token_yields_the_sub_as_user_id() -> None:
    claims = verify(make_token(USER_ID, email="traveller@example.test"))
    assert claims == TokenClaims(user_id=USER_ID, email="traveller@example.test")


def test_a_helper_token_outlasts_a_backward_clock_step() -> None:
    # WSL time sync steps the wall clock back by up to 0.35 s; iat = now then reads as the future.
    payload = jwt.decode(make_token(USER_ID), options={"verify_signature": False})
    assert payload["iat"] <= time.time() - 1


@pytest.mark.parametrize(
    "token",
    [
        make_token(USER_ID, expired=True),
        tampered(make_token(USER_ID)),
        make_token(USER_ID, secret=OTHER_SECRET),
        make_token(USER_ID, wrong_aud=True),
        make_token(USER_ID, omit=["aud"]),
        make_token(USER_ID, omit=["exp"]),
        make_token(USER_ID, omit=["sub"]),
        make_token("not-a-uuid"),
        jwt.encode({"sub": str(USER_ID), "aud": "authenticated", "exp": 9999999999}, None, "none"),
        "not.a.token",
        "",
    ],
    ids=[
        "expired",
        "tampered",
        "other secret",
        "wrong audience",
        "no aud",
        "no exp",
        "no sub",
        "sub not a UUID",
        "alg none",
        "garbage",
        "empty",
    ],
)
def test_tc_347_every_bad_token_is_the_same_unauthenticated(token: str) -> None:
    with pytest.raises(Unauthenticated) as raised:
        verify(token)
    # One message for every failure: it never says which check failed.
    assert raised.value.message == Unauthenticated.default_message


def test_without_a_secret_or_jwks_url_tokens_cannot_be_checked() -> None:
    with pytest.raises(ServiceUnavailable):
        verify(make_token(USER_ID), TokenVerifier(jwt_secret=""))


def test_verifier_uses_hs256_without_a_jwks_url() -> None:
    claims = verify(make_token(USER_ID), verifier_for(auth_test_settings()))
    assert claims.user_id == USER_ID


# ---------- JWKS (asymmetric keys, IMD-04) ----------

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeKeySource:
    """Stands in for jwt.PyJWKClient: no network call."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def get_signing_key_from_jwt(self, token: str) -> Any:
        if self.error is not None:
            raise self.error
        return jwt.PyJWK.from_dict(
            {**jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)},
            algorithm="RS256",
        )


def rs256_token(**overrides: Any) -> str:
    payload = {"sub": str(USER_ID), "aud": "authenticated", "exp": 9999999999, **overrides}
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"})


def test_jwks_verifies_an_asymmetric_token() -> None:
    claims = verify(rs256_token(), TokenVerifier(key_source=FakeKeySource()))
    assert claims.user_id == USER_ID


def test_jwks_rejects_an_hs256_token_and_a_wrong_audience() -> None:
    verifier = TokenVerifier(key_source=FakeKeySource())
    with pytest.raises(Unauthenticated):
        verify(make_token(USER_ID), verifier)
    with pytest.raises(Unauthenticated):
        verify(rs256_token(aud="anon"), verifier)


def test_jwks_unknown_key_is_unauthenticated() -> None:
    verifier = TokenVerifier(key_source=FakeKeySource(jwt.PyJWKClientError("no matching kid")))
    with pytest.raises(Unauthenticated):
        verify(rs256_token(), verifier)


def test_jwks_that_cannot_be_fetched_is_service_unavailable() -> None:
    error = jwt.PyJWKClientConnectionError("fetch failed")
    with pytest.raises(ServiceUnavailable):
        verify(rs256_token(), TokenVerifier(key_source=FakeKeySource(error)))


def test_verifier_uses_jwks_when_the_url_is_set() -> None:
    url = "https://project.example.test/auth/v1/.well-known/jwks.json"
    jwks_client.cache_clear()
    verifier = verifier_for(auth_test_settings(supabase_jwks_url=url))
    # The client is built without a request; it fetches lazily on the first token.
    assert verifier._key_source is jwks_client(url)


# ---------- The dependency: 401 envelope before any database access ----------


async def no_database() -> AsyncIterator[Any]:
    raise AssertionError("the database was reached without a valid token")
    yield  # pragma: no cover


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Bearer"},
        bearer(make_token(USER_ID, expired=True)),
        bearer(make_token(USER_ID, wrong_aud=True)),
        bearer(tampered(make_token(USER_ID))),
    ],
    ids=["no header", "basic", "empty bearer", "expired", "wrong audience", "tampered"],
)
def test_bad_or_missing_tokens_get_the_401_envelope(headers: dict[str, str]) -> None:
    app = create_app(auth_test_settings())
    app.dependency_overrides[deps.db_session] = no_database

    async def call() -> httpx.Response:
        async with client_for(app) as client:
            return await client.get("/api/v1/me", headers=headers)

    response = asyncio.run(call())
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "UNAUTHENTICATED"
    assert error["message"] == Unauthenticated.default_message
    assert error["details"] == []


# ---------- Access log: user_hash from the verified token (SG-3 open item) ----------


def test_a_verified_token_fills_user_hash_in_the_access_line_without_the_raw_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.state.settings = auth_test_settings()

    @app.get("/whoami")
    async def whoami(
        claims: Annotated[TokenClaims, Depends(deps.verified_claims)],
    ) -> dict[str, str]:
        return {"ok": "yes"}

    async def call() -> httpx.Response:
        async with client_for(app) as client:
            return await client.get("/whoami", headers=bearer(make_token(USER_ID)))

    with caplog.at_level(logging.INFO, logger="app.access"):
        assert asyncio.run(call()).status_code == 200
    (record,) = [r for r in caplog.records if r.name == "app.access"]
    assert record.__dict__["user_hash"] == user_hash(USER_ID)  # a logging extra
    assert str(USER_ID) not in caplog.text
    assert all(str(USER_ID) not in str(vars(r).values()) for r in caplog.records)


# ---------- ES256 through a JWKS key set, and the clock leeway (IMD-140, SG-3 open item) ----------

ES256_KEY = ec.generate_private_key(ec.SECP256R1())
ES256_KID = "es256-test-key"


class LocalJwksClient(jwt.PyJWKClient):
    """The real PyJWKClient key lookup, fed a local key set instead of an HTTP fetch."""

    def fetch_data(self) -> Any:
        public = jwt.algorithms.ECAlgorithm.to_jwk(ES256_KEY.public_key(), as_dict=True)
        return {"keys": [{**public, "kid": ES256_KID, "alg": "ES256", "use": "sig"}]}


def es256_token(**overrides: Any) -> str:
    now = int(time.time())
    payload = {"sub": str(USER_ID), "aud": "authenticated", "iat": now, "exp": now + 600}
    return jwt.encode({**payload, **overrides}, ES256_KEY, "ES256", headers={"kid": ES256_KID})


def es256_verify(token: str) -> TokenClaims:
    verifier = TokenVerifier(
        key_source=LocalJwksClient("https://jwks.invalid/.well-known/jwks.json")
    )
    return verify(token, verifier)


def test_an_es256_token_from_the_jwks_key_set_is_accepted() -> None:
    assert es256_verify(es256_token()).user_id == USER_ID


def test_iat_20_s_ahead_is_accepted_and_40_s_ahead_is_refused() -> None:
    now = int(time.time())
    assert es256_verify(es256_token(iat=now + 20)).user_id == USER_ID
    with pytest.raises(Unauthenticated):
        es256_verify(es256_token(iat=now + 40))


def test_an_expired_es256_token_is_refused() -> None:
    now = int(time.time())
    with pytest.raises(Unauthenticated):
        es256_verify(es256_token(iat=now - 700, exp=now - 60))
