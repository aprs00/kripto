"""InSilico pass 3, LD2: ladder flush-batch control on the server's full top-20 1-min universe (backlog LD2, from LD1). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_ld2 explore      # forms a, b, c on 2021-01-01 .. 2023-12-31 -> data/is3/ld2_explore.json
  nice -n 19 .venv/bin/python -m research.studies.is3_ld2 confirm <form>   # ONE run on 2024-01-01 .. 2026-10-31 (a SECOND look: LD1 spent it on cap 3 at 80% coverage)

Reuses ld1_ladder_skew (candidate table data/is3/ld1_cand.parquet built on the server, the one-bar-late E2 fill rule, the account simulator).
Pre-registration: research/is3/notes.md "LD2" (written before any run). Controls:
  scaled base  = base x c with c chosen so its ret/yr equals the form's (SR is scale-free: the question is the tail at equal return);
  thinning     = 200 random subsets of the BASE fills with the form's fill count (does WHICH fills are dropped matter?).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from research.studies import ld1_ladder_skew as L

OUT = L.OUT
FORMS = {"base": ("base", None), "D_cap5": ("D", 5), "A_0.5": ("A", 0.5), "A_0.5+cap5": ("AD", (0.5, 5)), "D_cap3": ("D", 3), "D_cap8": ("D", 8)}


def simulate(t, form, par):
    if form != "AD":
        return L.simulate(t, form, par)
    lam, cap = par
    # A with a hard cap: run A, then apply the cap on its own taken list (same slot rule as D: positions free at fill + HOLD)
    f = L.simulate(t, "A", lam).sort_values("time").reset_index(drop=True)
    keep, open_ = [], []
    for tm, g in f.groupby("time", sort=True):
        open_ = [x for x in open_ if x + L.HOLD * L.MIN > tm]
        room = max(0, cap - len(open_))
        idx = list(g.index[:room])
        keep += idx
        open_ += [tm] * len(idx)
    return f.loc[keep].reset_index(drop=True)


def tail(r):
    tot = float(r.sum())
    return {"ret_yr": tot / (len(r) / 365), "worst": float(r.min()), "worst5": float(r.nsmallest(5).sum())}


def run(lo, hi, names, size=L.SIZE):
    t = L.load(lo, hi)
    print(f"{len(t)} candidate minutes, {t.coin.nunique()} coins, {lo.date()}..{hi.date()}", flush=True)
    F, R, res = {}, {}, {}
    for nm in names:
        F[nm] = simulate(t, *FORMS[nm])
        R[nm] = L.daily(F[nm], lo, hi) * (size / L.SIZE)
        res[nm] = L.card(F[nm], R[nm], None if nm == "base" else R["base"])
    b = tail(R["base"])
    rng = np.random.default_rng(7)
    fb = F["base"]
    for nm in names:
        if nm == "base":
            continue
        x = tail(R[nm])
        c = x["ret_yr"] / b["ret_yr"]
        res[nm]["scaled_base"] = {"c": round(c, 3), "worst": round(c * b["worst"], 4), "worst5": round(c * b["worst5"], 4),
                                  "worst5_impr": round(1 - x["worst5"] / (c * b["worst5"]), 3), "worst_impr": round(1 - x["worst"] / (c * b["worst"]), 3)}
        n = len(F[nm])
        w5, sr = [], []
        for _ in range(200):
            s = fb.iloc[np.sort(rng.choice(len(fb), n, replace=False))]
            rr = L.daily(s, lo, hi) * (size / L.SIZE)
            w5.append(float(rr.nsmallest(5).sum()) / max(float(rr.sum()), 1e-9))
            sr.append(float(rr.mean() / rr.std()) if rr.std() > 0 else 0.0)
        mine = x["worst5"] / x["ret_yr"] / (len(R[nm]) / 365)
        res[nm]["thinning"] = {"w5_over_total_pct": round(float(np.mean(np.array(w5) < mine)), 3),   # share of draws with a WORSE (more negative) tail per unit total
                               "sr_pct": round(float(np.mean(np.array(sr) < float(R[nm].mean() / R[nm].std()))), 3)}
        s = res[nm]
        print(f"{nm:11s} n {s['n']:5d} sr {s['sr']:5.2f} (base {res['base']['sr']:.2f}) ret/yr {s['ret_yr']:+.3f} worst {s['worst']:+.4f} worst5 {s['worst5']:+.4f} | "
              f"scaled base c {s['scaled_base']['c']} worst {s['scaled_base']['worst']:+.4f} worst5 {s['scaled_base']['worst5']:+.4f} impr5 {s['scaled_base']['worst5_impr']:+.0%} | "
              f"thinning pct tail {s['thinning']['w5_over_total_pct']:.2f} sr {s['thinning']['sr_pct']:.2f}", flush=True)
    return res


def passes(res, nm):
    s, b = res[nm], res["base"]
    return s["sr"] >= b["sr"] - 0.1 and s["scaled_base"]["worst5_impr"] >= 0.25 and s["thinning"]["w5_over_total_pct"] >= 0.95


def explore():
    res = run(L.LO, L.SPLIT, list(FORMS))
    out = {"explore": res, "pass": {nm: passes(res, nm) for nm in FORMS if nm != "base"}}
    # (b) size re-derivation under a cap (E2d rule: -50% on every fill of the largest batch stays above the 25% kill)
    out["b_size"] = {}
    for nm, cap in (("D_cap5", 5), ("D_cap3", 3), ("D_cap8", 8)):
        size = 0.25 / (0.5 * cap)
        r = run(L.LO, L.SPLIT, ["base", nm], size=size)[nm]
        out["b_size"][nm] = {"size": size, **{k: r[k] for k in ("sr", "ret_yr", "worst", "worst5", "by_year")}}
        print(f"b {nm} size {size:.3f}: ret/yr {r['ret_yr']:+.3f} worst {r['worst']:+.4f} worst5 {r['worst5']:+.4f}", flush=True)
    live = run(L.LO, L.SPLIT, ["base", "D_cap5"], size=0.029)["base"]
    out["b_size"]["live_base_2.9pct"] = {k: live[k] for k in ("sr", "ret_yr", "worst", "worst5", "by_year")}
    print(f"b live base 2.9%: ret/yr {live['ret_yr']:+.3f} worst {live['worst']:+.4f} worst5 {live['worst5']:+.4f}", flush=True)
    (OUT / "ld2_explore.json").write_text(json.dumps(out, indent=1, default=str))
    print("pass", out["pass"])
    print(json.dumps({k: v["by_year"] for k, v in res.items()}, default=str))


def confirm(nm):
    p = OUT / "ld2_confirm.json"
    if p.exists():
        raise SystemExit(f"confirm already spent: {p}")
    res = run(L.SPLIT, L.HI, ["base", nm])
    ok = passes(res, nm)
    p.write_text(json.dumps({"form": nm, "pass": ok, **res}, indent=1, default=str))
    print("PASS" if ok else "FAIL", json.dumps({k: v["by_year"] for k, v in res.items()}, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"explore": explore, "confirm": lambda: confirm(a[1])}[a[0]]()
