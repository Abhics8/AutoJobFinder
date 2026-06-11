# job_finder — Autonomous Personal Job Matching System

Fetches jobs from Greenhouse, Lever, and JSearch (LinkedIn/Indeed aggregate),
scores them against 6 resume variants using local embeddings, and DMs you on
Slack when a job scores ≥80% fit. Runs on cron every 6 hours. Cost: $0
(plus optional ~$5/mo Claude API for borderline-match explanations).

## Setup (30 min, one time)

1. **Resumes**: drop your 6 PDFs into `data/` named exactly:
   `resume_MLE.pdf`, `resume_SWE.pdf`, `resume_DA.pdf`, `resume_DE.pdf`,
   `resume_DS.pdf`, `resume_FullStack.pdf`
2. **Run setup**: `./setup.sh` — creates venv, installs deps, downloads the
   embedding model (~90MB), embeds your resumes.
3. **API keys** in `.env`:
   - `JSEARCH_API_KEY` — reuse your key from `~/job-monitor` (RapidAPI JSearch,
     free tier 100 req/month; the 3 configured queries × 1 run/day fits).
   - `SLACK_BOT_TOKEN` + `SLACK_USER_ID` — create a Slack app at
     api.slack.com/apps, add the `chat:write` bot scope, install to workspace.
     Without these, alerts print to console/cron.log instead.
   - `ANTHROPIC_API_KEY` — optional, enables Phase-2 LLM explanations.
4. **Test**: `venv/bin/python main.py`
5. **Cron** (`crontab -e`):
   ```
   0 8 * * * cd ~/job_finder && venv/bin/python main.py >> cron.log 2>&1
   ```
   Note: JSearch free tier only supports ~3 queries/day, so 1 run/day for
   JSearch. Greenhouse/Lever are free — run every 6h if you want by adding
   a second cron line; the fetcher dedupes.

## How scoring works

`final = 0.6 × cosine_similarity(JD, best_resume) + 0.4 × skill_coverage`

- `< 70%` — archived silently
- `70–85%` — stored; Analyzer (if enabled) writes a short LLM explanation
- `≥ 80%` — Slack alert ✅
- `≥ 90%` — priority alert 🔥

Tune weights/thresholds in [config.py](config.py). Re-run `./setup.sh` after
updating a resume PDF (it re-embeds only changed files).

## Important reality checks vs. the original design

- **LinkedIn has no public job-search API** for individuals; JSearch covers
  LinkedIn + Indeed postings legally via RapidAPI.
- **GS / JPMorgan / Capital One use custom ATSs**, not Greenhouse — JSearch
  picks up their postings. Greenhouse/Lever boards in config are for
  companies with public boards (edit `GREENHOUSE_BOARDS` / `LEVER_BOARDS`).
- **FAISS dropped**: with 6 resume vectors, a numpy dot product is identical
  and removes a dependency.

## Layout

```
main.py            orchestrator (fetch → match → analyze → alert)
agents/            fetcher, matcher, analyzer (Phase 2), alerter
services/          embeddings (sentence-transformers), slack
db.py              SQLite: jobs, matches, alerts
config.py          keys, sources, skills list, score thresholds
data/              your resume PDFs (gitignore these)
embeddings/        cached resume vectors + extracted text
```

## Tracking applications (Phase 2, week 4)

After applying, record it so precision can be measured:
```sql
UPDATE alerts SET user_response='applied' WHERE job_id='...';
```
Target: >70% of alerted jobs are worth applying to. If you're ignoring
alerts, raise `ALERT_SCORE` in config.py.
