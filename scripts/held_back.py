"""The incubation gate (docs/design.md §4) applied mechanically to every non-retired strategy, and who is held back by what.

Why (2026-11-26, owner: "you are gatekeeping actual profitable strategies"): ladder@bn passed every clause on 11-23 and sat at
candidate / alloc 0 for three days because a session added a condition that is not in the gate. The gate lived in prose and was applied
by hand, so a cautious reading could quietly add clauses. This script reads the numbers and applies only the WRITTEN clauses:

    pick > 0.8 and grid avg > 0.8   (min(pick, grid avg), WF1 2026-11-17) on the venue traded
    DSR > 0.9                       on the longest survivorship-free venue that has the signal (bnall if a Binance analogue exists)
    robust.worst > 0                (lowest of base / 2x cost / one bar late / first 6, 12 months dropped)
    grid median > 0                 (over the pick's own hypothesis: a mixed-sign grid is two hypotheses, WF1)
    other venue positive            where the signal is testable there (pick > 0)

A strategy that passes every clause and is not incubation/active with alloc > 0 is HELD BACK WITHOUT A WRITTEN CLAUSE: exit code 2,
the watchdog WARNs, and the next session must either trade it or write the design.md clause it fails. Holding back a passer is an error
of the same size as promoting a failure (design.md §4, 2026-11-26).

    .venv/bin/python -m scripts.held_back            # markdown table (paste into STATUS.md "Held back")
    .venv/bin/python -m scripts.held_back --check    # exit 2 if any passer is not trading

Evidence: the latest research/results/*_<fn>_<dataset>.json, overridden field by field by research/gate_evidence.json for strategies whose
walk-forward lives elsewhere (order books: research/is3) or whose stored field is known to be wrong (mixed-sign grid averages). Every override
carries a `source`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "research" / "results"
EVID = ROOT / "research" / "gate_evidence.json"
CFG = ROOT / "config" / "strategies.json"
DS = {"bn": "bnall_1d", "hl": "hl_1d", "pair": "pair_1d"}


def _fn(name: str, sc: dict) -> str:
    base = name.split("@")[0]
    return "blend_nested" if base.startswith("blend_nested") else sc.get("strategy", base)


def _matches(d: dict, fn: str, params: dict) -> bool:
    """2026-11-28: a result counts for an entry only if the config it would trade agrees with the entry's params on every
    argument of `fn` (an argument missing on one side = the function default). Before, the newest file won, so a same-day
    re-run of another variant of the same function silently became an entry's gate evidence."""
    import inspect
    from kripto.strategies import REGISTRY
    if fn not in REGISTRY:
        return True
    sig = inspect.signature(REGISTRY[fn]).parameters
    rp = (d.get("robust") or {}).get("params") or {}
    norm = lambda v: list(v) if isinstance(v, tuple) else v
    for k, par in sig.items():
        if k in ("panel", "components", "phase"):
            continue
        dflt = None if par.default is inspect.Parameter.empty else par.default
        if norm(rp.get(k, dflt)) != norm(params.get(k, dflt)):
            return False
    return True


def _latest(fn: str, ds: str, root: Path, params: dict | None = None) -> dict | None:
    files = sorted((root / "research" / "results").glob(f"*_{fn}_{ds}.json"))
    if not files:
        return None
    docs = [json.loads(f.read_text()) for f in reversed(files)]
    if params is not None:
        for d in docs:
            if _matches(d, fn, params):
                return d
    return docs[0]


def _grid_median(d: dict) -> float | None:
    grid, params = d.get("grid") or [], (d.get("robust") or {}).get("params") or {}
    if "sign" in params:                                  # one hypothesis = the pick's own sign
        grid = [g for g in grid if g.get("sign") == params["sign"]]
    s = sorted(g["sharpe"] for g in grid if g.get("sharpe") is not None)
    if not s:
        return d.get("grid_median_sharpe")
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _mixed_sign(d: dict) -> bool:
    return len({g.get("sign") for g in d.get("grid") or [] if "sign" in g}) > 1


def evidence(name: str, sc: dict, root: Path = ROOT, overrides: dict | None = None) -> dict:
    fn, venue = _fn(name, sc), sc.get("venue", "hl")
    e: dict = {"fn": fn, "venue": venue}
    d = _latest(fn, DS.get(venue, ""), root, sc.get("params", {})) if venue in DS else None
    if d:
        o = d.get("oos") or {}
        e.update(pick=o.get("sharpe"), dsr=o.get("dsr"), worst=(d.get("robust") or {}).get("worst"),
                 grid_med=_grid_median(d), source=f"results {fn}_{DS[venue]}")
        n = d.get("n_configs") or 0
        avg = d.get("oos_grid_avg")
        e["grid_avg"] = None if _mixed_sign(d) else (avg if avg is not None else (o.get("sharpe") if n == 1 else None))
    if venue == "hl":                                     # DSR on bnall where a Binance analogue exists; other venue = bnall
        b = _latest(fn, "bnall_1d", root)
        if b:
            e["dsr"], e["other"] = (b.get("oos") or {}).get("dsr"), (b.get("oos") or {}).get("sharpe")
    elif venue == "bn":
        h = _latest(fn, "hl_1d", root)
        if h:
            e["other"] = (h.get("oos") or {}).get("sharpe")
    ov = (overrides or {}).get(name) or {}
    e.update({k: v for k, v in ov.items()})
    return e


CLAUSES = [
    ("pick>0.8", lambda e: e.get("pick") is not None and e["pick"] > 0.8),
    ("grid avg>0.8", lambda e: e.get("grid_avg") is not None and e["grid_avg"] > 0.8),
    ("DSR>0.9", lambda e: e.get("dsr") is not None and e["dsr"] > 0.9),
    ("worst>0", lambda e: e.get("worst") is not None and e["worst"] > 0),
    ("grid med>0", lambda e: e.get("grid_med") is not None and e["grid_med"] > 0),
    ("other venue>0", lambda e: e.get("other") is None or e["other"] > 0),   # only where testable
]


def table(root: Path = ROOT) -> list[dict]:
    cfg = json.loads((root / "config" / "strategies.json").read_text())
    ov = json.loads((root / "research" / "gate_evidence.json").read_text()) if (root / "research" / "gate_evidence.json").exists() else {}
    rows = []
    for name, sc in cfg.items():
        if sc.get("status") == "retired":
            continue
        e = evidence(name, sc, root, ov)
        key = {"pick>0.8": "pick", "grid avg>0.8": "grid_avg", "DSR>0.9": "dsr", "worst>0": "worst", "grid med>0": "grid_med"}
        fails = [(c + " (missing)") if c in key and e.get(key[c]) is None else c for c, ok in CLAUSES if not ok(e)]
        trading = sc.get("status") in ("incubation", "active") and (sc.get("alloc") or 0) > 0
        rows.append({"name": name, **e, "status": sc.get("status"), "alloc": sc.get("alloc", 0), "fails": fails,
                     "trading": trading, "held_back_unwritten": not fails and not trading})
    return rows


def _f(x) -> str:
    return "–" if x is None else f"{x:.2f}"


def render(rows: list[dict]) -> str:
    out = ["| strategy | pick | grid avg | DSR | worst | grid med | other venue | status / alloc | fails (written clauses) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (len(r["fails"]), -(r.get("pick") or -9))):
        why = ", ".join(r["fails"]) if r["fails"] else ("**none: HELD BACK WITHOUT A WRITTEN CLAUSE**" if r["held_back_unwritten"] else "none (trading)")
        out.append(f"| {r['name']} | {_f(r.get('pick'))} | {_f(r.get('grid_avg'))} | {_f(r.get('dsr'))} | {_f(r.get('worst'))} | "
                   f"{_f(r.get('grid_med'))} | {_f(r.get('other'))} | {r['status']} {r['alloc']} | {why} |")
    return "\n".join(out)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = table()
    bad = [r["name"] for r in rows if r["held_back_unwritten"]]
    if "--check" in argv:
        print("held back without a written clause: " + (", ".join(bad) if bad else "none"))
    else:
        print(render(rows))
        if bad:
            print(f"\nHELD BACK WITHOUT A WRITTEN CLAUSE: {', '.join(bad)} -> trade them (M1 rule) or cite the design.md clause they fail.")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
