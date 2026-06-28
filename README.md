# AutoJobFinder — Autonomous Personal Job Matching & Routing System

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Hugging%20Face-blue?style=flat-square&logo=huggingface)](https://huggingface.co/spaces/Ab0202000/AutoJobFinder)
[![Python Version](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

An autonomous job hunting engine that aggregates postings across multiple ATS platforms and general aggregators, runs local semantic embedding-based matching against resume variants, evaluates skill coverage with exact boundary matching, applies multi-tier company and location boosts, generates LLM-powered fit explanations, and triggers instant alerts (Slack/Console) for qualified positions.

> [!NOTE]
> **Live dashboard:** Deployed privately at [huggingface.co/spaces/Ab0202000/AutoJobFinder](https://huggingface.co/spaces/Ab0202000/AutoJobFinder) (log in as `Ab0202000`).

---

## 🏗️ System Architecture

The following diagram illustrates the lifecycle of a job posting through the AutoJobFinder cycle:

```mermaid
graph TD
    A[Orchestrator: main.py] --> B[1. Fetcher Agent]
    B -->|Greenhouse API| C[Jobs DB]
    B -->|Lever API| C
    B -->|Ashby API| C
    B -->|JSearch API| C
    
    A --> D[2. Matcher Agent]
    C -->|Unmatched Jobs| D
    E[(Resume PDFs)] -->|sentence-transformers| F[Vector Embeddings Cache]
    F -->|Cosine Similarity| D
    D -->|Calculate Skill Coverage & Boosts| G[Matches Table]
    
    A --> H[3. Analyzer Agent]
    G -->|Borderline Matches 70-85%| H
    H -->|Batch LLM Call| I[Claude API]
    I -->|JSON Explanations| G
    
    A --> J[4. Alerter Agent]
    G -->|Final Score >= ALERT_SCORE| J
    J -->|Slack Direct Message| K[Slack Bot]
    J -->|Fallback Console Logs| L[Standard Output]
```

---

## ✨ Key Features

1. **Multi-Source ATS Fetcher**
   - **Greenhouse, Lever, & Ashby APIs:** Scans public job boards of hundreds of top tech companies, fintechs, and quant shops in parallel using `ThreadPoolExecutor` for concurrent network requests. Ashby covers high-signal AI startups (e.g., OpenAI, Perplexity, Notion).
   - **JSearch (LinkedIn, Indeed, Glassdoor aggregate):** Queries broad roles from companies using custom ATS portals (e.g., Google, Meta, Apple, Goldman Sachs, JPMorgan, Capital One).
   - **Smart Quota Management:** Run Ashby, Greenhouse, and Lever continuously on a cron, while JSearch requests are throttled to run once daily to stay comfortably within the 100-request/month free tier.

2. **Semantic & Keyword Matcher**
   - **Sentence Transformers:** Computes local embedding vectors of job descriptions using the `all-MiniLM-L6-v2` model. Runs entirely locally on CPU/GPU ($0 cost).
   - **Pre-computed Resumes:** Automatically extracts text from uploaded PDF variants, embeds them, and serializes them (`embeddings/*.pkl`) for instant lookup.
   - **Exact-Match Skill Coverage:** Evaluates exact occurrences of 50+ tech skills (e.g., PyTorch, Airflow, React, SQL, Go) using regex word boundary limits to avoid false-positives (e.g., "Go" matching "Google").

3. **Multi-Tier Scoring & Diversity Rank**
   - **Weighted Scoring Model:** 
     $$\text{Base Score} = (0.6 \times \text{Cosine Similarity}) + (0.4 \times \text{Skill Coverage})$$
     $$\text{Final Score} = \min(\text{Base Score} + \text{Location Boost} + \text{Company Boost}, 1.0)$$
   - **Location Boost (+5%):** Applied to jobs matching target locales (e.g., Washington DC, Arlington VA, NYC, Remote).
   - **Company Boost (+8% / +5%):** Tiered bonuses for MAANG, top AI labs, elite quant trading desks, and Fortune 500 tech leaders.
   - **Diversity Rank Sorting:** Uses SQLite window functions (`ROW_NUMBER() OVER (PARTITION BY company, posted_date)`) to interleave companies on the dashboard, preventing a single company's bulk-upload from overwhelming the feed.

4. **Claude-Powered Borderline Analyzer**
   - Evaluates jobs scoring in the `70% - 85%` range.
   - Explains the fit in 1–2 sentences and highlights missing competencies.
   - Batches up to 10 jobs per single Anthropic API call to minimize token costs (<$5/month).

5. **Alerter & Application Hub**
   - Sends real-time Slack DM notifications for high-priority matches (fit $\ge 87\%$, with special $\ge 92\%$ priority badges).
   - Local Flask dashboard shows matched jobs, missing skills, and dynamic explanation cards.
   - **One-Click Resume Route:** Serves the *exact* PDF resume variant matched to that specific role, pre-configured for instant download.

---

## 🗃️ Database Layout

The SQLite database (`jobs.db`) consists of three simple, indexed tables:

- **`jobs`**: Job postings fetched from various boards. Includes a `dedup_key` (slugified `company|title`) with a unique index to prevent duplicate listings across multiple regions or scrapes.
- **`matches`**: Resume matching results. Stores the best matching variant, scores (similarity/coverage/final), matched/missing skills, and the LLM analysis.
- **`alerts`**: Tracks Slack delivery dates and logs applicant status (`pending`, `applied`, or `ignored`).

---

## 📄 Resume Variants

Resumes are dynamically discovered from the `data/` folder (named `resume_[Variant].pdf`). Out-of-the-box support for:

| Variant | Filename | Target Role |
| :--- | :--- | :--- |
| **MLE** | `resume_MLE.pdf` | Machine Learning Engineer |
| **DE** | `resume_DE.pdf` | Data Engineer |
| **DA** | `resume_DA.pdf` | Data Analyst |
| **Generic** | `resume_Generic.pdf` | General-purpose SDE roles |

*To add new variants (e.g., `Quant`, `FullStack`), upload the PDF via the **Resumes** tab in the dashboard. The engine automatically indexes, embeds, and caches the new variant.*

---

## 🛠️ Setup Instructions (Local)

### 1. Installation
Clone the repository and run the setup script:
```bash
git clone https://github.com/Abhics8/AutoJobFinder.git
cd AutoJobFinder
./setup.sh
```
*Note: The setup script builds a virtual environment, installs dependencies, initializes the database, and downloads the SentenceTransformer model (~90MB).*

### 2. Environment Configuration
Populate `.env` with your API keys:
```env
# RapidAPI JSearch key (LinkedIn/Indeed/Glassdoor aggregates)
JSEARCH_API_KEY=your_jsearch_key_here

# Slack Integration (Optional)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_USER_ID=your-member-id

# Borderline Match Explanations (Optional)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

### 3. Run Pipeline Cycles
- **Run Fetch/Match Cycle:** `venv/bin/python main.py`
- **Start Web Dashboard:** `venv/bin/python web.py` (Navigate to `http://localhost:8000`)
- **Automated Scheduling:** Set up a cron task to run every 6 hours:
  ```cron
  0 */6 * * * cd ~/job_finder && venv/bin/python main.py >> cron.log 2>&1
  ```

---

## 🐳 Hosted Deployment (Hugging Face Spaces)

This repository is pre-configured for Docker-based deployment on **Hugging Face Spaces**:

1. **Deployment script:** Run `deploy_hf.py` to upload the code and resume data directly to your Space:
   ```bash
   venv/bin/python deploy_hf.py
   ```
2. **Persistent storage:** In the cloud, the database matches are saved to persistent disk via the `JOB_DATA_DIR` environment variable.
3. **Automatic cycle scheduler:** The web application automatically spins up a background thread scheduler (`AUTO_CYCLE=1`) to perform checks every 6 hours, allowing complete hands-off operations without a local machine running.
4. Add all keys from your `.env` as variables in the Hugging Face Space Settings panel.

---

## ⚙️ Customization & Tuning

All parameters are configured in [`config.py`](config.py):
- **Scoring Weights:** Tune `SIMILARITY_WEIGHT` and `SKILL_COVERAGE_WEIGHT`.
- **Score Thresholds:** Adjust `MIN_SCORE` (default: 0.78), `ALERT_SCORE` (default: 0.87), and `PRIORITY_SCORE` (default: 0.92).
- **Target Lists:** Customize `PREFERRED_LOCATIONS`, `TIER1_COMPANIES`, `TIER2_COMPANIES`, and the base `SKILLS` array to fit your technical background.
