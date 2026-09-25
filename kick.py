#!/usr/bin/env python3
"""Wait for the next NSE slot on a public runner (free minutes), then kick the scan.

Tuesday and Thursday: every 15 minutes, including 15:10 and 15:15.
Monday, Wednesday, and Friday: every 30 minutes. No 15:10 or 15:15.
Every weekday ends with the 15:40 close scan.

Never stop at 15:40. After the last slot, hop in ≤5-hour sleeps until the next
trading day's 09:30. GitHub jobs time out at 6 hours, so overnight is several
public jobs. GitHub's own schedule is often skipped, so this chain is the clock.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, time as clock
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")
# Included private Actions minutes reset at 00:00 UTC on the 1st (05:30 IST).
PRIVATE_RESUME = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
PUBLIC_REPO = "AbhilashMunnur/nifty-index-scan"
PRIVATE_REPO = "AbhilashMunnur/nifty-index-trade"
SELF = os.environ.get("GITHUB_REPOSITORY", "AbhilashMunnur/nifty-scan-kick")
GRACE_SECONDS = 90
# GitHub-hosted jobs die at 6 hours. Stay under that.
MAX_SLEEP_SECONDS = 5 * 60 * 60

NSE_HOLIDAYS = {
    "2026-01-15",
    "2026-01-26",
    "2026-03-03",
    "2026-03-26",
    "2026-03-31",
    "2026-04-03",
    "2026-04-14",
    "2026-05-01",
    "2026-05-28",
    "2026-06-26",
    "2026-09-14",
    "2026-10-02",
    "2026-10-20",
    "2026-11-10",
    "2026-11-24",
    "2026-12-25",
}


def now_ist() -> datetime:
    return datetime.now(IST)


def target_repo(now: datetime | None = None) -> str:
    """Public copy until the private minute quota resets, then the old repo."""
    current = now if now is not None else datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)
    if current >= PRIVATE_RESUME:
        return PRIVATE_REPO
    return PUBLIC_REPO


def is_trading_day(as_of: date) -> bool:
    if as_of.weekday() >= 5:
        return False
    return as_of.isoformat() not in NSE_HOLIDAYS


def is_quarter_hour_day(as_of: date) -> bool:
    """Tuesday and Thursday keep the 15-minute grid, including 15:10 and 15:15."""
    return as_of.weekday() in (1, 3)


def iter_slots(day: datetime) -> list[datetime]:
    day = day.astimezone(IST)
    step = 15 if is_quarter_hour_day(day.date()) else 30
    slots: list[datetime] = []
    cursor = day.replace(hour=9, minute=30, second=0, microsecond=0)
    last_regular = day.replace(hour=15, minute=30, second=0, microsecond=0)
    while cursor <= last_regular:
        slots.append(cursor)
        if step == 15 and cursor.time() == clock(15, 0):
            slots.append(day.replace(hour=15, minute=10, second=0, microsecond=0))
        cursor += timedelta(minutes=step)
    slots.append(day.replace(hour=15, minute=40, second=0, microsecond=0))
    return slots


def next_slot(now: datetime | None = None) -> datetime | None:
    """Next unpaid grid slot, including the following trading days."""
    current = now if now is not None else now_ist()
    cutoff = current - timedelta(seconds=GRACE_SECONDS)
    for offset in range(0, 12):
        day = current.date() + timedelta(days=offset)
        if not is_trading_day(day):
            continue
        midnight = datetime.combine(day, clock.min, tzinfo=IST)
        for slot in iter_slots(midnight):
            if slot > cutoff:
                return slot
    return None


def chain() -> None:
    subprocess.check_call(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{SELF}/actions/workflows/kick.yml/dispatches",
            "-f",
            "ref=main",
        ]
    )


def dispatch_nifty(repo: str) -> None:
    subprocess.check_call(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{repo}/dispatches",
            "-f",
            "event_type=nifty-scan",
        ]
    )


def main() -> int:
    slot = next_slot()
    if slot is None:
        print("No NSE slot in the next 12 days — retry in 5 hours.")
        time.sleep(MAX_SLEEP_SECONDS)
        chain()
        return 0

    wait = max(0, int((slot - now_ist()).total_seconds()))
    print(f"Target {slot:%Y-%m-%d %H:%M} IST  wait={wait}s")

    if wait > MAX_SLEEP_SECONDS:
        print(f"Sleeping {MAX_SLEEP_SECONDS}s then continuing the wait.")
        time.sleep(MAX_SLEEP_SECONDS)
        chain()
        return 0

    if wait > 0:
        time.sleep(wait)

    repo = target_repo()
    print(f"Dispatching nifty-scan on {repo} for {slot:%H:%M} IST")
    dispatch_nifty(repo)
    print(f"Chaining public kicker after {slot:%H:%M} IST")
    chain()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"gh failed: {exc}", file=sys.stderr)
        sys.exit(1)
