"""Local web dashboard: browse matches, run cycles, track applications.

Usage: venv/bin/python web.py  ->  http://localhost:8000
"""
import threading

from flask import Flask, redirect, render_template_string, request

import config
import db
import main as orchestrator

app = Flask(__name__)
_cycle_lock = threading.Lock()
_cycle_status = {"running": False, "last": None}

PAGE = """
<!doctype html><html><head><meta charset="utf-8">
<title>AutoJobFinder</title>
<meta http-equiv="refresh" content="{{ 15 if running else 3600 }}">
<style>
  body { font-family: -apple-system, sans-serif; margin: 0; background: #f5f6f8; color: #1a1d23; }
  header { background: #1a1d23; color: #fff; padding: 16px 28px; display: flex; align-items: center; gap: 20px; }
  header h1 { font-size: 18px; margin: 0; flex: 1; }
  .stats { display: flex; gap: 14px; padding: 18px 28px 0; flex-wrap: wrap; }
  .stat { background: #fff; border-radius: 10px; padding: 12px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .stat b { font-size: 22px; display: block; }
  .stat span { font-size: 12px; color: #6b7280; }
  main { padding: 18px 28px; }
  .job { background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
         box-shadow: 0 1px 3px rgba(0,0,0,.08); display: flex; gap: 16px; align-items: flex-start; }
  .score { font-size: 20px; font-weight: 700; min-width: 64px; text-align: center;
           padding: 8px 0; border-radius: 8px; }
  .hot { background: #fee2e2; color: #b91c1c; } .good { background: #dcfce7; color: #15803d; }
  .ok  { background: #fef9c3; color: #a16207; }
  .job h3 { margin: 0 0 4px; font-size: 15px; }
  .meta { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
  .skills { font-size: 12px; } .skills b { color: #15803d; } .skills i { color: #b91c1c; font-style: normal; }
  .body { flex: 1; }
  .actions { display: flex; flex-direction: column; gap: 6px; }
  .btn { padding: 6px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px;
         text-decoration: none; text-align: center; }
  .apply { background: #2563eb; color: #fff; } .applied { background: #15803d; color: #fff; }
  .skip { background: #e5e7eb; color: #374151; }
  .run { background: #2563eb; color: #fff; padding: 8px 18px; border-radius: 8px; border: none;
         cursor: pointer; font-size: 14px; }
  .run[disabled] { background: #6b7280; }
  .tag { font-size: 11px; background: #eef2ff; color: #4338ca; padding: 2px 8px; border-radius: 10px; }
  .filters a { margin-right: 10px; font-size: 13px; }
</style></head><body>
<header>
  <h1>🎯 AutoJobFinder</h1>
  {% if running %}<span>⏳ cycle running… page auto-refreshes</span>{% endif %}
  <form method="post" action="/run"><button class="run" {{ 'disabled' if running }}>▶ Run cycle now</button></form>
</header>
<div class="stats">
  <div class="stat"><b>{{ stats.jobs }}</b><span>jobs fetched (7d)</span></div>
  <div class="stat"><b>{{ stats.matches }}</b><span>matches ≥ {{ '%d'|format(min_score*100) }}%</span></div>
  <div class="stat"><b>{{ stats.applied }}</b><span>applied</span></div>
  <div class="stat"><b>{{ stats.last or '–' }}</b><span>last cycle</span></div>
</div>
<main>
  <p class="filters">
    <a href="/">All matches</a> <a href="/?f=hot">≥90% 🔥</a>
    <a href="/?f=applied">Applied</a> <a href="/?f=all">Everything incl. &lt;{{ '%d'|format(min_score*100) }}%</a>
  </p>
  {% for j in jobs %}
  <div class="job">
    <div class="score {{ 'hot' if j.final_score >= 0.9 else 'good' if j.final_score >= 0.8 else 'ok' }}">
      {{ '%d'|format(j.final_score*100) }}%</div>
    <div class="body">
      <h3>{{ j.company }} — {{ j.title }} <span class="tag">{{ j.best_resume_variant }} resume</span></h3>
      <div class="meta">{{ j.location or 'n/a' }}{{ ' · Remote' if j.remote }} · {{ j.source }}
        · posted {{ j.posted_date or '?' }}</div>
      <div class="skills">
        <b>✓ {{ j.matched_skills.replace(',', ', ') or '—' }}</b><br>
        {% if j.missing_skills %}<i>✗ missing: {{ j.missing_skills.replace(',', ', ') }}</i>{% endif %}
      </div>
      {% if j.explanation %}<div class="skills" style="margin-top:6px">💡 {{ j.explanation }}</div>{% endif %}
    </div>
    <div class="actions">
      <a class="btn apply" href="{{ j.url }}" target="_blank">Open posting ↗</a>
      {% if j.user_response == 'applied' %}
        <span class="btn applied">✓ Applied</span>
      {% else %}
        <form method="post" action="/respond"><input type="hidden" name="job_id" value="{{ j.job_id }}">
          <button class="btn applied" name="response" value="applied">Mark applied</button>
          <button class="btn skip" name="response" value="ignored">Skip</button></form>
      {% endif %}
    </div>
  </div>
  {% else %}<p>No matches yet — drop resumes in data/, then hit “Run cycle now”.</p>{% endfor %}
</main></body></html>
"""


def query_jobs(flt: str):
    where, params = "m.final_score >= ?", [config.MIN_SCORE]
    if flt == "hot":
        where, params = "m.final_score >= ?", [config.PRIORITY_SCORE]
    elif flt == "applied":
        where, params = "a.user_response = 'applied'", []
    elif flt == "all":
        where, params = "1=1", []
    with db.connect() as conn:
        return conn.execute(
            f"""SELECT j.*, m.*, a.user_response FROM matches m
                JOIN jobs j ON j.job_id = m.job_id
                LEFT JOIN alerts a ON a.job_id = m.job_id
                WHERE {where} AND (a.user_response IS NULL OR a.user_response != 'ignored'
                                   OR ? = 'all')
                ORDER BY m.final_score DESC LIMIT 200""",
            params + [flt],
        ).fetchall()


@app.route("/")
def index():
    flt = request.args.get("f", "")
    with db.connect() as conn:
        stats = {
            "jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE fetched_at > datetime('now','-7 days')").fetchone()[0],
            "matches": conn.execute("SELECT COUNT(*) FROM matches WHERE final_score >= ?", (config.MIN_SCORE,)).fetchone()[0],
            "applied": conn.execute("SELECT COUNT(*) FROM alerts WHERE user_response='applied'").fetchone()[0],
            "last": _cycle_status["last"],
        }
    return render_template_string(PAGE, jobs=query_jobs(flt), stats=stats,
                                  running=_cycle_status["running"],
                                  min_score=config.MIN_SCORE)


@app.route("/run", methods=["POST"])
def run_cycle():
    def task():
        from datetime import datetime
        with _cycle_lock:
            _cycle_status["running"] = True
            try:
                orchestrator.run_cycle()
                _cycle_status["last"] = f"{datetime.now():%H:%M}"
            finally:
                _cycle_status["running"] = False
    if not _cycle_status["running"]:
        threading.Thread(target=task, daemon=True).start()
    return redirect("/")


@app.route("/respond", methods=["POST"])
def respond():
    job_id, response = request.form["job_id"], request.form["response"]
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO alerts (job_id, alerted_at, user_response)
               VALUES (?, datetime('now'), ?)
               ON CONFLICT(job_id) DO UPDATE SET user_response = excluded.user_response""",
            (job_id, response),
        )
    return redirect(request.referrer or "/")


if __name__ == "__main__":
    db.init()
    print("AutoJobFinder dashboard -> http://localhost:8000")
    app.run(port=8000, debug=False)
