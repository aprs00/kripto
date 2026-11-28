"""InSilico pass 3, T9R: pair-book legs (<COIN>@hl / <COIN>@bn) resting at the HL price of the order minute, judged on HL 1-min paths (BN leg: same coin, HL as proxy), q 5 bp.
Leg risk = pairs with exactly one leg filled in 24 h: the filled leg's signed move to 24 h (unhedged), then taker on the missing leg. Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t9r  -> research/is3/t9r_ab.json"""
import json
import sqlite3

import numpy as np
import pandas as pd

from kripto.data import DATA
from research.studies.is3_t9q import minutes

FEE = {"hl": (4.5, 1.5), "bn": (5.0, 2.0)}
Q = 5e-4


def main():
    g = minutes()
    end = max(x.index.max() for x in g.values())
    con = sqlite3.connect(DATA.parent / "state" / "paper.db")
    f = pd.read_sql("select ts, book, coin, size, px, mid, slip_bps from fills where book in ('shadow:fspread_hold@pair','main@pair','small:main@pair')", con)
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    f[["base", "ven"]] = f["coin"].str.split("@", expand=True)
    f["batch"] = f["ts"].dt.floor("10min")
    legs = []
    for _, r in f.iterrows():
        x = g.get(r.base)
        if x is None or r.ts < x.index.min() + pd.Timedelta(minutes=5) or r.ts + pd.Timedelta(hours=24) > end:
            continue
        m0 = r.ts.floor("1min"); ref = x["c"].asof(m0)
        w = x[(x.index > m0) & (x.index < r.ts + pd.Timedelta(hours=24))]
        if not np.isfinite(ref) or len(w) < 600:
            continue
        side = float(np.sign(r["size"]))
        hit = w.index[(w["l"] < ref * (1 - Q)) if side > 0 else (w["h"] > ref * (1 + Q))]
        legs.append({"book": r.book, "batch": r.batch, "base": r.base, "ven": r.ven, "side": side, "notional": abs(r["size"] * r.px), "slip": float(r.slip_bps or 0),
                     "filled": len(hit) > 0, "t_fill": hit[0] if len(hit) else pd.NaT, "move24": side * (float(w["c"].iloc[-1]) / ref - 1) * 1e4, "m0": m0})
    L = pd.DataFrame(legs)
    rows = []
    for (b, bt_, base), grp in L.groupby(["book", "batch", "base"]):
        if len(grp) != 2 or set(grp.ven) != {"hl", "bn"}:
            continue
        n = float(grp.notional.mean())
        save = sum(FEE[v][0] - FEE[v][1] + s for v, s, fl in zip(grp.ven, grp.slip, grp.filled) if fl)
        nf = int(grp.filled.sum())
        gap = float(abs((grp.t_fill.iloc[0] - grp.t_fill.iloc[1]).total_seconds()) / 60) if nf == 2 else np.nan
        # one leg only: the filled leg is unhedged for 24 h (its move24), then both legs' unfilled side is taken at 24 h as taker (fee+slip paid, no saving)
        leg_cost = float(grp.loc[grp.filled, "move24"].sum()) if nf == 1 else 0.0
        both_unfilled_cost = 0.0
        rows.append({"book": b, "base": base, "batch": bt_, "n": n, "nfilled": nf, "gap_min": gap, "net_bp": (save + leg_cost + both_unfilled_cost) / 2})   # per leg-unit
    P = pd.DataFrame(rows)
    out = {"legs": int(len(L)), "pairs": int(len(P)), "window": [str(L.m0.min()), str(L.m0.max())],
           "leg_fill_share": {v: round(float(x.filled.mean()), 3) for v, x in L.groupby("ven")},
           "pairs_both_filled": round(float((P.nfilled == 2).mean()), 3), "pairs_one_leg": int((P.nfilled == 1).sum()), "pairs_none": int((P.nfilled == 0).sum()),
           "gap_min_median": float(P.gap_min.median()), "gap_min_p90": float(P.gap_min.quantile(.9)),
           "one_leg_moves_bp": P.loc[P.nfilled == 1, "net_bp"].round(1).tolist(),
           "net_bp_per_leg_unit": round(float(np.average(P.net_bp, weights=P.n)), 2),
           "net_bp_per_leg_unit_both_filled_only": round(float(np.average(P.net_bp[P.nfilled == 2], weights=P.n[P.nfilled == 2])), 2)}
    print(json.dumps(out, indent=1, default=str)); json.dump(out, open("research/is3/t9r_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
