"""Configuration loader — reads environment variables set by run.sh."""

from __future__ import annotations

import os
import sys


class Config:
    """Immutable configuration for the AI Log Monitor."""

    def __init__(self) -> None:
        self.pplx_api_key: str = os.environ.get("PPLX_API_KEY", "")
        self.pplx_model: str = os.environ.get("PPLX_MODEL", "sonar")
        self.run_time: str = os.environ.get("RUN_TIME", "07:00")
        self.notify_service: str = os.environ.get(
            "NOTIFY_SERVICE", "persistent_notification.create"
        )
        self.max_log_chars: int = int(os.environ.get("MAX_LOG_CHARS", "60000"))
        self.log_lines: int = int(os.environ.get("LOG_LINES", "5000"))
        self.write_to_system_log: bool = os.environ.get(
            "WRITE_TO_SYSTEM_LOG", "true"
        ).lower() in ("true", "1", "yes")

        # Supervisor injects this automatically inside the add-on container.
        self.supervisor_token: str = os.environ.get("SUPERVISOR_TOKEN", "")

        # State file to track last successful run.
        self.state_file: str = "/data/last_run.json"

    def validate(self) -> None:
        """Exit early if critical settings are missing."""
        errors: list[str] = []
        if not self.pplx_api_key:
            errors.append(
                "pplx_api_key is not set. Please configure it in the app options."
            )
        if not self.supervisor_token:
            errors.append(
                "SUPERVISOR_TOKEN is not available. "
                "This app must run as a Home Assistant add-on."
            )
        if errors:
            for e in errors:
                print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
