"""Alerter agent: Slack DMs for unalerted matches above ALERT_SCORE."""
import config
import db
from services import slack_service


def format_alert(row) -> str:
    score = row["final_score"]
    if score >= config.PRIORITY_SCORE:
        tier, verdict = "🔥", "Apply NOW"
    else:
        tier, verdict = "✅", "Strong match — consider applying"

    matched = row["matched_skills"] or "—"
    missing = row["missing_skills"] or "None"
    lines = [
        f"{tier} *{row['company']} — {row['title']}* ({score:.0%} fit)",
        f"Resume: {row['best_resume_variant']} | Location: {row['location'] or 'n/a'}"
        + (" | Remote" if row["remote"] else ""),
        f"Matched: {matched.replace(',', ', ')}",
        f"Missing: {missing.replace(',', ', ')}",
    ]
    if row["explanation"]:
        lines.append(f"Why: {row['explanation']}")
    lines.append(f"→ {verdict}: {row['url']}")
    return "\n".join(lines)


def run() -> int:
    rows = db.unalerted_matches(config.ALERT_SCORE)
    sent = 0
    for row in rows:
        if slack_service.send_dm(format_alert(row)):
            db.mark_alerted(row["job_id"])
            sent += 1
    print(f"  sent {sent} alerts")
    return sent
