"""LLM agent: routes prompts to Mistral or returns a deterministic mock."""

import json
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)

_MOCK_RESPONSE = (
    "[MOCK] MISTRAL_API_KEY is not set. "
    "Set it in your .env file to enable real LLM responses."
)

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def ask_llm(prompt: str) -> str:
    """Route prompt to Mistral if key is present, otherwise return mock string."""
    if config.MISTRAL_API_KEY:
        return ask_llm_with_mistral(prompt, model="mistral-small")
    logger.info("No API key — returning mock response")
    return _MOCK_RESPONSE


def ask_llm_with_mistral(prompt: str, model: str) -> str:
    """Call the Mistral chat completions API and return the response text."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        return _post_with_requests(payload, headers)
    except ImportError:
        return _post_with_urllib(payload, headers)


def _post_with_requests(payload: dict[str, Any], headers: dict[str, str]) -> str:
    """Send POST via `requests` and parse the response."""
    import requests  # noqa: PLC0415

    response = requests.post(_MISTRAL_URL, json=payload, headers=headers, timeout=30)
    return _handle_response(response.status_code, response.text)


def _post_with_urllib(payload: dict[str, Any], headers: dict[str, str]) -> str:
    """Send POST via `urllib.request` as a fallback when requests is unavailable."""
    import urllib.request  # noqa: PLC0415

    data = json.dumps(payload).encode()
    req = urllib.request.Request(_MISTRAL_URL, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        body = resp.read().decode()
        return _parse_body(200, body)


def _handle_response(status: int, body: str) -> str:
    """Raise on HTTP errors, parse and return content on success."""
    if status in (401, 403):
        logger.error("Auth failure from Mistral (HTTP %s)", status)
        raise PermissionError("Invalid or missing MISTRAL_API_KEY")
    if status != 200:
        logger.error("Mistral API error HTTP %s: %s", status, body)
        raise RuntimeError(f"Mistral API error: {status} {body}")
    return _parse_body(status, body)


def _parse_body(status: int, body: str) -> str:
    """Extract choices[0].message.content from a Mistral response body."""
    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
        logger.info("Mistral response received (%d chars)", len(content))
        return content
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.error("Failed to parse Mistral response: %s", exc)
        raise RuntimeError(f"Unexpected Mistral response structure: {exc}") from exc
