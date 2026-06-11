"""Analyzer agent (Phase 2): LLM explanations for borderline matches (70-85%).

Skipped automatically unless ANTHROPIC_API_KEY is set. Batches up to 10 jobs
per call to keep cost under ~$5/month.
"""
import json

import config
import db


def run() -> int:
    if not config.ANTHROPIC_API_KEY:
        return 0
    import anthropic

    with db.connect() as conn:
        rows = conn.execute(
            """SELECT j.title, j.company, m.* FROM matches m
               JOIN jobs j ON j.job_id = m.job_id
               WHERE m.final_score BETWEEN 0.70 AND 0.85
                 AND m.explanation IS NULL
               LIMIT 10"""
        ).fetchall()
    if not rows:
        return 0

    jobs_blob = json.dumps([
        {"job_id": r["job_id"], "title": r["title"], "company": r["company"],
         "score": r["final_score"], "matched": r["matched_skills"],
         "missing": r["missing_skills"], "resume": r["best_resume_variant"]}
        for r in rows
    ])
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1500,
        messages=[{"role": "user", "content":
            "For each job below, write a 1-2 sentence explanation of why it "
            "matched my resume and whether to apply. I'm an MS CS new grad "
            "(May 2026) targeting ML/Data/SWE roles. Return JSON: "
            '[{"job_id": ..., "explanation": ...}]\n\n' + jobs_blob}],
    )
    text = msg.content[0].text
    explanations = json.loads(text[text.index("["):text.rindex("]") + 1])

    with db.connect() as conn:
        for e in explanations:
            conn.execute("UPDATE matches SET explanation = ? WHERE job_id = ?",
                         (e["explanation"], e["job_id"]))
    print(f"  analyzed {len(explanations)} borderline jobs")
    return len(explanations)
