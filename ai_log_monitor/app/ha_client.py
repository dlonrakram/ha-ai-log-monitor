"""Home Assistant API client using the Supervisor proxy."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

SUPERVISOR_BASE = "http://supervisor"


class HAClient:
    """Thin wrapper around the Supervisor / HA Core API."""

    def __init__(self, supervisor_token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Log collection (Supervisor API)
    # ------------------------------------------------------------------

    def fetch_core_logs(self, lines: int = 5000) -> str:
        """Fetch recent Home Assistant Core logs via Supervisor API.

        Uses ``GET /core/logs`` with ``text/plain`` accept header.
        The ``lines`` query parameter controls how many lines to return
        (counted from the end of the journal).

        Returns the raw log text (may contain ANSI colour codes which
        we strip).
        """
        url = f"{SUPERVISOR_BASE}/core/logs"
        resp = self.session.get(
            url,
            params={"lines": lines, "no_colors": ""},
            headers={"Accept": "text/plain"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Notifications (HA Core REST API via Supervisor proxy)
    # ------------------------------------------------------------------

    def call_service(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> None:
        """Call a Home Assistant service via the Supervisor proxy.

        Example: ``call_service("notify", "mobile_app_pixel", {...})``
        maps to ``POST /core/api/services/notify/mobile_app_pixel``.
        """
        url = f"{SUPERVISOR_BASE}/core/api/services/{domain}/{service}"
        resp = self.session.post(url, json=data, timeout=15)
        if resp.status_code == 404:
            logger.error(
                "Service %s.%s not found (404). Check notify_service config.",
                domain,
                service,
            )
        else:
            resp.raise_for_status()
        logger.info("Called %s.%s — HTTP %s", domain, service, resp.status_code)

    def send_notification(
        self, notify_service: str, title: str, message: str
    ) -> None:
        """Send a notification using the configured service name.

        ``notify_service`` is in ``domain.service`` format, e.g.
        ``persistent_notification.create`` or ``notify.mobile_app_pixel``.
        """
        parts = notify_service.split(".", 1)
        if len(parts) != 2:
            logger.error(
                "Invalid notify_service format '%s'. Expected 'domain.service'.",
                notify_service,
            )
            return

        domain, service = parts

        # persistent_notification uses a slightly different payload shape.
        if domain == "persistent_notification":
            data = {"title": title, "message": message, "notification_id": "ai_log_monitor"}
        else:
            data = {"title": title, "message": message}

        try:
            self.call_service(domain, service, data)
        except requests.RequestException:
            logger.exception("Failed to send notification via %s", notify_service)

    def write_system_log(self, message: str, level: str = "warning") -> None:
        """Write a message to the HA system log via system_log.write.

        This makes the detailed report visible in Settings > System > Logs.
        """
        try:
            self.call_service(
                "system_log",
                "write",
                {"message": message, "level": level, "logger": "custom_components.ai_log_monitor"},
            )
        except requests.RequestException:
            logger.exception("Failed to write to system log")
