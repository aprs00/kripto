"""FC1C a: HL-minus-Binance funding gap as a crowding measure, re-explored on HL funding BEFORE 2024-07 (backfilled 11-26 by is3_fc1c_fetch).
Same forms and outcome machinery as fc1_funding_contra (c): 3-d mean gap, short the top 10% (state H=1 and 7-d entry), Binance P&L, BTC-beta hedged,
net of funding and a taker round trip. Explore = 2023-05-15 .. 2024-07-01 (fresh: the PC explore used 2024-07..2025-06). Confirm 2025-07+ untouched.
Dose: 7-d entry price leg by gap-rank decile. Coverage printed (coins with HL funding per day).
    PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fc1c"""
import json, pickle, sys
import numpy as np
import pandas as pd
from kripto import data
from research.studies import fc1_funding_contra as F

LO, HI = "2023-05-15", "2024-07-01"


def main():
    snap = data.DATA / "is3" / "fc1c_bnall_1d.pkl"   # snapshot taken 11-27 00:48 UTC, before the nightly refresh window (bnall must not be loaded 01:15-03:30)
    p = pickle.load(open(snap, "rb")) if snap.exists() else data.load_panel("bnall", "1d")
    h = data.load_panel("hl", "1d")
    forms, sub, rc = F.gap_forms(h, p)
    out = F.Outcomes(sub)
    m3 = forms["c3s gap top10% short"][1]
    cov = m3.loc[LO:HI].sum(axis=1)
    hf = h["funding"].loc[LO:HI].notna().sum(axis=1)
    print(f"HL coins with funding per day {LO}..{HI}: median {hf.median():.0f}; c3s names/day median {cov.median():.0f}; rank corr gap vs BN f3 {rc.loc[LO:HI].mean():.2f}")
    rows = []
    for name, (side, m) in forms.items():
        rows.append(F.row(name + " [state]", F.events(m, side, out, 1, LO, HI, False), 1))
        rows.append(F.row(name + " [entry]", F.events(m, side, out, 7, LO, HI, True), 7))
    F.show(rows)
    # dose: gap-rank decile -> 7-d entry outcome (short side), every decile treated as its own entry form
    coins = [c for c in h["close"].columns if data.hl_to_bn(c) in p["close"].columns and h["funding"][c].notna().any()]
    bnc = [data.hl_to_bn(c) for c in coins]
    idx = p["close"].index
    hf_ = h["funding"][coins].reindex(idx).set_axis(bnc, axis=1)
    bf = sub["funding"][bnc]
    g3 = (hf_.rolling(3, min_periods=2).mean() - bf.rolling(3, min_periods=2).mean()).where(m3.reindex(columns=bnc).notna())
    ok = data._same_asset(h["close"][coins].reindex(idx).set_axis(bnc, axis=1), sub["close"][bnc]) & hf_.notna() & bf.notna() & F.universe(p, 100)[bnc]
    rk = g3.where(ok).rank(axis=1, pct=True)
    dose = []
    for k in range(10):
        mk = (rk > k / 10) & (rk <= (k + 1) / 10)
        e = F.events(mk, -1, out, 7, LO, HI, True)
        dose.append({"decile": k + 1, "n": len(e), "short_price_bp": e["price"].mean() * 1e4, "short_fund_bp": e["fund"].mean() * 1e4,
                     "short_net_bp": e["net"].mean() * 1e4, "t_price": F.nw_t(e.groupby(level=0)["price"].mean(), 6)})
    d = pd.DataFrame(dose).set_index("decile")
    print("\ndose (short each gap decile, 7-d entry):\n" + d.round(2).to_string())
    json.dump({"study": "research/studies/is3_fc1c.py", "window": [LO, HI], "rows": rows, "dose": dose,
               "coverage_median_hl_coins": float(hf.median())}, open("research/is3/fc1c_explore.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
