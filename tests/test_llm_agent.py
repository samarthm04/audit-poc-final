"""Tests for llm_agent: mock path, success path, and auth failure."""

import json
import types

import pytest

import agents.llm_agent as llm_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(status: int, body: dict) -> types.SimpleNamespace:
    """Build a minimal fake requests.Response-like object."""
    resp = types.SimpleNamespace()
    resp.status_code = status
    resp.text = json.dumps(body)

    def raise_for_status():
        if status >= 400:
            import requests  # noqa: PLC0415
            raise requests.HTTPError(response=resp)

    resp.raise_for_status = raise_for_status
    return resp


# ---------------------------------------------------------------------------
# Mock path (no API key)
# ---------------------------------------------------------------------------

def test_ask_llm_returns_mock_when_no_key(monkeypatch):
    """ask_llm returns deterministic mock string when MISTRAL_API_KEY is unset."""
    monkeypatch.setattr(llm_agent.config, "MISTRAL_API_KEY", None)
    result = llm_agent.ask_llm("any prompt")
    assert "MISTRAL_API_KEY" in result
    assert "[MOCK]" in result


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

def test_ask_llm_with_mistral_success(monkeypatch):
    """ask_llm_with_mistral extracts content from a well-formed Mistral response."""
    fake_body = {"choices": [{"message": {"content": "test output"}}]}
    fake_resp = _fake_response(200, fake_body)

    import requests  # noqa: PLC0415

    monkeypatch.setattr(requests, "post", lambda *a, **kw: fake_resp)
    monkeypatch.setattr(llm_agent.config, "MISTRAL_API_KEY", "sk-test")

    result = llm_agent.ask_llm_with_mistral("hello", model="mistral-small")
    assert result == "test output"


# ---------------------------------------------------------------------------
# Auth failure path
# ---------------------------------------------------------------------------

def test_ask_llm_with_mistral_401_raises_permission_error(monkeypatch):
    """ask_llm_with_mistral raises PermissionError on HTTP 401."""
    fake_body = {"message": "Unauthorized"}

    import requests as req_mod  # noqa: PLC0415

    class FakeResp:
        status_code = 401
        text = json.dumps(fake_body)

        def raise_for_status(self):
            raise req_mod.HTTPError(response=self)

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: FakeResp())
    monkeypatch.setattr(llm_agent.config, "MISTRAL_API_KEY", "sk-bad")

    with pytest.raises(PermissionError, match="MISTRAL_API_KEY"):
        llm_agent.ask_llm_with_mistral("hello", model="mistral-small")


def test_ask_llm_with_mistral_403_raises_permission_error(monkeypatch):
    """ask_llm_with_mistral raises PermissionError on HTTP 403."""
    import requests as req_mod  # noqa: PLC0415

    class FakeResp:
        status_code = 403
        text = json.dumps({"message": "Forbidden"})

        def raise_for_status(self):
            raise req_mod.HTTPError(response=self)

    monkeypatch.setattr(req_mod, "post", lambda *a, **kw: FakeResp())
    monkeypatch.setattr(llm_agent.config, "MISTRAL_API_KEY", "sk-bad")

    with pytest.raises(PermissionError):
        llm_agent.ask_llm_with_mistral("hello", model="mistral-small")
