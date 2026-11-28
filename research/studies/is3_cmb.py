"""InSilico pass 3, CMB: PRL + HBL together (a) and the $10-at-$1,000 min-order rule (b). Descriptive. HL 1d."""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from research.studies.is3_prb import partial, summary
from research.studies import is3_prl as PRL

p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
btc = p["close"]["BTC"].pct_change(fill_method=None)
orig = S.beta_to


def books(yb):
    S.beta_to = (lambda panel, *a, **k: orig(panel, *a, **k).fillna(yb))
    S._COMP_CACHE.clear()
    fin, ref, _ = PRL.legs(p)
    S.beta_to = orig
    return ref.fillna(0.0), fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)


def minorder(w, usd=10.0, equity=1000.0):
    """held weight moves to target only when |target - held| * equity >= usd; held drifts with price between trades."""
    T = w.fillna(0.0).to_numpy(); R = p["close"].pct_change(fill_method=None).reindex(w.index).fillna(0.0).to_numpy()
    out = np.zeros_like(T); h = np.zeros(T.shape[1])
    for t in range(len(T)):
        if t:
            g = 1 + (h * R[t]).sum()
            h = h * (1 + R[t]) / g
        hit = np.abs(T[t] - h) * equity >= usd
        h = np.where(hit, T[t], h)
        out[t] = h
    return pd.DataFrame(out, w.index, w.columns)


def stats(w):
    r = bt.run(w, p["close"], p.get("funding"), slip, band=0.0)
    o = {}
    for y in (2023, 2024, 2025, 2026):
        s = summary(r, f"{y}-01-01", f"{y+1}-01-01")
        g = r.returns[r.returns.index.year == y]
        s["corr_btc"] = float(g.corr(btc.reindex(g.index)))
        o[str(y)] = s
    return o


if __name__ == "__main__":
    out = {}
    l1, s33 = books(1.0)
    l1b, s33b = books(1.35)
    for k, w in (("lam1", l1), ("slow33", s33), ("beta135", l1b), ("both", s33b)):
        out["a_" + k] = stats(w)
        print("a", k, {y: (round(x["sr"], 2), round(x["corr_btc"], 2), round(x["costs_ann"], 3)) for y, x in out["a_" + k].items()}, flush=True)
    for k, w in (("lam1_min10", minorder(l1)), ("slow33_min10", minorder(s33))):
        out["b_" + k] = stats(w)
        print("b", k, {y: (round(x["sr"], 2), round(x["costs_ann"], 3), round(x["turnover_ann"], 1)) for y, x in out["b_" + k].items()}, flush=True)
    json.dump(out, open("research/is3/cmb_ab.json", "w"), indent=1)
