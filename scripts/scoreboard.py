"""Weekly scoreboard for the top of STATUS.md (owner 2026-11-26: "I still find it hard to believe you are doing your actual best").
Facts only, from the registry, git and config, so a quiet week cannot be written up as a busy one:

    .venv/bin/python -m scripts.scoreboard            # last 7 days
    .venv/bin/python -m scripts.scoreboard 14

The session adds two lines by hand under it: paper vs backtest per main book (scripts.live_vs_backtest, server only) and
"my mistakes this week" (from the journals and the CLAUDE.md changelog: what went wrong, what it cost, the fix).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout


def facts(days: int = 7, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    wf = cfgs = 0
    for line in (ROOT / "research" / "registry.jsonl").open():
        ts = line[8:28]
        if ts >= since:
            wf += '"kind": "walk_forward"' in line
            cfgs += '"kind": "walk_forward"' not in line
    studies = [l for l in _git("log", f"--since={days} days ago", "--diff-filter=A", "--name-only", "--format=",
                                "--", "research/studies").splitlines() if l.endswith(".py")]
    sessions = [l for l in _git("log", f"--since={days} days ago", "--format=%s").splitlines()]
    now_cfg = json.loads((ROOT / "config" / "strategies.json").read_text())
    rev = _git("rev-list", "-1", f"--before={days} days ago", "HEAD").strip()
    old_cfg = json.loads(_git("show", f"{rev}:config/strategies.json")) if rev else {}
    changes = []
    for n, sc in now_cfg.items():
        o = old_cfg.get(n)
        a, b = (o or {}).get("status"), sc.get("status")
        if o is None:
            changes.append(f"{n}: new ({b})")
        elif a != b or (o.get("alloc") or 0) != (sc.get("alloc") or 0):
            changes.append(f"{n}: {a} {o.get('alloc', 0)} -> {b} {sc.get('alloc', 0)}")
    q = json.loads((ROOT / "research" / "insilico_queue.json").read_text())
    closed = [it for it in q["items"] if it.get("closed", it.get("date", "")) >= since[:10] and it["status"] == "closed"]
    return {"days": days, "wf": wf, "configs": cfgs, "studies": len(studies), "commits": len(sessions),
            "lifecycle": changes, "insilico_closed": [(it["id"], it.get("verdict")) for it in closed]}


def render(f: dict) -> str:
    lc = "; ".join(f["lifecycle"]) if f["lifecycle"] else "none"
    from collections import Counter
    c = Counter(v for _, v in f["insilico_closed"])
    ins = (f"{len(f['insilico_closed'])} (" + ", ".join(f"{v} {n}" for v, n in c.most_common()) + ")") if c else "none"
    return (f"**Scoreboard, last {f['days']} days** (scripts.scoreboard): walk-forward experiments {f['wf']}, single backtests {f['configs']}, "
            f"new studies {f['studies']}, commits {f['commits']}. Lifecycle changes: {lc}. InSilico items closed: {ins}.")


if __name__ == "__main__":
    print(render(facts(int(sys.argv[1]) if len(sys.argv) > 1 else 7)))
    try:   # the $200 twins' deployed share goes next to every $200 number (SMB step 1, insilico SMB1 2026-11-28); needs state/paper.db
        import sqlite3
        from scripts import twin_deployed as T
        if T.DB.exists():
            t = [r for r in T.table(T.latest(sqlite3.connect(T.DB))) if r["sibling"] in ("main", "main_bn", "main@pair")]
            print("$200 deployed share of the $1,000 book (scripts.twin_deployed): " + ", ".join(f"{r['twin']} {r['deployed']} ({r['names']} vs {r['sibling_names']} names)" for r in t))
    except Exception as e:
        print(f"(twin_deployed unavailable: {e!r})")
