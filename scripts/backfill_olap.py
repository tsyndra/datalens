#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import threading
import time
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import psycopg

from sync_iiko import IikoCloudSync, MSK, parse_date


REPO_ROOT = Path(__file__).resolve().parents[1]


def date_chunks(date_from: dt.date, date_to: dt.date, chunk_days: int) -> list[tuple[dt.date, dt.date]]:
    chunks: list[tuple[dt.date, dt.date]] = []
    cur = date_from
    while cur <= date_to:
        end = min(date_to, cur + dt.timedelta(days=chunk_days - 1))
        chunks.append((cur, end))
        cur = end + dt.timedelta(days=1)
    return chunks


ALLOWED_APPLICATIONS = {"olap_backfill", "olap_backfill_watchdog"}


def terminate_other_writers(database_url: str, stop_event: threading.Event, interval_seconds: float = 2.0) -> None:
    while not stop_event.is_set():
        with suppress(Exception):
            with psycopg.connect(database_url, application_name="olap_backfill_watchdog") as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND pid <> pg_backend_pid()
                          AND COALESCE(application_name, '') <> ALL(%s)
                        """,
                        (list(ALLOWED_APPLICATIONS),),
                    )
                conn.commit()
        stop_event.wait(interval_seconds)


def sync_chunk(index: int, total: int, date_from: dt.date, date_to: dt.date) -> dict[str, Any]:
    started = time.time()
    sync = IikoCloudSync()
    with psycopg.connect(sync.database_url, application_name="olap_backfill") as conn:
        print(f"[backfill] chunk {index}/{total} start {date_from}..{date_to}", flush=True)
        counts = sync.sync_olap_sales_marts(conn, date_from, date_to)
        conn.commit()
    elapsed = round(time.time() - started, 1)
    print(f"[backfill] chunk {index}/{total} done {date_from}..{date_to} elapsed={elapsed}s counts={counts}", flush=True)
    return {"index": index, "date_from": str(date_from), "date_to": str(date_to), "elapsed_seconds": elapsed, **counts}


def main() -> int:
    today = dt.datetime.now(MSK).date()
    parser = argparse.ArgumentParser(description="Parallel iikoServer OLAP backfill.")
    parser.add_argument("--date-from", type=parse_date, default=today.replace(year=today.year - 3) + dt.timedelta(days=1))
    parser.add_argument("--date-to", type=parse_date, default=today)
    parser.add_argument("--chunk-days", type=int, default=31)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--summary-path", default=str(REPO_ROOT / "data" / "olap_backfill_summary.jsonl"))
    parser.add_argument("--kill-other-db-sessions", action="store_true")
    args = parser.parse_args()

    if args.chunk_days < 1:
        raise SystemExit("--chunk-days must be >= 1")
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    chunks = date_chunks(args.date_from, args.date_to, args.chunk_days)
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    print(
        f"[backfill] OLAP range {args.date_from}..{args.date_to}; chunks={len(chunks)} chunk_days={args.chunk_days} workers={args.workers}",
        flush=True,
    )
    failures = 0
    stop_event = threading.Event()
    watchdog: threading.Thread | None = None
    if args.kill_other_db_sessions:
        database_url = IikoCloudSync().database_url
        watchdog = threading.Thread(target=terminate_other_writers, args=(database_url, stop_event), daemon=True)
        watchdog.start()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(sync_chunk, index, len(chunks), start, end): (index, start, end)
            for index, (start, end) in enumerate(chunks, 1)
        }
        for future in as_completed(futures):
            index, start, end = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                result = {"index": index, "date_from": str(start), "date_to": str(end), "error": str(exc)}
                print(f"[backfill] chunk {index}/{len(chunks)} failed {start}..{end}: {exc}", file=sys.stderr, flush=True)
            with lock:
                with summary_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    stop_event.set()
    if watchdog:
        watchdog.join(timeout=5)
    print(f"[backfill] finished failures={failures} summary={summary_path}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
