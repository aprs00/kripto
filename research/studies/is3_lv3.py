"""InSilico pass 3, LV3: lowvol ranked on idiosyncratic (BTC-residual) vol (backlog LV1 b). Descriptive, NOT registered. Reuses is3_lv2 legs/pnl/line.

  nice -n 19 .venv/bin/python -m research.studies.is3_lv3       # forms a and b, bnall 1d 2021-23 -> research/is3/lv3_ab.json
"""
import json

import numpy as np
import pandas as pd

from kripto import data
from kripto.strategies import beta_to, universe, xs_demean_rank
from research.studies.is3_lv2 import legs, pnl, line
from research.studies.lv1_lowvol import vols, window

A, B = "2021-01-01", "2023-12-31"


def main():
    p = data.load_panel("bnall", "1d")
    r, tv, _ = vols(p)
    fr = p["funding"]
    r1, f1 = r.shift(-1), fr.shift(-1)
    m1 = r1["BTC"]
    beta = beta_to(p)
    e = r - beta.fillna(1.0).mul(r["BTC"], axis=0)
    iv = e.rolling(30, min_periods=10).std()
    out = {}
    for top in (30, 100):
        print(f"\n--- top{top} ---", flush=True)
        mask = universe(p, top) & tv.notna() & iv.notna()
        w0 = legs(xs_demean_rank(-tv, mask).fillna(0.0))
        s0 = line("base: rank on total vol", *pnl(w0, r1, f1, beta, m1), A, B)
        wi = legs(xs_demean_rank(-iv, mask).fillna(0.0))
        h, hp = pnl(wi, r1, f1, beta, m1)
        si = line("a: rank on idio vol", h, hp, A, B)
        hw = window(h, A, B)
        yrs = {int(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in hw.groupby(hw.index.year)}
        # residual idio: rank of idio vol within total-vol terciles (double sort), i.e. idio beyond total
        tt = tv.where(mask).rank(axis=1, pct=True)
        terc = np.ceil(tt * 3).clip(1, 3)
        ir = pd.DataFrame(np.nan, iv.index, iv.columns)
        for k in (1, 2, 3):
            m = mask & (terc == k)
            ir = ir.fillna(iv.where(m).rank(axis=1, pct=True))
        wr = legs(xs_demean_rank(-ir, mask & ir.notna()).fillna(0.0))
        sr_r = line("b: idio rank WITHIN total-vol terciles", *pnl(wr, r1, f1, beta, m1), A, B)
        # dose: hedged next-day return (net of funding) by idio-vol quintile
        q = iv.where(mask).rank(axis=1, pct=True)
        hr = (r1 - f1.fillna(0) - beta.fillna(1).mul(m1, axis=0))
        st = pd.DataFrame({"h": window(hr.where(mask), A, B).stack(), "q": window(q, A, B).stack()}).dropna()
        st["b"] = np.ceil(st.q * 5).clip(1, 5).astype(int)
        dose = st.groupby("b").h.agg(["size", "mean", "median"])
        dose[["mean", "median"]] *= 1e4
        print("   hedged next-day bp by idio-vol quintile (1 = lowest):\n" + dose.round(2).to_string(), flush=True)
        cc = float(pd.DataFrame({"t": tv.where(mask).stack(), "i": iv.where(mask).stack()}).corr("spearman").iloc[0, 1])
        print(f"   spearman(total, idio) pooled {cc:.2f}", flush=True)
        out[f"top{top}"] = {"sr_total": round(s0, 2), "sr_idio": round(si, 2), "sr_idio_within_total": round(sr_r, 2), "idio_years": yrs,
                            "dose_bp": dose.round(2).to_dict("index"), "spearman_total_idio": round(cc, 2),
                            "pass": bool(si >= 0.5 and all(v > 0 for v in yrs.values()) and si > s0)}
    print(json.dumps({k: v["pass"] for k, v in out.items()}))
    json.dump({"study": "research/studies/is3_lv3.py", **out}, open("research/is3/lv3_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
