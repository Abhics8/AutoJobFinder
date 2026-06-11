"""Central configuration: API keys, sources, scoring thresholds."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# On hosted platforms (HF Spaces persistent storage), set JOB_DATA_DIR=/data
_data_dir = Path(os.getenv("JOB_DATA_DIR", ROOT))
DB_PATH = _data_dir / "jobs.db"
DATA_DIR = ROOT / "data"
EMBEDDINGS_DIR = ROOT / "embeddings"

# --- API keys ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_USER_ID = os.getenv("SLACK_USER_ID", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Resume variants: discovered dynamically from PDFs in data/ ---
# Drop any number of PDFs in data/ (or upload via the dashboard's Resumes
# page); the variant name is the filename without the "resume_" prefix.
def resume_variants() -> dict[str, str]:
    return {p.stem.removeprefix("resume_"): p.name
            for p in sorted(DATA_DIR.glob("*.pdf"))}

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Sources ---
# Greenhouse/Lever board tokens for companies with public boards.
# Note: GS, JPMorgan, Capital One use custom ATSs — JSearch covers them.
GREENHOUSE_BOARDS = ["stripe", "databricks", "robinhood"]
LEVER_BOARDS = ["palantir"]

# JSearch queries (each costs 1 API request; free tier = 100/month,
# so 3 queries x 1 run/day = ~90/month)
JSEARCH_QUERIES = [
    "machine learning engineer new grad",
    "data engineer entry level",
    "software engineer new grad 2026",
]
JSEARCH_LOCATION = "Washington, DC"

# Title keywords a job must contain (case-insensitive) to be kept
TITLE_KEYWORDS = [
    "machine learning", "ml engineer", "data engineer", "data scientist",
    "data analyst", "software engineer", "swe", "ai engineer", "full stack",
]
# Seniority levels to exclude
TITLE_EXCLUDE = ["staff", "principal", "director", "manager", "vp", "head of", "10+"]

# --- Scoring ---
SIMILARITY_WEIGHT = 0.6
SKILL_COVERAGE_WEIGHT = 0.4
MIN_SCORE = 0.70        # below: archive silently
ALERT_SCORE = 0.80      # above: Slack alert
PRIORITY_SCORE = 0.90   # above: priority alert

# Skills looked for in JDs and resumes (extend freely)
SKILLS = [
    "python", "java", "c++", "sql", "scala", "go", "typescript", "javascript",
    "pytorch", "tensorflow", "scikit-learn", "spark", "kafka", "airflow",
    "dbt", "snowflake", "databricks", "aws", "gcp", "azure", "docker",
    "kubernetes", "mlops", "llm", "nlp", "computer vision", "react",
    "next.js", "fastapi", "flask", "postgresql", "mongodb", "redis",
    "tableau", "power bi", "pandas", "numpy", "etl", "ci/cd", "terraform",
]
