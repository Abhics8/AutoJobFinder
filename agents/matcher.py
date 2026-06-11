"""Matcher agent: score unmatched jobs against pre-embedded resume variants."""
import re

import numpy as np

import config
import db
from services import embeddings


def extract_skills(text: str) -> set[str]:
    t = text.lower()
    found = set()
    for skill in config.SKILLS:
        # word-boundary match so "go" doesn't hit "google"
        if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", t):
            found.add(skill)
    return found


def _location_boost(location: str) -> float:
    loc = (location or "").lower()
    return config.LOCATION_BOOST if any(p in loc for p in config.PREFERRED_LOCATIONS) else 0.0


def _company_boost(company: str) -> float:
    c = (company or "").lower()
    if any(t in c for t in config.TIER1_COMPANIES):
        return config.TIER1_BOOST
    if any(t in c for t in config.TIER2_COMPANIES):
        return config.TIER2_BOOST
    return 0.0


def score_job(job_text: str, resume_vectors: dict, resume_skills: dict,
              company: str = "", location: str = "") -> dict:
    job_vec = embeddings.embed_text(job_text)
    sims = {v: float(np.dot(job_vec, vec)) for v, vec in resume_vectors.items()}
    best = max(sims, key=sims.get)
    cos = sims[best]

    jd_skills = extract_skills(job_text)
    matched = jd_skills & resume_skills[best]
    missing = jd_skills - resume_skills[best]
    coverage = len(matched) / len(jd_skills) if jd_skills else 0.5

    base = config.SIMILARITY_WEIGHT * cos + config.SKILL_COVERAGE_WEIGHT * coverage
    loc_b = _location_boost(location)
    comp_b = _company_boost(company)
    final = min(base + loc_b + comp_b, 1.0)

    return {
        "best_resume_variant": best,
        "cosine_similarity": round(cos, 3),
        "skill_coverage": round(coverage, 3),
        "final_score": round(final, 3),
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
    }


def run() -> int:
    """Score all unmatched jobs. Returns count of jobs >= MIN_SCORE."""
    resume_vectors = embeddings.load_resume_vectors()
    if not resume_vectors:
        print("  No resume embeddings found — run setup.sh first.")
        return 0
    resume_skills = {v: extract_skills(embeddings.load_resume_text(v))
                     for v in resume_vectors}

    qualified = 0
    jobs = db.unmatched_jobs()
    for job in jobs:
        text = f"{job['title']}\n{job['description'] or ''}"
        result = score_job(text, resume_vectors, resume_skills,
                           company=job["company"], location=job["location"])
        result["job_id"] = job["job_id"]
        db.insert_match(result)
        if result["final_score"] >= config.MIN_SCORE:
            qualified += 1
    print(f"  scored {len(jobs)} jobs, {qualified} >= {config.MIN_SCORE:.0%}")
    return qualified
