"""SQLite schema and helpers. Tables: jobs, matches, alerts."""
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
    fetched_at TEXT NOT NULL
);
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
        conn.executescript(SCHEMA)


def insert_job(job: dict) -> bool:
    """Insert a job. Returns True if new, False if duplicate."""
    with connect() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO jobs
               (job_id, source, title, company, posted_date, description,
                url, location, remote, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (job["job_id"], job["source"], job["title"], job["company"],
             job.get("posted_date"), job.get("description", ""),
             job.get("url"), job.get("location"),
             int(bool(job.get("remote"))), datetime.now().isoformat()),
        )
        return cur.rowcount > 0


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
