"""Fetcher agent: pull jobs from Greenhouse, Lever, and JSearch; dedupe into SQLite."""
import hashlib
import html
import re

import requests

import config
import db

TIMEOUT = 20


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", " ", text)


def _title_ok(title: str) -> bool:
    t = title.lower()
    if any(x in t for x in config.TITLE_EXCLUDE):
        return False
    return any(k in t for k in config.TITLE_KEYWORDS)


def fetch_greenhouse(board: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        if not _title_ok(j.get("title", "")):
            continue
        jobs.append({
            "job_id": f"gh_{board}_{j['id']}",
            "source": "greenhouse",
            "title": j["title"],
            "company": board.title(),
            "posted_date": (j.get("updated_at") or "")[:10],
            "description": _clean(j.get("content", "")),
            "url": j.get("absolute_url"),
            "location": (j.get("location") or {}).get("name", ""),
            "remote": "remote" in str(j.get("location", "")).lower(),
        })
    return jobs


def fetch_lever(board: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json():
        if not _title_ok(j.get("text", "")):
            continue
        jobs.append({
            "job_id": f"lv_{board}_{j['id']}",
            "source": "lever",
            "title": j["text"],
            "company": board.title(),
            "posted_date": None,
            "description": _clean(j.get("descriptionPlain") or j.get("description", "")),
            "url": j.get("hostedUrl"),
            "location": (j.get("categories") or {}).get("location", ""),
            "remote": "remote" in str(j.get("workplaceType", "")).lower(),
        })
    return jobs


def fetch_ashby(board: str) -> list[dict]:
    """Ashby public job-board API — covers many startups/scaleups."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        if not _title_ok(j.get("title", "")):
            continue
        jobs.append({
            "job_id": f"ash_{board}_{j.get('id', hashlib.md5(j['title'].encode()).hexdigest())}",
            "source": "ashby",
            "title": j["title"],
            "company": board.replace("-", " ").title(),
            "posted_date": (j.get("publishedAt") or "")[:10],
            "description": _clean(j.get("descriptionPlain") or j.get("descriptionHtml", "")),
            "url": j.get("jobUrl") or j.get("applyUrl"),
            "location": j.get("location", ""),
            "remote": bool(j.get("isRemote")),
        })
    return jobs


def fetch_jsearch(query: str) -> list[dict]:
    """JSearch (RapidAPI) aggregates LinkedIn/Indeed/Glassdoor postings."""
    if not config.JSEARCH_API_KEY:
        return []
    r = requests.get(
        "https://jsearch.p.rapidapi.com/search",
        headers={
            "X-RapidAPI-Key": config.JSEARCH_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        },
        params={"query": f"{query} in {config.JSEARCH_LOCATION}",
                "date_posted": "3days", "num_pages": 1},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    jobs = []
    for j in r.json().get("data", []):
        title = j.get("job_title", "")
        if not _title_ok(title):
            continue
        raw_id = j.get("job_id") or hashlib.md5(
            (title + j.get("employer_name", "")).encode()).hexdigest()
        jobs.append({
            "job_id": f"js_{raw_id}",
            "source": "jsearch",
            "title": title,
            "company": j.get("employer_name", ""),
            "posted_date": (j.get("job_posted_at_datetime_utc") or "")[:10],
            "description": j.get("job_description", ""),
            "url": j.get("job_apply_link"),
            "location": f"{j.get('job_city') or ''}, {j.get('job_state') or ''}".strip(", "),
            "remote": bool(j.get("job_is_remote")),
        })
    return jobs


def run() -> int:
    """Fetch all sources in parallel, insert new jobs. Returns count of new jobs.

    Greenhouse/Lever/Ashby are free public APIs, so we monitor hundreds of
    company boards concurrently — invalid/empty boards just fail gracefully.
    """
    from concurrent.futures import ThreadPoolExecutor

    sources = (
        [("greenhouse:" + b, lambda b=b: fetch_greenhouse(b)) for b in config.GREENHOUSE_BOARDS]
        + [("lever:" + b, lambda b=b: fetch_lever(b)) for b in config.LEVER_BOARDS]
        + [("ashby:" + b, lambda b=b: fetch_ashby(b)) for b in config.ASHBY_BOARDS]
    )
    # JSearch has a 100-req/month free quota, so run it at most once a day —
    # the free ATS sources above run every cycle. Keeps LinkedIn/Indeed
    # coverage (Google/Meta/Amazon/Goldman) alive long-term instead of burning out.
    if config.JSEARCH_API_KEY and db.hours_since_source("jsearch") >= 20:
        sources += [("jsearch:" + q, lambda q=q: fetch_jsearch(q)) for q in config.JSEARCH_QUERIES]

    def safe(item):
        name, fn = item
        try:
            return name, fn(), None
        except Exception as e:
            return name, [], str(e)

    # Network fetches run in parallel (I/O-bound); DB inserts stay single-threaded.
    new = total = ok_boards = errors = 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        for name, jobs, err in pool.map(safe, sources):
            if err:
                errors += 1
                continue
            if jobs:
                ok_boards += 1
                total += len(jobs)
                new += sum(db.insert_job(j) for j in jobs)
    print(f"  {len(sources)} boards scanned · {ok_boards} with hits · "
          f"{total} jobs · {new} new · {errors} skipped")
    return new
