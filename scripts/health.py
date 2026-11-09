"""Deterministic health check: the hourly watchdog that used to be a Claude session every 4 hours.

  .venv/bin/python -m scripts.health          # print "HEALTH: OK|WARN|ALERT — reasons"; exit 0|1|2
  .venv/bin/python -m scripts.health --act    # also write state/health.json, start a Claude review on a NEW problem,
                                              # and stamp STATUS.md itself if Claude is the thing that is broken

Claude is only needed to diagnose and fix; noticing is cheaper and more reliable in code. The dead-man switch matters
because the owner reads only STATUS.md / journal / git log: if the Claude login expires, nothing else would ever
change the HEALTH line and a dead system would keep saying OK.
Read-only except for state/health.json and (agent-dead case only) the first line of STATUS.md + a commit.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("KRIPTO_ROOT") or Path(__file__).resolve().parent.parent)
DB = ROOT / "state" / "paper.db"
OUT = ROOT / "state" / "health.json"
MARK = "(written by scripts/health.py, not by Claude)"


def parse_ts(s) -> datetime | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)", str(s or ""))
    if not m:
        return None
    t = m.group(2) if m.group(2).count(":") == 2 else m.group(2) + ":00"
    return datetime.fromisoformat(f"{m.group(1)}T{t}+00:00")


def gather(root: Path = ROOT, db: Path = DB) -> dict:
    """Raw facts. Missing pieces are simply absent; assess() treats absence of the trader's heartbeat as a problem."""
    f: dict = {"disk_free_gb": shutil.disk_usage(root).free / 1e9, "events": [], "halted": [], "sessions": []}
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        meta = dict(con.execute("select k,v from meta").fetchall())
        f["last_run"], f["last_bar"], f["bn_last_run"] = meta.get("last_run"), meta.get("last_bar"), meta.get("bn_last_run")
        try:
            f["collect"] = json.loads(meta["collect_last"]) if meta.get("collect_last") else None
        except Exception:
            f["collect"] = None
        since = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f["events"] = con.execute("select ts,level,msg from events where level!='INFO' and ts>? order by ts", (since,)).fetchall()
        f["halted"] = [r[0] for r in con.execute("select name from books where halted=1")]
    for p in sorted((root / "logs").glob("agent-*-*.log"))[-12:]:
        for line in p.read_text(errors="replace").splitlines():
            m = re.match(r"=== (\S+) end (\w+) rc=(\d+)", line)
            if m:
                f["sessions"].append((m.group(1), m.group(2), int(m.group(3))))
    f["sessions"].sort()
    return f


def assess(f: dict, now: datetime) -> tuple[str, list[str]]:
    """(level, reasons). Reasons that start with "agent:" mean Claude itself is failing."""
    alert, warn = [], []
    age = lambda ts: (now - ts).total_seconds() / 3600 if ts else None
    h = age(parse_ts(f.get("last_run")))
    if h is None or h > 2.2:
        alert.append("trader has never run" if h is None else f"trader has not run for {h:.1f}h")
    elif h > 1.3:
        warn.append(f"trader last ran {h:.1f}h ago")
    b = age(parse_ts(f.get("last_bar")))
    if b is not None and b > 9.5:      # the last closed 4h bar opened 4-8h ago when data is fresh
        warn.append(f"market data stale: last bar {b:.0f}h old")
    if f.get("bn_last_run") and (age(parse_ts(f["bn_last_run"])) or 0) > 2.2:
        warn.append(f"Binance venue has not run for {age(parse_ts(f['bn_last_run'])):.1f}h")
    for ts, level, msg in f.get("events", []):
        (alert if level == "ALERT" else warn).append(f"{level} event: {str(msg)[:60]}")
    if f.get("halted"):
        alert.append("halted books: " + ", ".join(f["halted"]))
    c = f.get("collect")
    if c:
        ch = age(parse_ts(c.get("ts")))
        if ch is not None and ch > 2.2:
            warn.append(f"collector silent for {ch:.1f}h (this data cannot be backfilled)")
        elif c.get("errors"):
            warn.append(f"collector errors={c['errors']}")
    d = f.get("disk_free_gb")
    if d is not None and d < 5:
        alert.append(f"disk {d:.1f}G free")
    elif d is not None and d < 10:
        warn.append(f"disk {d:.1f}G free")
    s = f.get("sessions") or []
    if s:
        ok = [parse_ts(t) for t, _, rc in s if rc == 0]
        last_ok = age(max(ok)) if ok else None
        if last_ok is None or last_ok > 60:    # reviews are daily: 60h = two missed in a row
            alert.append("agent: no successful Claude session " + ("on record" if last_ok is None else f"for {last_ok:.0f}h")
                         + " (login expired? `sudo -u kripto -i`, `claude`, `/login`)")
        elif s[-1][2] != 0:
            warn.append(f"agent: last {s[-1][1]} session ended rc={s[-1][2]}")
    # de-duplicate, keep order
    alert, warn = list(dict.fromkeys(alert)), list(dict.fromkeys(warn))
    return ("ALERT" if alert else "WARN" if warn else "OK"), alert + warn


def line(level: str, reasons: list[str]) -> str:
    return f"HEALTH: {level} — " + ("; ".join(reasons) if reasons else "trader, data, collector, disk and agent sessions all fine")


def should_trigger(level: str, reasons: list[str], prev: dict, now: datetime) -> bool:
    """Start a Claude review for a problem Claude can fix: a new set of reasons, or the same one still there 12h later."""
    fixable = [r for r in reasons if not r.startswith("agent:")]
    if level == "OK" or not fixable:
        return False
    last = parse_ts(prev.get("triggered"))
    return sorted(fixable) != sorted(prev.get("triggered_for") or []) or last is None or (now - last) > timedelta(hours=12)


def stamp_status(text: str, alert_line: str) -> str:
    """STATUS.md with its first line replaced by the watchdog's ALERT (idempotent)."""
    rest = text.split("\n", 1)[1] if "\n" in text else ""
    return f"{alert_line} {MARK}\n{rest}"


def act(level: str, reasons: list[str], now: datetime) -> None:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    rec = {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "level": level, "reasons": reasons,
           "triggered": prev.get("triggered"), "triggered_for": prev.get("triggered_for")}
    env = {**os.environ, "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")}
    if should_trigger(level, reasons, prev, now):
        subprocess.run(["systemctl", "--user", "start", "--no-block", "kripto-review.service"], env=env, check=False)
        rec["triggered"], rec["triggered_for"] = rec["ts"], [r for r in reasons if not r.startswith("agent:")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    dead = [r for r in reasons if r.startswith("agent:") and level == "ALERT" and "no successful" in r]
    status = ROOT / "STATUS.md"
    if dead and status.exists() and MARK not in status.read_text().split("\n", 1)[0]:
        import fcntl
        lock = open(Path.home() / ".kripto-agent.lock", "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # never race a running session's git work
        except OSError:
            return
        status.write_text(stamp_status(status.read_text(), f"HEALTH: ALERT — {dead[0]}"))
        git = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], check=False, capture_output=True)
        git("add", "STATUS.md")
        git("commit", "-qm", "health: ALERT, no successful Claude session (watchdog, not Claude)")
        git("pull", "-q", "--rebase")
        git("push", "-q")


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    level, reasons = assess(gather(), now)
    print(line(level, reasons))
    if "--act" in sys.argv:
        act(level, reasons, now)
    sys.exit({"OK": 0, "WARN": 1, "ALERT": 2}[level])
