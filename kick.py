#!/usr/bin/env python3
"""Wait for the next NSE slot on a public runner (free minutes), then kick Nifty.

GitHub's schedule on a private repo is often skipped for a whole morning.
This job sleeps until 09:30 / 09:45 / … / 15:40 IST, POSTs nifty-scan, then
starts the next wait. Sleep time is billed on this public repo, not the
2,000-minute private cap.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TARGET = os.environ.get("TARGET_REPO", "AbhilashMunnur/nifty-index-trade")
SELF = os.environ.get("GITHUB_REPOSITORY", "AbhilashMunnur/nifty-scan-kick")
# Treat a slot as still "now" for this many seconds after it starts.
GRACE_SECONDS = 25

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


def is_trading_day(as_of: date) -> bool:
    if as_of.weekday() >= 5:
        return False
    return as_of.isoformat() not in NSE_HOLIDAYS


def iter_slots(day: datetime) -> list[datetime]:
    day = day.astimezone(IST)
    slots: list[datetime] = []
    cursor = day.replace(hour=9, minute=30, second=0, microsecond=0)
    last_regular = day.replace(hour=15, minute=30, second=0, microsecond=0)
    while cursor <= last_regular:
        slots.append(cursor)
        cursor += timedelta(minutes=15)
    slots.append(day.replace(hour=15, minute=40, second=0, microsecond=0))
    return slots


def next_slot(now: datetime | None = None) -> datetime | None:
    current = now if now is not None else now_ist()
    if not is_trading_day(current.date()):
        return None
    cutoff = current - timedelta(seconds=GRACE_SECONDS)
    for slot in iter_slots(current):
        if slot > cutoff:
            return slot
    return None


def gh(*args: str) -> None:
    subprocess.check_call(["gh", "api", "--method", "POST", *args])


def main() -> int:
    slot = next_slot()
    if slot is None:
        print("No remaining NSE slot today — stop.")
        return 0

    wait = max(0, int((slot - now_ist()).total_seconds()))
    print(f"Target {slot:%Y-%m-%d %H:%M} IST  wait={wait}s")
    if wait > 0:
        import time

        time.sleep(wait)

    print(f"Dispatching nifty-scan on {TARGET} for {slot:%H:%M} IST")
    gh(f"repos/{TARGET}/dispatches", "-f", "event_type=nifty-scan")

    nxt = next_slot(slot + timedelta(seconds=30))
    if nxt is None:
        print("Last slot of the day dispatched.")
        return 0

    print(f"Chaining public kicker for {nxt:%H:%M} IST")
    gh(
        f"repos/{SELF}/actions/workflows/kick.yml/dispatches",
        "-f",
        "ref=main",
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"gh failed: {exc}", file=sys.stderr)
        sys.exit(1)
