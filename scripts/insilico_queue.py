"""Work queue of the InSilico third pass (research/insilico_pass3.md). State: research/insilico_queue.json (committed).

  python -m scripts.insilico_queue status              # one line per item
  python -m scripts.insilico_queue should-run          # exit 0 = there is work now, 3 = paused or nothing due (agent.sh asks this)
  python -m scripts.insilico_queue show L1             # the item with every planned form
  python -m scripts.insilico_queue start L1            # a session begins working on it (counts sessions)
  python -m scripts.insilico_queue form L1 a done "result in one line" <evidence>     # evidence = file stem in research/is3/
  python -m scripts.insilico_queue form L1 b skipped "why it cannot be tested"
  python -m scripts.insilico_queue add-form L1 d "what"         # a NEW formulation you thought of (say so before you run it)
  python -m scripts.insilico_queue defer L1 2026-12-01 "why"    # waits for data
  python -m scripts.insilico_queue close L1 DEAD|OPEN|FEATURE|CONFIRMED|UNTESTABLE "diagnosed reason"

Owner's stop switch: `touch state/insilico.paused` (resume: delete it). Why this tool exists: the second pass (2026-11-15)
planned 18 formulations, quietly ran half and still wrote DEAD. Here a verdict is refused while a planned form has no outcome,
a skipped form never counts as a failed one, and DEAD needs three forms with evidence files.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE, EVID, PAUSE = ROOT / "research" / "insilico_queue.json", ROOT / "research" / "is3", ROOT / "state" / "insilico.paused"
VERDICTS = ("DEAD", "OPEN", "FEATURE", "CONFIRMED", "UNTESTABLE")
MAX_SESSIONS = 4


def load() -> dict:
    return json.loads(FILE.read_text())


def save(d: dict) -> None:
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    tmp.rename(FILE)


def get(d: dict, i: str) -> dict:
    for it in d["items"]:
        if it["id"] == i:
            return it
    raise SystemExit(f"no item {i}")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def next_item(day: str | None = None) -> dict | None:
    day, d = day or today(), load()
    closed = {it["id"] for it in d["items"] if it["status"] == "closed"}
    ok = [it for it in d["items"] if it["status"] in ("todo", "wip") and it.get("due", "") <= day
          and all(a in closed for a in it.get("after", []))]
    # unfinished work first, unless it already ate MAX_SESSIONS sessions: then it goes behind everything else
    return min(ok, key=lambda it: (it.get("sessions", 0) >= MAX_SESSIONS, it["status"] != "wip", it["prio"]), default=None)


def should_run(day: str | None = None) -> tuple[bool, str]:
    if PAUSE.exists():
        return False, "paused by state/insilico.paused"
    it = next_item(day)
    return (True, it["id"]) if it else (False, "nothing due")


def start(i: str) -> None:
    d = load()
    it = get(d, i)
    it["status"], it["sessions"] = "wip", it.get("sessions", 0) + 1
    save(d)


def form(i: str, f: str, status: str, result: str, evidence: str | None = None) -> None:
    d = load()
    fm = next((x for x in get(d, i)["forms"] if x["id"] == f), None)
    if fm is None or status not in ("done", "skipped") or not result.strip():
        raise SystemExit("usage: form ITEM FORM done|skipped \"result or reason\" [evidence stem]")
    if status == "done" and not (evidence and (EVID / f"{evidence}.json").exists()):
        raise SystemExit(f"a done form needs an evidence file research/is3/<stem>.json (got {evidence})")
    fm.update(status=status, result=result, date=today(), **({"evidence": evidence} if evidence else {}))
    save(d)


def add_form(i: str, f: str, what: str) -> None:
    d = load()
    it = get(d, i)
    if any(x["id"] == f for x in it["forms"]):
        raise SystemExit(f"{i}{f} exists")
    it["forms"].append({"id": f, "what": what, "status": "planned", "added": today()})
    save(d)


def defer(i: str, day: str, why: str) -> None:
    d = load()
    get(d, i).update(due=day, defer_why=why, status="todo")
    save(d)


def close(i: str, verdict: str, reason: str) -> None:
    d = load()
    it = get(d, i)
    if verdict not in VERDICTS or not reason.strip():
        raise SystemExit(f"verdict one of {VERDICTS} plus a diagnosed reason")
    left = [x["id"] for x in it["forms"] if x["status"] == "planned"]
    if left:
        raise SystemExit(f"{i}: forms {left} have no outcome; run them or mark them skipped with the reason")
    done = [x for x in it["forms"] if x["status"] == "done"]
    if verdict == "DEAD" and len(done) < 3:
        raise SystemExit(f"{i}: DEAD needs three forms with evidence, has {len(done)}; use OPEN")
    if verdict == "CONFIRMED" and not any(EVID.glob(f"{i}*__confirm*.json")):
        raise SystemExit(f"{i}: CONFIRMED needs a confirm-sample card")
    it.update(status="closed", verdict=verdict, reason=reason, closed=today())
    save(d)


def status() -> None:
    d = load()
    for it in sorted(d["items"], key=lambda x: (x["status"] == "closed", x["prio"])):
        n = {k: sum(x["status"] == k for x in it["forms"]) for k in ("done", "skipped", "planned")}
        tail = it.get("verdict") or (f"due {it['due']}" if it.get("due", "") > today() else "")
        print(f"{it['prio']:>3} {it['id']:<4} {it['status']:<6} {n['done']}/{len(it['forms'])} done {n['skipped']} skip  "
              f"{it['title'][:62]:<62} {tail}")
    f = [x for it in d["items"] for x in it["forms"]]
    print(f"forms: {len(f)} total, {sum(x['status'] == 'done' for x in f)} done, {sum(x['status'] == 'skipped' for x in f)} skipped; "
          f"items closed {sum(it['status'] == 'closed' for it in d['items'])}/{len(d['items'])}; next: {should_run()[1]}")


if __name__ == "__main__":
    cmd, a = (sys.argv[1] if len(sys.argv) > 1 else "status"), sys.argv[2:]
    if cmd == "should-run":
        ok, why = should_run()
        print(why)
        sys.exit(0 if ok else 3)
    elif cmd == "show":
        print(json.dumps(get(load(), a[0]), indent=1, ensure_ascii=False))
    else:
        {"status": status, "start": start, "form": form, "add-form": add_form, "defer": defer, "close": close}[cmd](*a)
