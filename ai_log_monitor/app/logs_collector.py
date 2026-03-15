"""Collect and pre-process Home Assistant Core logs."""

from __future__ import annotations

import logging
import re

from .ha_client import HAClient

logger = logging.getLogger(__name__)

# Patterns for lines that are typically noise and safe to drop before
# sending to the AI.  Users can extend this list if needed.
NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"We found a custom integration .+ which has not been tested"),
    re.compile(r"You are using a custom integration .+ which has not been tested"),
    re.compile(r"Updating .+ took longer than"),
    re.compile(r"Setup of config entry .+ is taking longer than"),
]


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences that journald may include."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _is_noise(line: str) -> bool:
    """Return True if the line matches a known noisy pattern."""
    return any(pat.search(line) for pat in NOISE_PATTERNS)


def _is_error_or_warning(line: str) -> bool:
    """Heuristic: keep lines containing ERROR, WARNING, or Exception."""
    upper = line.upper()
    return any(
        kw in upper
        for kw in ("ERROR", "WARNING", "EXCEPTION", "TRACEBACK", "CRITICAL")
    )


def collect_logs(
    ha_client: HAClient,
    log_lines: int = 5000,
    max_chars: int = 60000,
    errors_only: bool = False,
) -> str:
    """Fetch, filter, and truncate HA Core logs.

    Parameters
    ----------
    ha_client:
        Authenticated HAClient instance.
    log_lines:
        Number of recent lines to request from the Supervisor API.
    max_chars:
        Hard cap on the returned text length (characters).
    errors_only:
        If True, pre-filter to keep only lines containing error/warning
        keywords.  This reduces token usage but may lose context.

    Returns
    -------
    str
        Cleaned log text, ready to be sent to the AI.  An empty string
        means no relevant logs were found.
    """
    logger.info("Fetching up to %d lines of HA Core logs…", log_lines)

    try:
        raw = ha_client.fetch_core_logs(lines=log_lines)
    except Exception:
        logger.exception("Failed to fetch logs from Supervisor API")
        return ""

    raw = _strip_ansi(raw)
    lines = raw.splitlines()
    logger.info("Fetched %d raw log lines (%d chars)", len(lines), len(raw))

    # Drop known noisy lines.
    filtered = [ln for ln in lines if not _is_noise(ln)]

    # Optionally keep only error/warning lines.
    if errors_only:
        filtered = [ln for ln in filtered if _is_error_or_warning(ln)]

    text = "\n".join(filtered)

    # Truncate to max_chars, keeping the most recent entries (end of log).
    if len(text) > max_chars:
        truncation_note = (
            f"[… truncated — showing last {max_chars} characters "
            f"of {len(text)} total …]\n"
        )
        text = truncation_note + text[-max_chars:]

    logger.info(
        "Prepared %d chars of log text after filtering (%d lines kept)",
        len(text),
        text.count("\n") + 1,
    )
    return text
