"""Minimal client for the Perplexity Sonar API (chat completions)."""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any

import requests

logger = logging.getLogger(__name__)

SONAR_URL = "https://api.perplexity.ai/v1/sonar"

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert Home Assistant and Linux systems engineer.

    You will receive raw Home Assistant Core logs covering roughly the last
    24 hours.  Your task:

    1. Identify all errors, warnings, and exceptions.
    2. Group them by likely root cause (do not list duplicates individually).
    3. Assign a severity to each group: high, medium, or low.
       - high: service outage, data loss, security issue, repeated crash loops.
       - medium: degraded functionality, intermittent failures, deprecated usage.
       - low: cosmetic warnings, one-off transient errors, informational.
    4. For each group, suggest a concrete next step or likely fix.

    Respond with ONLY valid JSON matching this structure (no markdown fences,
    no commentary outside the JSON):

    {
      "summary": "2-5 line human-readable overview of the system health.",
      "issues": [
        {
          "title": "Short descriptive title",
          "severity": "high | medium | low",
          "count": 123,
          "example_log_lines": ["one or two representative lines"],
          "likely_cause": "Explanation of probable root cause",
          "recommended_action": "What the user should do"
        }
      ]
    }

    If there are no significant issues, return:
    {
      "summary": "No significant issues found in the last 24 hours.",
      "issues": []
    }
""")


def _build_messages(log_text: str) -> list[dict[str, str]]:
    """Build the messages array for the Sonar API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Here are the Home Assistant Core logs for analysis:\n\n"
                f"{log_text}"
            ),
        },
    ]


def analyse_logs(
    log_text: str,
    api_key: str,
    model: str = "sonar",
) -> dict[str, Any]:
    """Send logs to Perplexity Sonar and return parsed analysis.

    Returns a dict with keys ``summary`` (str) and ``issues`` (list).
    On any failure the dict still has ``summary`` with an error note and
    an empty ``issues`` list so callers always get a usable result.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": _build_messages(log_text),
        "disable_search": True,  # No web search needed — saves cost.
        "max_tokens": 4096,
    }

    logger.info(
        "Sending %d chars of logs to Perplexity (%s)…",
        len(log_text),
        model,
    )

    try:
        resp = requests.post(
            SONAR_URL, headers=headers, json=payload, timeout=120
        )
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Perplexity API request failed")
        return {
            "summary": "AI analysis failed — could not reach Perplexity API.",
            "issues": [],
        }

    data = resp.json()
    content: str = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    # Log token usage for cost awareness.
    usage = data.get("usage", {})
    logger.info(
        "Perplexity response: %d prompt tokens, %d completion tokens",
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )

    # Try to parse the JSON response.
    return _parse_response(content)


def _parse_response(content: str) -> dict[str, Any]:
    """Parse the model's response, falling back gracefully."""
    # Strip markdown code fences if the model wrapped them anyway.
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].rstrip()

    try:
        result = json.loads(cleaned)
        if "summary" in result:
            return result
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse Perplexity response as JSON")

    # Fallback: treat the entire response as the summary.
    return {
        "summary": content[:2000] if content else "No response from AI.",
        "issues": [],
    }
