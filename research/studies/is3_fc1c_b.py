"""FC1C b: HL-minus-Binance 3-d funding gap as a FILTER for listing_short on HL 1d (F0 harness, exit on blocked cells).
Blocked = a short in a coin whose 3-d mean gap (HL daily funding - Binance daily funding, same asset) is <= 0 (HL longs not paying more than Binance's);
gap undefined (coin not on Binance / no funding) -> kept. Explore 2023-05-15..2024-07-01 (F0 'explore' re-pointed here; HL funding backfilled 11-26/27).
Binance panel from the 00:48 snapshot data/is3/fc1c_bnall_1d.pkl (nightly-window rule).  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fc1c_b"""
import json, pickle
import numpy as np
import pandas as pd
from kripto import data
from research.studies import is3_lib as L
from research.studies import is3_filter as F

LO, HI = "2023-05-15", "2024-07-01"


def gap_mask(h: dict, p: dict) -> pd.DataFrame:
    hc = h["close"].columns
    bn = {c: data.hl_to_bn(c) for c in hc if data.hl_to_bn(c) in p["close"].columns}
    idx = h["close"].index
    bf = p["funding"][list(bn.values())].set_axis(list(bn), axis=1).reindex(idx)
    bc = p["close"][list(bn.values())].set_axis(list(bn), axis=1).reindex(idx)
    hf = h["funding"][list(bn)]
    same = data._same_asset(h["close"][list(bn)], bc)
    g = (hf.rolling(3, min_periods=2).mean() - bf.rolling(3, min_periods=2).mean()).where(same)
    m = pd.DataFrame(True, idx, hc)
    m[list(bn)] = ~(g <= 0)          # NaN gap -> keep
    return m, g


def main():
    L.SAMPLES["explore"] = (LO, HI)
    p = pickle.load(open(data.DATA / "is3" / "fc1c_bnall_1d.pkl", "rb"))
    w, h, slip = F.book("listing_short", "hl", {})
    m, g = gap_mask(h, p)
    sh = (w < 0).loc[LO:HI]
    held = int(sh.to_numpy().sum()); blocked = int((sh & ~m.loc[LO:HI].reindex(columns=w.columns).fillna(True)).to_numpy().sum())
    gdef = int((sh & g.reindex(index=sh.index, columns=w.columns).notna()).to_numpy().sum())
    print(f"short coin-days {held}, with a defined gap {gdef} ({gdef/max(held,1):.0%}), blocked {blocked} ({blocked/max(held,1):.0%})")
    out = F.judge("FC1Cb_gap_filter_listing_short", w, h, slip, m, "explore", side=-1, n_random=200, note="gap<=0 shorts exited; HL 2023-05..2024-06")
    base = F.run(w, h, slip); filt = F.run(F.apply(w, m, -1), h, slip)
    yrs = {}
    for y in (2023, 2024):
        b = F.cut(base, "explore"); f = F.cut(filt, "explore")
        b, f = b[b.index.year == y], f[f.index.year == y]
        yrs[y] = {"base_sr": round(F.stats(b)["sr"], 2), "filt_sr": round(F.stats(f)["sr"], 2), "days": len(b)}
    # dose: kept shorts by gap tercile -> next-day short return (price, hedging not applied: descriptive only)
    r1 = h["close"].pct_change(fill_method=None).shift(-1)
    st = pd.DataFrame({"g": g.reindex(index=sh.index, columns=w.columns).where(sh).stack(), "r": (-r1).reindex(index=sh.index, columns=w.columns).where(sh).stack()}).dropna()
    st["q"] = pd.qcut(st["g"], 3, labels=["low", "mid", "high"])
    dose = st.groupby("q", observed=True)["r"].agg(["size", "mean", "median"]).mul([1, 1e4, 1e4]).round(1)
    print("years", yrs); print("short next-day return by gap tercile (bp):\n" + dose.to_string())
    out.update({"years": yrs, "short_days": held, "gap_defined": gdef, "blocked": blocked, "dose": dose.reset_index().to_dict("records")})
    json.dump(out, open("research/is3/fc1c_b_explore.json", "w"), indent=1, default=float)


def form_d(confirm: bool = False):
    """d: block shorts whose 3-d gap is above the explore top-tercile edge (frozen below once measured)."""
    import sys
    p = pickle.load(open(data.DATA / "is3" / "fc1c_bnall_1d.pkl", "rb"))
    w, h, slip = F.book("listing_short", "hl", {})
    _, g = gap_mask(h, p)
    sh = (w < 0).loc[LO:HI]
    edge = float(g.reindex(index=sh.index, columns=w.columns).where(sh).stack().quantile(2 / 3))
    print(f"explore top-tercile gap edge {edge:.6f} (daily funding units)")
    m = ~(g.reindex(index=w.index, columns=w.columns) > edge)
    name = "FC1Cd_block_high_gap_shorts"
    if confirm:
        L.SAMPLES["confirmT"] = ("2025-07-01", "2026-11-01")
        out = F.judge(name, w, h, slip, m, "confirmT", side=-1, n_random=200, note=f"edge {edge:.6f} frozen from explore; confirm 2025-07..2026-10")
        json.dump(out, open("research/is3/fc1c_d_confirm.json", "w"), indent=1, default=float)
        return
    L.SAMPLES["explore"] = (LO, HI)
    out = F.judge(name + "_x", w, h, slip, m, "explore", side=-1, n_random=200, note=f"edge {edge:.6f}")
    base = F.run(w, h, slip); filt = F.run(F.apply(w, m, -1), h, slip)
    yrs = {}
    for y in (2023, 2024):
        b, f = F.cut(base, "explore"), F.cut(filt, "explore")
        yrs[y] = {"base_sr": round(F.stats(b[b.index.year == y])["sr"], 2), "filt_sr": round(F.stats(f[f.index.year == y])["sr"], 2)}
    print("years", yrs)
    out.update({"years": yrs, "edge": edge})
    json.dump(out, open("research/is3/fc1c_d_explore.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    import sys
    if "--d" in sys.argv:
        form_d("--confirm" in sys.argv)
    else:
        main()
