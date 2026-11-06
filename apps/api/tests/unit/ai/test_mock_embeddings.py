"""MOCK embeddings, mock-embed-v1 (Amendment A1 §6.5; IMP-312: TC-443)."""

import asyncio
import hashlib
import math
import socket

import pytest

from app.ai.errors import ProviderUnavailable
from app.ai.providers.finetuned import FineTunedProvider
from app.ai.providers.mock import EMBED_MODEL_ID, MockProvider, hashed_embedding


def embed(*texts: str) -> list[list[float]]:
    return asyncio.run(MockProvider("ok", app_env="test").embed_texts(texts, "document")).vectors


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_tc_443_mock_embeddings_are_deterministic_unit_vectors() -> None:
    first, again = embed("Old fort at sunrise")[0], embed("Old fort at sunrise")[0]

    assert first == again
    assert len(first) == 768
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_tc_443_mock_embeddings_follow_the_a1_algorithm_for_one_token() -> None:
    digest = hashlib.sha256(b"fort").hexdigest()
    index, sign = int(digest[:8], 16) % 768, 1.0 if int(digest[8], 16) % 2 == 0 else -1.0

    vector = hashed_embedding("FORT, at")  # lower-cased, split, "at" is under 3 characters

    assert vector[index] == sign
    assert sum(abs(value) for value in vector) == 1.0


def test_tc_443_texts_that_share_words_are_similar() -> None:
    fort, fort_again, market = embed("old fort walls", "the old fort", "spice bazaar")

    assert cosine(fort, fort_again) > 0
    assert cosine(fort, fort_again) > cosine(fort, market)


@pytest.mark.parametrize("text", ["", "a b", "--"])
def test_tc_443_a_text_without_tokens_gives_the_unit_vector_at_index_0(text: str) -> None:
    vector = embed(text)[0]

    assert vector[0] == 1.0
    assert sum(abs(value) for value in vector) == 1.0


def test_tc_443_mock_embeddings_open_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the mock opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)

    result = asyncio.run(MockProvider("ok", app_env="test").embed_texts(["fort"], "query"))

    assert result.model_id == EMBED_MODEL_ID
    assert set(result.usage.model_dump().values()) == {None}


def test_embeddings_ignore_the_scenario_and_use_embed_error() -> None:
    scenario = MockProvider("timeout", app_env="test")
    assert asyncio.run(scenario.embed_texts(["fort"], "query")).vectors == embed("fort")

    failing = MockProvider("ok", app_env="test", embed_error=ProviderUnavailable())
    with pytest.raises(ProviderUnavailable):
        asyncio.run(failing.embed_texts(["fort"], "query"))


def test_the_finetuned_stub_refuses_embeddings() -> None:
    from app.ai.errors import ProviderBadRequest

    stub = FineTunedProvider.__new__(FineTunedProvider)  # its constructor refuses too
    with pytest.raises(ProviderBadRequest, match="not enabled in Stage 1"):
        asyncio.run(stub.embed_texts(["fort"], "query"))
