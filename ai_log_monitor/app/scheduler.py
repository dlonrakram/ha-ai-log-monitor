"""Schedule the daily analysis run and support on-demand triggers."""

from __future__ import annotations

import logging
import time

import schedule

logger = logging.getLogger(__name__)


def start_scheduler(run_time: str, job_fn: callable) -> None:  # type: ignore[type-arg]
    """Schedule ``job_fn`` to run daily at ``run_time`` (HH:MM) and then
    enter the main loop.

    The first run happens immediately on startup so the user can verify
    the app is working without waiting until the next scheduled time.
    """
    logger.info("Scheduling daily run at %s", run_time)
    schedule.every().day.at(run_time).do(job_fn)

    # Run once immediately on start-up.
    logger.info("Running initial analysis now…")
    job_fn()

    # Main loop — check every 30 seconds.
    while True:
        schedule.run_pending()
        time.sleep(30)
