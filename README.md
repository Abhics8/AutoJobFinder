# AutoJobFinder — Autonomous Personal Job Matching System

**Live dashboard:** [huggingface.co/spaces/Ab0202000/AutoJobFinder](https://huggingface.co/spaces/Ab0202000/AutoJobFinder) (private — log in as `Ab0202000`)

Fetches jobs from Greenhouse, Lever, and JSearch (LinkedIn/Indeed aggregate),
scores them against your resume variants using local embeddings, and alerts
when a job scores ≥80% fit. Runs automatically every 6 hours. Cost: $0
(plus optional ~$5/mo Claude API for borderline-match explanations).

## Current resume variants

Resume PDFs are auto-discovered from `data/`. Upload/delete via the dashboard's
**Resumes** tab — no code changes needed. Current variants:

| Variant | File | Target roles |
|---------|------|-------------|
| MLE | `resume_MLE.pdf` | Machine Learning Engineer |
| DE | `resume_DE.pdf` | Data Engineer |
| DA | `resume_DA.pdf` | Data Analyst |
| Generic | `resume_Generic.pdf` | General-purpose resume |

Add more anytime (SDE, DS, FullStack, Quant, …) — each job is scored against
every variant and matched to the best fit. The dashboard shows which resume
to use per job and lets you download it in one click.

## Setup (local, 30 min one-time)

1. **Clone & install**:
   ```bash
   cd ~/job_finder
   ./setup.sh
   ```
2. **API keys** in `.env`:
   - `JSEARCH_API_KEY` — RapidAPI JSearch (free tier, 100 req/month). Covers
     LinkedIn, Indeed, Glassdoor — and companies with custom ATSs (Goldman
     Sachs, JPMorgan, Capital One).
   - `SLACK_BOT_TOKEN` + `SLACK_USER_ID` — optional, for Slack DM alerts.
   - `ANTHROPIC_API_KEY` — optional, enables LLM explanations for borderline
     matches (70–85%).
3. **Test**: `venv/bin/python main.py`
4. **Dashboard**: `venv/bin/python web.py` → http://localhost:8000
5. **Cron** (optional, for hands-off local runs):
   ```
   0 8 * * * cd ~/job_finder && venv/bin/python main.py >> cron.log 2>&1
   ```

## How scoring works

`final = 0.6 × cosine_similarity(JD, best_resume) + 0.4 × skill_coverage`

- `< 70%` — archived silently
- `70–85%` — stored; Analyzer (if enabled) writes a short LLM explanation
- `≥ 80%` — Slack alert ✅ / dashboard highlight
- `≥ 90%` — priority alert 🔥

Tune weights/thresholds in [config.py](config.py).

## Hosted deployment (Hugging Face Space)

The dashboard is deployed as a private Docker Space on Hugging Face. It runs
fetch/match/alert cycles automatically every 6 hours — laptop can be off.

To redeploy after local changes:
```bash
venv/bin/python deploy_hf.py
```

Add API keys as secrets in [Space settings](https://huggingface.co/spaces/Ab0202000/AutoJobFinder/settings) → Variables and secrets.

## Layout

```
main.py            orchestrator (fetch → match → analyze → alert)
web.py             Flask dashboard (matches, resumes, tracking)
agents/            fetcher, matcher, analyzer, alerter
services/          embeddings (sentence-transformers), slack
db.py              SQLite: jobs, matches, alerts
config.py          keys, sources, skills list, score thresholds
data/              resume PDFs (auto-discovered, gitignored)
embeddings/        cached resume vectors + extracted text
```

## Job sources

| Source | Method | Coverage |
|--------|--------|----------|
| Greenhouse | Public board API | Stripe, Databricks, Robinhood (configurable) |
| Lever | Public board API | Palantir (configurable) |
| JSearch | RapidAPI (free tier) | LinkedIn, Indeed, Glassdoor — GS, JPM, Uber, Capital One |

## Application tracking

Track applications directly from the dashboard — click **Mark applied** or
**Skip** on each job card. Stats at the top show jobs fetched, matches, and
applications. Target: >70% of alerted jobs are worth applying to; if not,
raise `ALERT_SCORE` in config.py.
