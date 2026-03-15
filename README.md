# AI Log Monitor for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Home Assistant App (add-on) that performs daily AI-powered analysis of
your Home Assistant logs using the [Perplexity Sonar API](https://docs.perplexity.ai/).
It identifies errors and warnings, groups them by root cause, assigns
severity, suggests fixes, and sends you a concise summary as a
notification.

---

## Features

- **Daily automated analysis** — runs once per day at your chosen time
  (and once on startup for immediate feedback).
- **AI-powered root-cause grouping** — errors are clustered by probable
  cause, not listed individually.
- **Severity classification** — high / medium / low for easy triage.
- **Actionable recommendations** — each issue group includes a suggested
  fix or next step.
- **Configurable notification** — push to your mobile app, persistent
  notification in the sidebar, or any `notify` service.
- **Detailed system-log report** — optional full report written to
  Settings → System → Logs for deeper review.
- **Cost-efficient** — defaults to the `sonar` model at ~$0.006/run
  (~$0.18/month).
- **No external tokens needed** — uses the Supervisor API internally;
  no long-lived access token required.

---

## Requirements

| Requirement | Detail |
|-------------|--------|
| Home Assistant | OS or Supervised installation (Apps/add-ons support) |
| HA version | 2024.1.0 or later recommended |
| Perplexity API key | Free to create; requires API credit (see [Cost Estimates](#cost-estimates)) |
| Internet access | The add-on container must reach `api.perplexity.ai` |

> **Note:** Home Assistant Container (Docker-only) installations do not
> support Apps/add-ons. This add-on will not work on Container installs.

---

## Installation

### 1. Add the repository

Click the button below to add this repository to your Home Assistant:

[![Add repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FYOUR_USERNAME%2Fha-ai-log-monitor)

Or manually:

1. In Home Assistant, go to **Settings → Apps → App Store** (three-dot
   menu in the top-right corner).
2. Select **Repositories**.
3. Paste the Git URL of this repository:
   ```
   https://github.com/YOUR_USERNAME/ha-ai-log-monitor
   ```
4. Click **Add** → **Close**.

### 2. Install the app

1. After adding the repository, you should see **AI Log Monitor** in the
   App Store.  If it doesn't appear, refresh the page.
2. Click **AI Log Monitor** → **Install**.
3. Wait for the build to complete (first build takes a minute or two).

### 3. Configure

Go to the **Configuration** tab of the AI Log Monitor app and set:

| Option | What to enter |
|--------|---------------|
| **Perplexity API Key** | Your key from [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| **Perplexity Model** | `sonar` (default, cheapest) / `sonar-pro` / `sonar-reasoning-pro` |
| **Daily Run Time** | e.g. `07:00` — uses your HA timezone |
| **Notification Service** | e.g. `persistent_notification.create` or `notify.mobile_app_pixel` |
| **Maximum Log Characters** | `60000` (default) — raise for more thorough analysis, lower to save tokens |
| **Log Lines to Fetch** | `5000` (default) — how many recent journal lines to request |
| **Write to System Log** | `true` (default) — writes detailed report to Settings → System → Logs |

### 4. Start

Click **Start**.  The app runs an initial analysis immediately, so you
should receive your first notification within a minute or two.

After that, it runs once per day at the configured time.

---

## Getting a Perplexity API Key

1. Sign in at [perplexity.ai](https://www.perplexity.ai/).
2. Go to **Settings → API** (or visit
   [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
   directly).
3. Click **Generate** to create an API key.
4. Copy the key (starts with `pplx-`).
5. **Add credit**: The API uses a pay-as-you-go model.  $5 of credit
   will last months of daily use with the default `sonar` model.

---

## Choosing a Notification Service

The `notify_service` setting uses the `domain.service` format that
matches your Home Assistant service calls.

| Value | What it does |
|-------|-------------|
| `persistent_notification.create` | Shows a notification in the HA sidebar (default — works out of the box) |
| `notify.mobile_app_pixel` | Push notification to a Pixel phone via the HA Companion app |
| `notify.mobile_app_iphone` | Push notification to an iPhone via the HA Companion app |
| `notify.notify` | Default notify group (if configured) |

To find your exact service name:
1. Go to **Developer Tools → Services** in Home Assistant.
2. Search for `notify` — you'll see all available notification services.
3. Use the full `domain.service` name (e.g. `notify.mobile_app_marks_pixel`).

---

## How It Works — Architecture

```
┌─────────────────────────────────────────────────────┐
│  Home Assistant OS / Supervised                     │
│                                                     │
│  ┌──────────────┐    Supervisor API     ┌────────┐  │
│  │  AI Log      │◄────────────────────► │  HA    │  │
│  │  Monitor     │  GET /core/logs       │  Core  │  │
│  │  (container) │  POST /core/api/...   │        │  │
│  └──────┬───────┘                       └────────┘  │
│         │                                           │
└─────────┼───────────────────────────────────────────┘
          │  HTTPS
          ▼
  ┌───────────────┐
  │  Perplexity   │
  │  Sonar API    │
  └───────────────┘
```

1. **Log collection** — Fetches HA Core logs via the Supervisor API
   (`GET /core/logs`).  Authenticated automatically with the
   `SUPERVISOR_TOKEN` injected into the container — no user token needed.

2. **Pre-processing** — Strips ANSI codes, removes known noisy patterns,
   and truncates to the configured character limit (keeping the most
   recent entries).

3. **AI analysis** — Sends the cleaned logs to Perplexity's Sonar API
   with `disable_search: true` (no web search needed, saves cost).  The
   system prompt asks for structured JSON output with grouped issues,
   severity, root causes, and recommended actions.

4. **Notification** — Calls the configured HA notification service via
   the Supervisor proxy (`POST /core/api/services/...`).

5. **System log** — Optionally writes a detailed report via
   `system_log.write` so it appears under Settings → System → Logs.

---

## Cost Estimates

With default settings (`sonar` model, 60000 character limit):

| Component | Estimate |
|-----------|----------|
| Input tokens | ~15,000 (~$0.015) |
| Output tokens | ~500 (~$0.0005) |
| Request fee (low context) | $0.005 |
| **Total per run** | **~$0.006** |
| **Monthly (daily runs)** | **~$0.18** |

### Reducing costs

- Lower `max_log_chars` to 30000 (~7500 tokens → ~$0.003/run).
- Lower `log_lines` to 2000 for less data.
- Stick with the `sonar` model ($1/$1 per 1M tokens).

### Higher-quality analysis

- `sonar-pro`: ~$0.06/run → ~$1.80/month.  Better grouping and deeper
  root-cause analysis.
- `sonar-reasoning-pro`: ~$0.04/run → ~$1.20/month.  Multi-step
  reasoning for complex issue chains.

---

## Example Output

### Notification (persistent notification)

> **AI Log Monitor**
>
> Found 3 issue group(s): 🔴 1 high, 🟡 1 medium, 🟢 1 low
>
> System has 3 distinct issue groups over the last 24 hours.  The high-severity
> item is a Z-Wave device communication failure that needs attention.
>
> 🔴 **Z-Wave node 7 communication timeout**
>    → Check the Z-Wave device is powered on and within range.  Consider
>      re-interviewing the node in the Z-Wave JS UI.
>
> 🟡 **Deprecated YAML configuration for sensor platform**
>    → Migrate the `sensor:` YAML config to the UI-based integration setup.
>      See the HA 2025.x migration guide.
>
> 🟢 **Transient DNS resolution warnings**
>    → These resolved on their own.  If persistent, check your DNS server
>      configuration.

### Detailed report (system log)

```
═══ AI Log Monitor — Detailed Report ═══

System has 3 distinct issue groups over the last 24 hours.

--- Issue #1: [HIGH] Z-Wave node 7 communication timeout (×47) ---
  Root cause : Node 7 is not responding to commands, likely offline or out of range.
  Action     : Check power supply and distance.  Re-interview in Z-Wave JS UI.
  Example log lines:
    | 2026-03-14 22:15:03 ERROR (MainThread) [zwave_js] Node 7: command timed out
    | 2026-03-14 22:15:33 ERROR (MainThread) [zwave_js] Node 7: command timed out

--- Issue #2: [MEDIUM] Deprecated YAML configuration for sensor platform (×3) ---
  Root cause : sensor platform config should be migrated to config entries.
  Action     : Remove YAML config and set up via Settings > Integrations.
  Example log lines:
    | 2026-03-15 00:00:12 WARNING (MainThread) [homeassistant.loader] sensor platform uses deprecated YAML

--- Issue #3: [LOW] Transient DNS resolution warnings (×2) ---
  Root cause : Brief DNS lookup failure, likely a network blip.
  Action     : No action needed unless recurring.
  Example log lines:
    | 2026-03-15 03:22:01 WARNING (MainThread) [homeassistant.helpers.aiohttp_client] DNS resolution failed
```

---

## Troubleshooting

### The app starts but I don't get a notification

1. Check the app log (click **Log** tab in the app page) for errors.
2. Verify `notify_service` matches an existing service in
   Developer Tools → Services.
3. For `persistent_notification.create`, the notification appears in the
   HA sidebar bell icon.

### "Perplexity API request failed" in the logs

1. Verify your API key is correct and has credit.
2. Check that your HA instance has internet access.
3. Try the key with `curl`:
   ```bash
   curl -s https://api.perplexity.ai/v1/sonar \
     -H "Authorization: Bearer pplx-YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"sonar","messages":[{"role":"user","content":"hello"}],"disable_search":true}'
   ```

### "SUPERVISOR_TOKEN is not available"

This app must run as a Home Assistant App (add-on) on HA OS or
Supervised.  It cannot run as a standalone Docker container.

### I want to trigger a run manually

Currently, manual triggers require restarting the app (which runs an
analysis immediately on startup).  A future version may add a web UI
button or service call for on-demand runs.

---

## Repository Structure

```
ha-ai-log-monitor/
├── LICENSE
├── README.md
├── repository.yaml
└── ai_log_monitor/
    ├── CHANGELOG.md
    ├── DOCS.md
    ├── Dockerfile
    ├── build.yaml
    ├── config.yaml
    ├── requirements.txt
    ├── run.sh
    ├── translations/
    │   └── en.yaml
    └── app/
        ├── __init__.py
        ├── main.py            # Entry point, wires components, scheduler
        ├── config.py           # Loads env vars into Config object
        ├── ha_client.py        # Supervisor/HA REST API client
        ├── logs_collector.py   # Fetches & pre-processes Core logs
        ├── pplx_client.py      # Perplexity Sonar API client
        ├── summary_formatter.py # Formats notifications & detailed reports
        └── scheduler.py        # Daily schedule + startup run
```

---

## Contributing

Contributions are welcome.  Please open an issue first to discuss
significant changes.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and test locally with `docker build`.
4. Open a pull request.

---

## License

[MIT](LICENSE)
