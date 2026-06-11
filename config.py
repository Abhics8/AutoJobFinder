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
def resume_variants() -> dict[str, str]:
    return {p.stem.removeprefix("resume_"): p.name
            for p in sorted(DATA_DIR.glob("*.pdf"))}

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ═══════════════════════════════════════════════════════════════════
# SOURCES — Big Tech, Finance, and top-tier companies
# ═══════════════════════════════════════════════════════════════════

# Greenhouse boards (public API, free, no auth)
GREENHOUSE_BOARDS = [
    # Big Tech / FAANG
    "airbnb", "doordash", "figma", "notion", "discord",
    "twitch", "pinterest", "lyft", "instacart", "snap",
    "bytedance", "tiktok", "reddit", "dropbox", "stripe",
    "databricks", "snowflakecomputing", "cockroachlabs",
    "robinhood", "plaid", "brex", "ramp", "chime",
    "spotifyforjobs", "wayfair",
    # AI / ML focused
    "openai", "anthropic", "scale", "huggingface",
    "cohere", "deepmind",
    # Finance / Fintech
    "citadel", "twosigma", "deshaw", "point72",
    "bloomberg", "blackrock",
]

# Lever boards (public API, free, no auth)
LEVER_BOARDS = [
    "palantir", "anduril", "netflix",
    "nerdwallet", "sofi", "affirm",
]

# JSearch queries — covers LinkedIn, Indeed, Glassdoor.
# Covers companies with custom ATSs: Google, Meta, Amazon, Microsoft,
# Apple, Goldman Sachs, JPMorgan, Capital One, Uber, Deloitte.
# Free tier = 100 req/month → 7 queries × 1 run/day = ~210/month (upgrade
# to Basic $10/mo for 500 req, or reduce to 3 queries to fit free tier).
JSEARCH_QUERIES = [
    "machine learning engineer",
    "data engineer",
    "software engineer new grad",
    "data scientist",
    "AI engineer",
    "data analyst",
    "ML engineer finance",
]
JSEARCH_LOCATION = "Washington, DC"
JSEARCH_RADIUS = 50  # miles — covers Arlington 22202 + DC + nearby VA/MD

# ═══════════════════════════════════════════════════════════════════
# LOCATION PREFERENCES — prioritize jobs near you
# ═══════════════════════════════════════════════════════════════════

# Preferred locations get a score boost; others are still shown but ranked lower.
PREFERRED_LOCATIONS = [
    "arlington", "22202",
    "washington", "d.c.", "dc",
    "new york", "nyc", "manhattan", "brooklyn",
    "remote",
]
LOCATION_BOOST = 0.05  # +5% score for preferred locations

# ═══════════════════════════════════════════════════════════════════
# COMPANY PREFERENCES — tier-based scoring boost
# ═══════════════════════════════════════════════════════════════════

# Tier 1: MAANG + Big Tech + Top Finance → +8% score boost
TIER1_COMPANIES = [
    # MAANG
    "meta", "amazon", "apple", "netflix", "google", "alphabet",
    # Big Tech
    "microsoft", "uber", "nvidia", "salesforce", "oracle", "adobe",
    "tesla", "ibm", "intel", "qualcomm", "cisco", "samsung",
    # AI leaders
    "openai", "anthropic", "deepmind",
    # Top finance / Wall Street
    "goldman sachs", "jpmorgan", "jp morgan", "morgan stanley",
    "citadel", "two sigma", "de shaw", "jane street",
]

# Tier 2: Fortune 500, strong tech, fintech, consulting, startups → +5%
TIER2_COMPANIES = [
    # Fortune 500 — Tech
    "hewlett packard", "hpe", "dell", "vmware", "accenture",
    "infosys", "cognizant", "tcs", "wipro", "capgemini",
    "atlassian", "servicenow", "workday", "twilio", "intuit",
    "autodesk", "synopsys", "cadence", "broadcom", "amd",
    "micron", "western digital", "seagate", "netapp", "arista",
    "fortinet", "palo alto networks", "crowdstrike", "zscaler",
    "okta", "veeva", "splunk", "teradata",
    # Fortune 500 — Finance / Insurance
    "capital one", "bank of america", "boa", "wells fargo",
    "citi", "citigroup", "barclays", "hsbc", "deutsche bank",
    "bnp paribas", "ubs", "credit suisse",
    "visa", "mastercard", "american express", "paypal",
    "fidelity", "charles schwab", "vanguard", "blackrock",
    "state street", "northern trust",
    "aig", "metlife", "prudential", "allstate", "progressive",
    "travelers", "liberty mutual", "nationwide",
    # Fortune 500 — Consulting / Big 4
    "deloitte", "pwc", "pricewaterhousecoopers", "ey", "ernst & young",
    "kpmg", "mckinsey", "bain", "bcg", "boston consulting",
    "booz allen", "leidos", "saic", "raytheon", "lockheed martin",
    "northrop grumman", "general dynamics", "bah",
    # Fortune 500 — Healthcare / Pharma / Biotech
    "unitedhealth", "anthem", "elevance", "cigna", "humana", "cvs",
    "johnson & johnson", "j&j", "pfizer", "abbvie", "merck",
    "eli lilly", "bristol-myers", "amgen", "gilead", "regeneron",
    "moderna", "biogen", "illumina",
    # Fortune 500 — Retail / Consumer / Media
    "walmart", "target", "costco", "kroger", "home depot", "lowes",
    "nike", "starbucks", "mcdonald", "disney", "comcast", "warner",
    "paramount", "fox", "nbc",
    # Fortune 500 — Energy / Industrial / Logistics
    "exxon", "chevron", "conocophillips", "ge", "general electric",
    "honeywell", "3m", "caterpillar", "deere", "john deere",
    "ups", "fedex", "boeing", "airbus",
    # Growth tech / Pre-IPO
    "stripe", "databricks", "snowflake", "airbnb", "doordash",
    "palantir", "spotify", "pinterest", "lyft", "snap",
    "bytedance", "tiktok", "reddit", "dropbox", "figma",
    "notion", "discord", "anduril", "scale ai",
    "datadog", "elastic", "confluent", "hashicorp",
    "mongodb", "cloudflare", "vercel",
    "bloomberg",
    # Fintech
    "robinhood", "plaid", "coinbase", "ramp", "brex", "chime",
    "sofi", "affirm", "square", "block", "marqeta", "toast",
    "bill.com", "adyen", "klarna", "nubank",
    # Hot startups
    "instacart", "wayfair", "grammarly", "duolingo", "canva",
    "airtable", "rippling", "gusto", "deel", "retool",
    "linear", "supabase", "nerdwallet",
]

TIER1_BOOST = 0.08
TIER2_BOOST = 0.05

# ═══════════════════════════════════════════════════════════════════
# TITLE FILTERS
# ═══════════════════════════════════════════════════════════════════

TITLE_KEYWORDS = [
    "machine learning", "ml engineer", "data engineer", "data scientist",
    "data analyst", "software engineer", "swe", "ai engineer", "full stack",
    "backend engineer", "platform engineer", "applied scientist",
    "research engineer", "quantitative", "analytics engineer",
]
TITLE_EXCLUDE = ["staff", "principal", "director", "manager", "vp",
                 "head of", "10+", "lead", "architect"]

# ═══════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════

SIMILARITY_WEIGHT = 0.6
SKILL_COVERAGE_WEIGHT = 0.4
MIN_SCORE = 0.70
ALERT_SCORE = 0.80
PRIORITY_SCORE = 0.90

SKILLS = [
    "python", "java", "c++", "sql", "scala", "go", "typescript", "javascript",
    "pytorch", "tensorflow", "scikit-learn", "spark", "kafka", "airflow",
    "dbt", "snowflake", "databricks", "aws", "gcp", "azure", "docker",
    "kubernetes", "mlops", "llm", "nlp", "computer vision", "react",
    "next.js", "fastapi", "flask", "postgresql", "mongodb", "redis",
    "tableau", "power bi", "pandas", "numpy", "etl", "ci/cd", "terraform",
    "ray", "mlflow", "sagemaker", "hugging face", "langchain", "hadoop",
    "flink", "elasticsearch", "graphql", "rust",
]
