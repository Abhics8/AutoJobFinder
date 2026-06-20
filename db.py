"""SQLite schema and helpers. Tables: jobs, matches, alerts."""
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    posted_date TEXT,
    description TEXT,
    url TEXT,
    location TEXT,
    remote INTEGER DEFAULT 0,
    fetched_at TEXT NOT NULL,
    dedup_key TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
CREATE TABLE IF NOT EXISTS matches (
    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
    best_resume_variant TEXT,
    cosine_similarity REAL,
    skill_coverage REAL,
    final_score REAL,
    matched_skills TEXT,
    missing_skills TEXT,
    explanation TEXT,
    matched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
    alerted_at TEXT NOT NULL,
    user_response TEXT DEFAULT 'pending'
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as conn:
        # Migrate pre-dedup_key databases before applying schema/index.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if cols and "dedup_key" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN dedup_key TEXT")
        conn.executescript(SCHEMA)


def _dedup_key(company: str, title: str) -> str:
    """Collapse the same role posted across multiple locations/IDs."""
    norm = lambda s: re.sub(r"[^a-z0-9]+", "", (s or "").lower())
    return f"{norm(company)}|{norm(title)}"


def insert_job(job: dict) -> bool:
    """Insert a job. Returns True if new, False if duplicate (id or content)."""
    with connect() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO jobs
               (job_id, source, title, company, posted_date, description,
                url, location, remote, fetched_at, dedup_key)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (job["job_id"], job["source"], job["title"], job["company"],
             job.get("posted_date"), job.get("description", ""),
             job.get("url"), job.get("location"),
             int(bool(job.get("remote"))), datetime.now().isoformat(),
             _dedup_key(job["company"], job["title"])),
        )
        return cur.rowcount > 0


def hours_since_source(source: str) -> float:
    """Hours since a source last produced a job. Large number if never."""
    with connect() as conn:
        row = conn.execute(
            "SELECT MAX(fetched_at) FROM jobs WHERE source = ?", (source,)
        ).fetchone()
    if not row or not row[0]:
        return 1e9
    return (datetime.now() - datetime.fromisoformat(row[0])).total_seconds() / 3600


def unmatched_jobs() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """SELECT j.* FROM jobs j
               LEFT JOIN matches m ON j.job_id = m.job_id
               WHERE m.job_id IS NULL"""
        ).fetchall()


def insert_match(m: dict):
    with connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO matches
               (job_id, best_resume_variant, cosine_similarity, skill_coverage,
                final_score, matched_skills, missing_skills, explanation, matched_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (m["job_id"], m["best_resume_variant"], m["cosine_similarity"],
             m["skill_coverage"], m["final_score"],
             ",".join(m["matched_skills"]), ",".join(m["missing_skills"]),
             m.get("explanation"), datetime.now().isoformat()),
        )


def unalerted_matches(min_score: float) -> list[sqlite3.Row]:
    """Matches above min_score not alerted in the last 7 days."""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    with connect() as conn:
        return conn.execute(
            """SELECT j.*, m.* FROM matches m
               JOIN jobs j ON j.job_id = m.job_id
               LEFT JOIN alerts a ON a.job_id = m.job_id
               WHERE m.final_score >= ?
                 AND (a.job_id IS NULL OR a.alerted_at < ?)""",
            (min_score, cutoff),
        ).fetchall()


def mark_alerted(job_id: str):
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO alerts (job_id, alerted_at) VALUES (?, ?)",
            (job_id, datetime.now().isoformat()),
        )
