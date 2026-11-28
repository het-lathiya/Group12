"""Gemini primary, Gemini fallback, Groq, labelled rule-based plan (IMD-223)."""

import json
from pathlib import Path

import httpx
import pytest
from fixtures.ai import sample_request
from fixtures.groq import MODEL, Calls, completion
from fixtures.pipeline import Journal

from app.ai import factory
from app.ai.errors import ProviderAuthError, ProviderQuotaExhausted, ProviderUnavailable
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mock import MockProvider
from app.core.config import Settings
from app.generation import pipeline

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures/provider_recordings/gemini"


def primary(calls: Calls) -> GeminiProvider:
    return GeminiProvider(
        Settings(
            gemini_api_key="unit-test-key-not-real",
            gemini_model_id="gemini-primary",
            gemini_fallback_model_id="gemini-fallback",
        ),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(calls)),
        clock=lambda: calls.now,
        sleep=calls.sleep,
    )


def outage(name: str = "unavailable_503") -> Calls:
    data = json.loads((RECORDINGS / f"{name}.json").read_text())
    return Calls(httpx.Response(data["http_status"], json=data["body"], headers=data["headers"]))


def enable(monkeypatch: pytest.MonkeyPatch, calls: Calls) -> None:
    provider = calls.provider()
    monkeypatch.setattr(factory, "get_groq_provider", lambda: provider)


def test_two_gemini_models_fail_then_groq_is_recorded_and_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    gemini, groq = outage(), Calls()
    provider = primary(gemini)
    for _ in range(4):
        factory.breaker_for(provider).record_failure(ProviderUnavailable())
    enable(monkeypatch, groq)

    journal.run(provider)

    assert [json.loads(r.content)["model"] for r in gemini.requests] == [
        "gemini-primary",
        "gemini-primary",
        "gemini-fallback",
    ]
    assert len(groq.requests) == 1
    assert journal.recorded_provider == "GROQ"
    assert journal.recorded_model == MODEL
    assert journal.completed["outcome"] == "model"
    assert journal.saved_ids() <= sample_request().shortlist_ids()
    assert factory.breaker_for(provider).state == "open"
    assert journal.settings["api_style"] == "chat_completions"
    assert journal.completed["adapter_version"] == "groq-chat-1"
    assert journal.steps.count("running") == journal.steps.count("complete") == 1


@pytest.mark.parametrize("status", [429, 503, 401, 402, 400])
def test_groq_failure_always_ends_in_labelled_rule_based(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls(httpx.Response(status))
    enable(monkeypatch, groq)
    journal.run(primary(outage()))
    reason = {
        429: "provider_rate_limited",
        503: "provider_unavailable",
        401: "config_error",
        402: "provider_quota_exhausted",
        400: "config_error",
    }[status]
    assert journal.fell_back(reason)
    assert len(groq.requests) == (2 if status in (429, 503) else 1)
    assert journal.recorded_provider == "GROQ"
    assert journal.failed is None


def test_groq_off_makes_no_call_and_preserves_todays_path(
    monkeypatch: pytest.MonkeyPatch,
    clean_settings_env: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("disabled Groq was constructed")

    journal = Journal(monkeypatch, sample_request())
    monkeypatch.setattr(factory, "_groq", refuse)
    journal.run(primary(outage()))
    assert journal.fell_back("provider_unavailable")
    assert journal.recorded_provider is None


def test_bad_groq_json_uses_only_the_existing_single_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls(httpx.Response(200, json=completion("{")))
    enable(monkeypatch, groq)
    journal.run(primary(outage()))
    assert journal.fell_back("invalid_output")
    assert journal.completed["repair_attempts"] == 1
    assert journal.steps.count("repairing") == 1
    assert len(groq.requests) == 2  # first answer, one repair; no blind retry or second loop


def test_groq_json_can_be_repaired_with_the_same_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls(httpx.Response(200, json=completion("{")), httpx.Response(200, json=completion()))
    enable(monkeypatch, groq)
    journal.run(primary(outage()))
    assert journal.completed["outcome"] == "model_repaired"
    assert journal.completed["repair_attempts"] == 1
    assert len(groq.requests) == 2


@pytest.mark.parametrize("name", ["quota_429", "timeout"])
def test_gemini_quota_and_timeout_also_reach_groq(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls()
    enable(monkeypatch, groq)
    gemini = outage(name) if name != "timeout" else Calls(httpx.ReadTimeout("slow"))
    journal.run(primary(gemini))
    assert journal.completed["outcome"] == "model"
    assert journal.recorded_provider == "GROQ"


@pytest.mark.parametrize("quota", [True, False])
def test_open_gemini_transient_or_quota_breaker_reaches_groq(
    monkeypatch: pytest.MonkeyPatch, quota: bool
) -> None:
    journal = Journal(monkeypatch, sample_request())
    gemini = outage()
    provider = primary(gemini)
    breaker = factory.breaker_for(provider)
    for _ in range(5):
        breaker.record_failure(ProviderQuotaExhausted() if quota else ProviderUnavailable())
    enable(monkeypatch, Calls())
    journal.run(provider)
    assert gemini.requests == []
    assert journal.recorded_provider == "GROQ"


def test_auth_failure_does_not_switch_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls()
    enable(monkeypatch, groq)
    journal.run(primary(outage("permission_denied_403")))
    assert journal.failed == "config_error"
    assert groq.requests == []


def test_mock_never_switches_to_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls()
    enable(monkeypatch, groq)
    journal.run(MockProvider("timeout", app_env="test"))
    assert journal.fell_back("provider_timeout")
    assert groq.requests == []


def test_groq_cannot_start_after_the_shared_time_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls()
    enable(monkeypatch, groq)
    monkeypatch.setattr(pipeline, "GEMINI_TIME_ALLOWANCE_S", 0)
    journal.run(primary(outage()))
    assert journal.fell_back("provider_unavailable")
    assert groq.requests == []


def test_gemini_auth_breaker_does_not_switch_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq, gemini = Calls(), outage()
    provider = primary(gemini)
    factory.breaker_for(provider).record_failure(ProviderAuthError())
    enable(monkeypatch, groq)
    journal.run(provider)
    assert journal.failed == "config_error"
    assert gemini.requests == groq.requests == []


def test_open_groq_breaker_keeps_the_last_attempted_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    groq = Calls()
    provider = groq.provider()
    factory.breaker_for(provider).record_failure(ProviderQuotaExhausted())
    monkeypatch.setattr(factory, "get_groq_provider", lambda: provider)
    journal.run(primary(outage()))
    assert journal.fell_back("provider_quota_exhausted")
    assert groq.requests == []
    assert journal.recorded_provider is None
    assert journal.completed["adapter_version"] == "gemini-interactions-1"
