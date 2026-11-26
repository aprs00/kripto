"""E2B a: does moving the daily decision anchor from 00:00 UTC to 16:00 / 20:00 UTC (CME-break execution, E2) cost signal P&L?
blend_nested@bn's live components (carry_trend, carry, xsmom; defaults) on daily bars built from bn100 1h (survivorship-free, point-in-time
top-100 members), anchored at H UTC (bar = [d H:00, d+1 H:00)). Each anchor is one research.evaluate line (tag "anchor", logged). flow@bn
needs the hourly taker split, which the hourly archive download dropped: not testable here (stated in the result).
    PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_e2b"""
import json
import numpy as np
import pandas as pd
from kripto import data, research
from kripto.data import BN100_DIR, DATA

ANCH = (0, 4, 8, 12, 16, 20)
COMP = {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}}


def panels():
    tf = data.bn_tradfi()
    cl = {h: {} for h in ANCH}; vo = {h: {} for h in ANCH}; fu = {h: {} for h in ANCH}
    for f in sorted(BN100_DIR.glob("*.parquet")):
        sym = f.stem; coin = sym.removesuffix("USDT")
        df = pd.read_parquet(f, columns=["t", "c", "qv"])
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = data.drop_tradfi(df[~df.index.duplicated()], sym, tf)
        if df.empty:
            continue
        fp = DATA / "bn" / "funding_all" / f"{sym}.parquet"
        fr = pd.read_parquet(fp) if fp.exists() else None
        for h in ANCH:
            sh = df.set_axis(df.index - pd.Timedelta(hours=h))      # pandas ignores resample(offset=) on tz-aware daily bins
            r = sh.resample("1D")
            c_, v_ = r["c"].last(), r["qv"].sum()
            c_.index = c_.index + pd.Timedelta(hours=h); v_.index = c_.index
            if coin == "BTC":   # known answer: bar labelled L closes at the hourly bar opening L+23h
                L = c_.index[100]; assert c_.iloc[100] == df["c"].get(L + pd.Timedelta(hours=23)), (h, L)
            cl[h][coin] = c_.astype("float32"); vo[h][coin] = v_.astype("float32")
            if fr is not None:
                ts = (pd.to_datetime(fr["time"] - 1, unit="ms", utc=True) - pd.Timedelta(hours=h)).dt.floor("1D") + pd.Timedelta(hours=h)
                fu[h][coin] = fr.groupby(ts)["fundingRate"].sum().astype("float32")
    out = {}
    for h in ANCH:
        c = pd.DataFrame(cl[h]).sort_index(); v = pd.DataFrame(vo[h]).reindex(c.index)
        v = v.where(v > 0)
        out[h] = {"close": c.where(v.notna()), "volume": v, "funding": pd.DataFrame(fu[h]).reindex(index=c.index, columns=c.columns)}
    return out


def main():
    P = panels()
    rows = {}
    for h, p in P.items():
        res, s = research.evaluate("blend", p, COMP, f"bn100_1d@{h:02d}", tag="anchor")
        r = res.returns[res.gross.cumsum() > 0]
        r = r[r.index < "2026-11-01"]
        yrs = {int(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in r.groupby(r.index.year) if len(x) > 30}
        rows[h] = {"sharpe": s.get("sharpe"), "ann": s.get("ann_return"), "cost_yr": s.get("cost_yr") or s.get("costs_ann"), "years": yrs,
                   "r": r}
        print(f"anchor {h:02d} UTC: SR {s.get('sharpe')} ann {s.get('ann_return')} | " + " ".join(f"{y}:{v:5.2f}" for y, v in yrs.items()), flush=True)
    # paired difference vs 00 (daily returns aligned by the calendar day of the bar end)
    base = rows[0]["r"].copy(); base.index = base.index.floor("D")
    out = {}
    for h in ANCH[1:]:
        x = rows[h]["r"].copy(); x.index = (x.index + pd.Timedelta(hours=h)).floor("D")
        d = (x - base).dropna()
        out[h] = {"sharpe": rows[h]["sharpe"], "ann": rows[h]["ann"], "years": rows[h]["years"],
                  "diff_ann_bp": round(float(d.mean() * 365 * 1e4), 0), "corr_vs_00": round(float(x.corr(base)), 3)}
        print(f"  {h:02d} vs 00: corr {out[h]['corr_vs_00']}, mean diff {out[h]['diff_ann_bp']} bp/yr", flush=True)
    out[0] = {k: v for k, v in rows[0].items() if k != "r"}
    json.dump({"study": "research/studies/is3_e2b.py", "book": "blend_nested@bn components, defaults, bn100 1h -> daily at anchor H",
               "anchors": {str(k): {kk: vv for kk, vv in v.items() if kk != "r"} for k, v in out.items()}},
              open("research/is3/e2b_anchor.json", "w"), indent=1, default=str)




def hourly(coins):
    """{coin: Series of prices at the full hour (close of the hourly bar that ends then)}."""
    out = {}
    for coin in coins:
        f = BN100_DIR / f"{coin}USDT.parquet"
        if not f.exists():
            continue
        df = pd.read_parquet(f, columns=["t", "c"])
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        s = pd.Series(df["c"].to_numpy(), pd.to_datetime(t, unit="ms", utc=True) + pd.Timedelta(hours=1))
        out[coin] = s[~s.index.duplicated()].sort_index()
    return out


def form_b():
    """Deferred sells: trades decided at the anchor-H close (time T = bar label + 24 h); buys at T, sells (dw < 0) at T + 3 h.
    Gain of deferring a sell = -dw * r(T -> T+3h) (the sold amount keeps its exposure 3 more hours). Per unit sold, by year.
    Hypothesis window: H = 20 (T = 20:00, deferral covers the CME break 21-23 UTC). Placebo: the same 3-h sell deferral at the other
    anchors (00..16). Raw target changes (no band), blend_nested@bn components."""
    from kripto.strategies import REGISTRY
    P = panels()
    res = {}
    hp = None
    for h, p in P.items():
        w = REGISTRY["blend"](p, **COMP).fillna(0.0)
        dw = w.diff().loc["2020-06-01":"2026-10-31"]
        dw = dw.loc[:, dw.abs().sum() > 0]
        if hp is None:
            hp = hourly(list(P[0]["close"].columns))
        T = dw.index + pd.Timedelta(hours=24)
        gain = pd.Series(0.0, dw.index); sold = pd.Series(0.0, dw.index); bgain = pd.Series(0.0, dw.index); bought = pd.Series(0.0, dw.index)
        for coin in dw.columns:
            if coin not in hp:
                continue
            s = hp[coin]
            r = (s.reindex(T + pd.Timedelta(hours=3)).to_numpy() / s.reindex(T).to_numpy() - 1)
            d = dw[coin].to_numpy()
            ok = np.isfinite(r)
            sm = ok & (d < 0); bm = ok & (d > 0)
            gain += np.where(sm, -d * np.nan_to_num(r), 0.0); sold += np.where(sm, -d, 0.0)
            bgain += np.where(bm, -d * np.nan_to_num(r), 0.0); bought += np.where(bm, d, 0.0)
        yrs = {}
        for y in range(2020, 2027):
            m = gain.index.year == y
            yrs[y] = round(float(gain[m].sum() / sold[m].sum() * 1e4), 2) if sold[m].sum() > 0 else None
        daily = gain / sold.replace(0, np.nan)
        t = float(gain.mean() / gain.std() * np.sqrt(len(gain))) if gain.std() > 0 else np.nan
        res[h] = {"sell_defer_bp_per_unit": round(float(gain.sum() / sold.sum() * 1e4), 2), "t_daily": round(t, 2), "years": yrs,
                  "buy_defer_bp_per_unit": round(float(bgain.sum() / bought.sum() * 1e4), 2),
                  "sold_per_yr": round(float(sold.sum() / (len(sold) / 365)), 1), "gain_bp_per_yr_of_book": round(float(gain.sum() / (len(gain) / 365) * 1e4), 1)}
        print(f"anchor {h:02d}: defer sells 3h {res[h]['sell_defer_bp_per_unit']:+.2f} bp/unit sold (t {t:.2f}), defer buys {res[h]['buy_defer_bp_per_unit']:+.2f}; "
              f"book +{res[h]['gain_bp_per_yr_of_book']} bp/yr; by year " + " ".join(f"{y}:{v}" for y, v in yrs.items()), flush=True)
    json.dump({"study": "research/studies/is3_e2b.py form_b", "what": form_b.__doc__, "anchors": res}, open("research/is3/e2b_defer.json", "w"), indent=1)


if __name__ == "__main__":
    import sys
    form_b() if "b" in sys.argv[1:] else main()
