"""InSilico pass 3, HLB: listing_short with established-on-other-venue coins removed from eligibility, HL and bnall (cached). Uses is3_lsw.eligible."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_lsw import eligible
from research.studies.is3_prb import summary


def first_trade(p):
    t = (p["volume"].fillna(0) > 0) & p["close"].notna()
    return t.idxmax().where(t.any()), t.any(axis=1).idxmax()


def established(p, other):
    f, _ = first_trade(p)
    fo, ostart = first_trade(other)
    est = []
    for coin, d0 in f.dropna().items():
        do = fo.get(coin)
        if isinstance(do, pd.Timestamp) and (d0 - do).days >= 60:
            est.append(coin)
        elif isinstance(do, pd.Timestamp) and do <= ostart + pd.Timedelta(days=1) and d0 > ostart + pd.Timedelta(days=60):
            est.append(coin)
    return set(est) - {"BTC"}


def book(p, drop):
    elig, _ = eligible(p)
    if drop:
        elig = elig.copy(); elig.loc[:, [c for c in drop if c in elig.columns]] = False
    raw = -elig.astype(float)
    raw = raw.div(elig.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return S.scheduled(S.hedge_beta(raw, S.beta_to(p)), p, 1, 0.20, 1.5, None)


if __name__ == "__main__":
    b = pickle.load(open(sys.argv[1], "rb")); h = data.load_panel("hl", "1d")
    out = {}
    for nm, p, other, yrs in (("hl", h, b, (2023, 2024, 2025, 2026)), ("bnall", b, h, (2023, 2024, 2025, 2026))):
        est = established(p, other)
        slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
        w0 = book(p, set())
        chk = float((w0.fillna(0) - REGISTRY["listing_short"](p).fillna(0)).abs().max().max()) if nm == "hl" else None
        for k, w in (("base", w0), ("skip_est", book(p, est))):
            r = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
            o = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
            o["all"] = summary(r, "2023-04-01", "2027-01-01")
            idle = (w.drop(columns="BTC").abs().sum(1) == 0)
            o["idle_share_by_year"] = {str(y): round(float(idle[idle.index.year == y].mean()), 3) for y in yrs}
            out[f"{nm}_{k}"] = o
            print(nm, k, "n_est", len(est), "repl", chk, {y: (round(x["sr"], 2), round(x["ann"], 3), round(x["worst10_mean"], 3)) for y, x in o.items() if isinstance(x, dict) and "sr" in x}, o["idle_share_by_year"], flush=True)
        if nm == "hl":
            S._COMP_CACHE.clear()
            orig = REGISTRY["listing_short"]
            for k, d in (("base", set()), ("skip_est", est)):
                REGISTRY["listing_short"] = (lambda panel, target_vol=0.20, _d=d: book(panel, _d))
                S._COMP_CACHE.clear()
                wb = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})
                REGISTRY["listing_short"] = orig
                r = bt.run(wb, p["close"], p.get("funding"), slip, band=0.005)
                out[f"hl_blend_{k}"] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
                print("hl_blend", k, {y: round(x["sr"], 2) for y, x in out[f"hl_blend_{k}"].items()}, flush=True)
    json.dump(out, open("research/is3/hlb_abc.json", "w"), indent=1)
