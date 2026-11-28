"""Synthetic chat completions and fake time for offline Groq adapter tests (IMD-223)."""

import json
from typing import Any

import httpx
from fixtures.ai import SAMPLE_OUTPUT

from app.ai.providers.groq import GroqProvider
from app.core.config import Settings

MODEL = "openai/gpt-oss-20b"


def completion(content: str | None = None, **overrides: Any) -> dict[str, Any]:
    return {
        "id": "sample-completion",
        "model": MODEL,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(SAMPLE_OUTPUT) if content is None else content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 40,
            "completion_tokens_details": {"reasoning_tokens": 10},
            "total_tokens": 160,
        },
        **overrides,
    }


class Calls:
    def __init__(self, *answers: httpx.Response | Exception) -> None:
        self.answers = list(answers) or [httpx.Response(200, json=completion())]
        self.requests: list[httpx.Request] = []
        self.now = 1000.0
        self.delays: list[float] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answers[min(len(self.requests) - 1, len(self.answers) - 1)]
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def sleep(self, delay: float) -> None:
        self.delays.append(delay)
        self.now += delay

    def provider(self, **overrides: Any) -> GroqProvider:
        settings = Settings(
            **{
                "groq_api_key": "unit-test-key-not-real",
                "groq_model_id": MODEL,
                **overrides,
            }
        )
        return GroqProvider(
            settings,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(self)),
            clock=lambda: self.now,
            sleep=self.sleep,
        )
