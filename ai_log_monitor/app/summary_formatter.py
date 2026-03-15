"""Format the AI analysis into notification and system-log messages."""

from __future__ import annotations

from typing import Any

SEVERITY_EMOJI = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


def format_notification(analysis: dict[str, Any]) -> tuple[str, str]:
    """Return (title, message) for the HA notification service.

    The notification is kept short — suitable for a mobile push or
    persistent notification in the sidebar.
    """
    issues = analysis.get("issues", [])
    summary = analysis.get("summary", "No summary available.")

    if not issues:
        return ("AI Log Monitor", f"✅ {summary}")

    high = sum(1 for i in issues if i.get("severity") == "high")
    medium = sum(1 for i in issues if i.get("severity") == "medium")
    low = sum(1 for i in issues if i.get("severity") == "low")

    title = "AI Log Monitor"
    counts = []
    if high:
        counts.append(f"🔴 {high} high")
    if medium:
        counts.append(f"🟡 {medium} medium")
    if low:
        counts.append(f"🟢 {low} low")

    header = f"Found {len(issues)} issue group(s): {', '.join(counts)}"

    # Build a concise bullet list (first 5 issues).
    bullets: list[str] = []
    for issue in issues[:5]:
        sev = issue.get("severity", "?")
        emoji = SEVERITY_EMOJI.get(sev, "⚪")
        title_text = issue.get("title", "Unknown issue")
        action = issue.get("recommended_action", "")
        line = f"{emoji} **{title_text}**"
        if action:
            line += f"\n   → {action}"
        bullets.append(line)

    if len(issues) > 5:
        bullets.append(f"… and {len(issues) - 5} more (see system log for full report)")

    body = f"{header}\n\n{summary}\n\n" + "\n\n".join(bullets)
    return (title, body)


def format_detailed_report(analysis: dict[str, Any]) -> str:
    """Return a longer text suitable for ``system_log.write``.

    This includes all issues with example log lines, causes, and actions.
    """
    issues = analysis.get("issues", [])
    summary = analysis.get("summary", "No summary available.")

    lines: list[str] = [
        "═══ AI Log Monitor — Detailed Report ═══",
        "",
        summary,
        "",
    ]

    if not issues:
        lines.append("No significant issues found.")
        return "\n".join(lines)

    for idx, issue in enumerate(issues, 1):
        sev = issue.get("severity", "unknown").upper()
        title_text = issue.get("title", "Unknown")
        count = issue.get("count", "?")
        cause = issue.get("likely_cause", "Unknown")
        action = issue.get("recommended_action", "None")
        examples = issue.get("example_log_lines", [])

        lines.append(f"--- Issue #{idx}: [{sev}] {title_text} (×{count}) ---")
        lines.append(f"  Root cause : {cause}")
        lines.append(f"  Action     : {action}")
        if examples:
            lines.append("  Example log lines:")
            for ex in examples[:3]:
                lines.append(f"    | {ex}")
        lines.append("")

    return "\n".join(lines)
