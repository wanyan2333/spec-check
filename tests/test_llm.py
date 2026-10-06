from types import SimpleNamespace

import httpx
import openai
import pytest

from spec_check.llm import OpenAICompatClient


def rate_limit_error():
    request = httpx.Request("POST", "https://example.test/chat/completions")
    return openai.RateLimitError("quota", response=httpx.Response(429, request=request), body=None)


def fake_completion(text="{}"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )


def make_client(outcomes, **kwargs):
    """Client whose underlying OpenAI SDK call is replaced by scripted outcomes."""
    sleeps = []
    client = OpenAICompatClient(api_key="test", model="m", sleep=sleeps.append, **kwargs)
    calls = []

    def create(**params):
        calls.append(params)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return client, calls, sleeps


def test_sends_temperature_zero_and_json_mode():
    client, calls, _ = make_client([fake_completion('{"a": 1}')])
    response = client.complete([{"role": "user", "content": "hi"}])
    assert response.text == '{"a": 1}'
    assert response.total_tokens == 18
    assert calls[0]["temperature"] == 0
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_retries_429_with_exponential_backoff():
    client, calls, sleeps = make_client(
        [rate_limit_error(), rate_limit_error(), fake_completion()], base_delay_s=2
    )
    response = client.complete([])
    assert len(calls) == 3
    assert sleeps == [2, 4]
    assert response.retries == 2


def test_gives_up_after_max_retries():
    client, calls, sleeps = make_client([rate_limit_error()] * 3, max_retries=2)
    with pytest.raises(openai.RateLimitError):
        client.complete([])
    assert len(calls) == 3
    assert len(sleeps) == 2
