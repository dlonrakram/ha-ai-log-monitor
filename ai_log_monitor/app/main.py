"""AI Log Monitor — main entry point.

This module wires together all components and runs the scheduler loop.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .ha_client import HAClient
from .logs_collector import collect_logs
from .pplx_client import analyse_logs
from .scheduler import start_scheduler
from .summary_formatter import format_detailed_report, format_notification

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("ai_log_monitor")


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state(path: str) -> dict:
    """Load persistent state from a JSON file."""
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(path: str, state: dict) -> None:
    """Persist state to a JSON file."""
    Path(path).write_text(json.dumps(state, indent=2))

# ---------------------------------------------------------------------------
# Override handling
# ---------------------------------------------------------------------------

def _apply_severity_overrides(analysis: dict, overrides: list[dict]) -> None:
    """Force severity on issue groups matching override patterns."""
    if not overrides:
        return
    import re
    rules = []
    for rule in overrides:
        pattern = rule.get("match", "")
        action = rule.get("action", "")
        if not pattern or not action.startswith("force_"):
            continue
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            compiled = re.compile(re.escape(pattern), re.IGNORECASE)
        rules.append((compiled, action.replace("force_", "")))

    for issue in analysis.get("issues", []):
        haystack = " ".join([
            issue.get("title", ""),
            issue.get("likely_cause", ""),
            *issue.get("example_log_lines", []),
        ])
        for pattern, new_severity in rules:
            if pattern.search(haystack):
                issue["severity"] = new_severity
                issue["title"] = f"{issue.get('title', '')} (overridden)"
                break

# ---------------------------------------------------------------------------
# Core analysis job
# ---------------------------------------------------------------------------

def run_analysis(cfg: Config, ha: HAClient) -> None:
    """Execute one analysis cycle: collect → analyse → notify."""
    run_start = datetime.now(timezone.utc).isoformat()
    logger.info("=== Analysis run started at %s ===", run_start)

    # 1. Collect logs -------------------------------------------------------
    log_text = collect_logs(
        ha_client=ha,
        log_lines=cfg.log_lines,
        max_chars=cfg.max_log_chars,
        overrides=cfg.overrides,
    )

    if not log_text.strip():
        logger.info("No log data retrieved — sending 'all clear' notification.")
        ha.send_notification(
            cfg.notify_service,
            "AI Log Monitor",
            "✅ No log data was available for analysis. "
            "This may mean logging is not active or the system just started.",
        )
        _save_state(cfg.state_file, {"last_run": run_start, "status": "no_logs"})
        return

    # 2. Send to Perplexity for analysis ------------------------------------
    analysis = analyse_logs(
        log_text=log_text,
        api_key=cfg.pplx_api_key,
        model=cfg.pplx_model,
    )

    # 2b. Apply user-defined severity overrides -----------------------------
    _apply_severity_overrides(analysis, cfg.overrides)

    # 3. Format results -----------------------------------------------------
    title, message = format_notification(analysis)
    detailed = format_detailed_report(analysis)

    # 4. Send notification --------------------------------------------------
    logger.info("Sending notification via %s", cfg.notify_service)
    ha.send_notification(cfg.notify_service, title, message)

    # 5. Log the detailed report to the add-on log -------------------------
    for line in detailed.splitlines():
        logger.info(line)

    # 6. Optionally write detailed report to system log ---------------------
    if cfg.write_to_system_log:
        logger.info("Writing detailed report to HA system log")
        ha.write_system_log(detailed, level="warning")

    # 7. Update state -------------------------------------------------------
    issue_count = len(analysis.get("issues", []))
    _save_state(
        cfg.state_file,
        {
            "last_run": run_start,
            "status": "ok",
            "issues_found": issue_count,
        },
    )
    logger.info(
        "=== Analysis complete — %d issue group(s) reported ===", issue_count
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Load config, validate, and start the scheduler."""
    cfg = Config()
    cfg.validate()

    ha = HAClient(cfg.supervisor_token)

    logger.info(
        "AI Log Monitor v1.0.0 — model=%s, run_time=%s, notify=%s, "
        "max_chars=%d, log_lines=%d",
        cfg.pplx_model,
        cfg.run_time,
        cfg.notify_service,
        cfg.max_log_chars,
        cfg.log_lines,
    )

    # The scheduler runs the job once immediately, then daily.
    start_scheduler(cfg.run_time, lambda: run_analysis(cfg, ha))


if __name__ == "__main__":
    main()
