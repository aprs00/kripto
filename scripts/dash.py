"""Phone-width dashboard (≤ 46 columns) for checking kripto over SSH.

Usage: .venv/bin/python -m scripts.dash            # one-shot summary
       scripts/dash.sh [dash|status|journal|log]    # wrapper; interactive menu when on a TTY
Read-only: touches nothing, imports no heavy libraries (runs in < 1 s).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("KRIPTO_ROOT") or Path(__file__).resolve().parent.parent)
DB = ROOT / "state" / "paper.db"
UNITS = ["trader", "health", "review", "research", "insilico", "data"]   # timers; kripto-live is a service (see books section)

TTY = sys.stdout.isatty()


def c(s: str, code: str) -> str:
    return f"\033[{code}m{s}\033[0m" if TTY else s


def red(s): return c(s, "31")
def green(s): return c(s, "32")
def yellow(s): return c(s, "33")
def bold(s): return c(s, "1")
def dim(s): return c(s, "2")


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)", s)
    if not m:
        return None
    t = m.group(2) if m.group(2).count(":") == 2 else m.group(2) + ":00"
    return datetime.fromisoformat(f"{m.group(1)}T{t}+00:00")


def ago(t: datetime | None) -> str:
    if t is None:
        return "never"
    s = (now() - t).total_seconds()
    sign = "in " if s < 0 else ""
    s = abs(s)
    v = f"{s/60:.0f}m" if s < 3600 else f"{s/3600:.1f}h" if s < 172800 else f"{s/86400:.0f}d"
    return sign + v if sign else v + " ago"


def section(title: str) -> None:
    print(bold(f"── {title} " + "─" * max(0, 42 - len(title))))


def health() -> None:
    p = ROOT / "STATUS.md"
    if not p.exists():
        print(red("STATUS.md missing"))
        return
    lines = p.read_text().splitlines()
    top = lines[0] if lines else ""
    col = green if top.startswith("HEALTH: OK") else yellow if "WARN" in top else red
    print(col(top))
    upd = next((l for l in lines[1:5] if l.startswith("_Updated")), "")
    if upd:
        print(dim(upd.strip("_")))
    hp = ROOT / "state" / "health.json"      # hourly deterministic watchdog (scripts/health.py), independent of Claude
    if hp.exists():
        try:
            h = json.loads(hp.read_text())
            lvl = h.get("level", "?")
            hc = green if lvl == "OK" else yellow if lvl == "WARN" else red
            print(hc(f"watchdog {lvl}") + dim(f" {ago(parse_ts(h.get('ts')))}"))
            for r in (h.get("reasons") or [])[:3]:
                print(hc(("  " + r)[:46]))
        except Exception:
            print(yellow("watchdog file unreadable"))


def books() -> None:
    section("books")
    if not DB.exists():
        print(red("no state/paper.db"))
        return
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    meta = dict(q("select k,v from meta")) if q("select name from sqlite_master where name='meta'") else {}
    lr = parse_ts(meta.get("last_run"))
    stale = lr is None or (now() - lr).total_seconds() > 75 * 60
    print(f"trader ran {(red if stale else green)(ago(lr))}, bar {str(meta.get('last_bar', '?'))[5:16]}")
    try:      # always-on watcher heartbeat (kripto-live.service, every ~20 s)
        lv = json.loads(meta["live_tick"])
        lt = parse_ts(lv.get("ts"))
        dead = lt is None or (now() - lt).total_seconds() > 180
        print(f"live watch {(red if dead else green)(ago(lt))}, {lv.get('open_books', 0)} open, "
              f"worst dd {lv.get('worst_dd', 0):+.1%}"[:60])
    except Exception:
        print(yellow("live watch: no heartbeat yet"))
    try:
        cfg = json.loads((ROOT / "config" / "strategies.json").read_text())
    except Exception:
        cfg = {}
    print(dim(f"{'book':13s}{'equity':>9s}{'ret':>8s}{'pos':>4s} {'rebal':>9s}"))
    rows = q("select name,start_equity,halted from books order by name")
    rows = [r for r in rows if not r[0].startswith("small:")] + [None] + [r for r in rows if r[0].startswith("small:")]
    for row in rows:
        if row is None:     # the same strategies in a $200 account (min order decides what can be held)
            print(dim("small accounts (same targets, small size)"))
            continue
        name, start, halted = row
        r = q("select equity,n_pos from equity where book=? order by ts desc limit 1", name)
        if not r:
            continue
        eq, n = r[0]
        short = name.split(":", 1)[1] if ":" in name else name
        st = cfg.get(short, {}).get("status", "") if ":" in name else ""
        if st == "retired":
            continue
        ret = eq / start - 1
        reb = q("select max(bar) from rebalances where book=?", name)[0][0]
        retc = green if ret > 0 else red if ret < 0 else str
        tag = {"candidate": "", "incubation": "ⁱ", "active": "ᵃ"}.get(st, "")
        print(f"{(short + tag)[:12]:13s}{eq:9.2f}{retc(f'{ret:+8.2%}')}{n:4d} "
              f"{(reb[5:13] + 'h') if reb else 'never':>9s}" + (red(" HALT") if halted else ""))
    ev = q("select ts,level,msg from events where level!='INFO' and ts > ? order by ts desc limit 3",
           now().strftime("%Y-%m-%d"))
    for t, l, m in ev:
        print(red(f"{t[5:16]} {l}: {m}"[:46]))
    act = [f"{k}={v.get('alloc', 0):g}" for k, v in cfg.items() if v.get("status") in ("incubation", "active")]
    print(dim("in main book: " + (", ".join(act) if act else "none (flat)")))


def systemd(*args: str) -> str:
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    try:
        return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True,
                              timeout=5, env=env).stdout
    except Exception:
        return ""


def timers() -> None:
    section("jobs")
    for u in UNITS:
        t = dict(l.split("=", 1) for l in systemd("show", f"kripto-{u}.timer", "-p",
                 "LastTriggerUSec", "-p", "NextElapseUSecRealtime").splitlines() if "=" in l)
        s = dict(l.split("=", 1) for l in systemd("show", f"kripto-{u}.service", "-p", "Result",
                 "-p", "ActiveState", "-p", "ExecMainStatus").splitlines() if "=" in l)
        if not t and not s:
            print(f"{u:9s}" + yellow("systemd n/a"))
            continue
        state = s.get("ActiveState", "?")
        if state in ("active", "activating"):
            res = yellow(f"{'running':8s}")
        elif s.get("Result") == "success" and s.get("ExecMainStatus", "0") == "0":
            res = green(f"{'ok':8s}")
        else:
            res = red(f"FAIL rc={s.get('ExecMainStatus')}")
        last, nxt = parse_ts(t.get("LastTriggerUSec")), parse_ts(t.get("NextElapseUSecRealtime"))
        print(f"{u:9s}{res} {ago(last):>9s}  next {ago(nxt) if nxt else '-'}")
    fails = ROOT / "logs" / "agent-failures.log"
    if fails.exists():
        tail = fails.read_text().splitlines()[-2:]
        for l in tail:
            print(red(l[:46]))


def sessions() -> None:
    section("claude sessions")
    ends = []
    for p in sorted((ROOT / "logs").glob("agent-*-*.log"))[-6:]:
        for l in p.read_text(errors="replace").splitlines():
            m = re.match(r"=== (\S+) (start|end) (\w+)(?: rc=(\d+))?", l)
            if m:
                ends.append(m.groups())
    ends.sort(key=lambda x: x[0])
    if not ends:
        print(dim("no agent logs yet"))
    for ts, kind, mode, rc in ends[-10:]:
        if kind == "start":
            continue
        dur = ""
        st = next((parse_ts(x[0]) for x in reversed(ends) if x[2] == mode and x[1] == "start"
                   and x[0] <= ts), None)
        if st:
            dur = f"{(parse_ts(ts) - st).total_seconds() / 60:.0f}min"
        ok = green("ok") if rc == "0" else red(f"rc={rc}")
        print(f"{ts[5:16].replace('T', ' ')} {mode:9s}{dur:>6s}  {ok}")
    # Claude CLI auth problems show up as text in the latest log
    logs = sorted((ROOT / "logs").glob("agent-*-*.log"))
    if logs:
        txt = logs[-1].read_text(errors="replace")[-3000:].lower()
        if any(k in txt for k in ("please run /login", "invalid api key", "oauth token has expired",
                                   "credit balance")):
            print(red("! Claude login/credits problem in last log"))


def commits() -> None:
    section("recent commits")
    out = subprocess.run(["git", "-C", str(ROOT), "log", "-6", "--format=%cd|%s",
                          "--date=format-local:%m-%d %H:%M"], capture_output=True, text=True,
                         env={**os.environ, "TZ": "UTC"}).stdout
    for l in out.splitlines():
        d, s = l.split("|", 1)
        print(f"{dim(d)} {s[:34]}")


def server() -> None:
    section("server")
    du = shutil.disk_usage("/home")
    mem = {}
    try:
        for l in Path("/proc/meminfo").read_text().splitlines():
            k, v = l.split(":")
            mem[k] = int(v.split()[0]) / 1e6
    except Exception:
        pass
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0
    free_gb = du.free / 1e9
    ma = mem.get("MemAvailable", 0)
    print(f"disk {(red if free_gb < 5 else str)(f'{free_gb:.0f}G free')}  "
          f"ram {(red if ma < 1.5 else str)(f'{ma:.1f}G avail')}  load {load:.1f}")
    reg = ROOT / "research" / "registry.jsonl"
    n = sum(1 for _ in reg.open()) if reg.exists() else 0
    print(dim(f"backtests in registry: {n}   {now():%Y-%m-%d %H:%M} UTC"))


def insilico() -> None:
    """The InSilico test programme (research/insilico_queue.json): its tests do not appear in the trader log or the registry."""
    import json as _j
    p = ROOT / "research" / "insilico_queue.json"
    if not p.exists():
        return
    items = _j.loads(p.read_text())["items"]
    forms = [f for it in items for f in it["forms"]]
    done = sum(f["status"] == "done" for f in forms)
    section("insilico tests")
    print(f"{done}/{len(forms)} tests done, {sum(it['status'] == 'closed' for it in items)}/{len(items)} items closed")
    live = [it for it in items if it["status"] == "wip"] or sorted((it for it in items if it["status"] == "todo"), key=lambda x: x["prio"])[:1]
    for it in live[:2]:
        print(dim(f"now: {it['id']} {it['title']}"[:46]))
    last = sorted(((f.get("date", ""), it["id"] + f["id"], f.get("result", "")) for it in items for f in it["forms"] if f["status"] == "done"), reverse=True)[:3]
    for d, k, r in last:
        print(f"{dim(d[5:])} {k} {r}"[:46])
    for it in items:
        if it["status"] == "closed" and it.get("verdict") not in (None, "UNTESTABLE"):
            print(f"{it['id']} {it['verdict']}: {it['title']}"[:46])


def main() -> None:
    for f in (health, books, insilico, timers, sessions, commits, server):
        try:
            f()
        except Exception as e:  # a broken section must never hide the others
            print(red(f"[{f.__name__} failed: {e!r}]"[:46]))


if __name__ == "__main__":
    main()
