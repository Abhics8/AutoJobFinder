"""Orchestrator: one full cycle of fetch -> match -> alert. Run via cron."""
import sys
from datetime import datetime

import db
from agents import alerter, analyzer, fetcher, matcher


def run_cycle():
    print(f"=== job_finder cycle @ {datetime.now():%Y-%m-%d %H:%M} ===")
    db.init()
    print("[1/4] Fetcher")
    new = fetcher.run()
    print("[2/4] Matcher")
    matcher.run()
    print("[3/4] Analyzer")
    analyzer.run()
    print("[4/4] Alerter")
    sent = alerter.run()
    print(f"=== done: {new} new jobs, {sent} alerts ===")


if __name__ == "__main__":
    try:
        run_cycle()
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
