"""Unit tests for the Ollama client — JSON extraction and retry logic.

The network call (requests.post) is monkeypatched, so no Ollama is needed.
This is important coverage: these helpers are what protect the app from messy
or failing LLM output.
"""
import json

import pytest

from app.services import llm_client as llm_module
from app.services.llm_client import LLMClient, extract_json


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == '{"a": 1}'


def test_extract_json_from_markdown_fence():
    raw = "```json\n{\"a\": 1}\n```"
    assert json.loads(extract_json(raw)) == {"a": 1}


def test_extract_json_surrounded_by_prose():
    raw = 'Sure! Here it is: {"a": 1, "b": 2} — hope that helps'
    assert json.loads(extract_json(raw)) == {"a": 1, "b": 2}


def test_extract_json_returns_none_when_absent():
    assert extract_json("there is no json here at all") is None


class _FakeResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"response": self._text}


def test_complete_json_parses_valid_output(monkeypatch):
    monkeypatch.setattr(
        llm_module.requests, "post", lambda *a, **k: _FakeResponse('{"x": 1}')
    )
    assert LLMClient().complete_json("sys", "user") == {"x": 1}


def test_complete_json_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_post(*args, **kwargs):
        calls["n"] += 1
        # First reply is garbage, second is valid JSON.
        return _FakeResponse("garbage no braces" if calls["n"] == 1 else '{"ok": true}')

    monkeypatch.setattr(llm_module.requests, "post", fake_post)

    result = LLMClient().complete_json("sys", "user", retries=2)

    assert result == {"ok": True}
    assert calls["n"] == 2  # it retried exactly once


def test_complete_json_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr(
        llm_module.requests, "post", lambda *a, **k: _FakeResponse("still not json")
    )
    with pytest.raises(ValueError):
        LLMClient().complete_json("sys", "user", retries=1)
