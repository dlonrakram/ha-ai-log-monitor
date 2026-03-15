# AI Log Monitor

This app analyses your Home Assistant logs daily using the Perplexity
Sonar AI and sends you a summary of any issues found.

## How it works

1. At the configured time each day (and once on startup), the app fetches
   recent logs from your Home Assistant Core instance.
2. The logs are cleaned, filtered, and truncated to stay within your
   configured character limit.
3. The processed logs are sent to the Perplexity Sonar API with a
   carefully engineered prompt that identifies errors, groups them by
   root cause, assigns severity, and suggests fixes.
4. A concise summary notification is sent to your chosen notification
   service (e.g. mobile app push, persistent notification).
5. Optionally, a detailed report is written to the HA system log
   (visible under Settings > System > Logs).

## Configuration

| Option | Description |
|--------|-------------|
| **Perplexity API Key** | Your API key from https://www.perplexity.ai/settings/api |
| **Perplexity Model** | `sonar` (cheapest), `sonar-pro`, or `sonar-reasoning-pro` |
| **Daily Run Time** | When to run the analysis (HH:MM, 24-hour, your HA timezone) |
| **Notification Service** | e.g. `persistent_notification.create` or `notify.mobile_app_xxx` |
| **Maximum Log Characters** | Cap on log text sent to the AI (default 60000) |
| **Log Lines to Fetch** | How many recent lines to request (default 5000) |
| **Write to System Log** | Whether to write the detailed report to HA system log |

## Getting a Perplexity API Key

1. Go to https://www.perplexity.ai/settings/api
2. Generate a new API key.
3. Add credit to your API account (the Sonar model costs ~$0.006 per
   daily run with default settings — roughly $0.18/month).

## Estimated costs

With default settings (`sonar` model, 60000 chars max):

- ~15000 input tokens + ~500 output tokens per run
- Cost per run: ~$0.006 (including $0.005 request fee)
- Daily use: ~$0.18/month
- With `sonar-pro`: ~$0.06/run → ~$1.80/month

Reduce costs by lowering `max_log_chars` or `log_lines`.
