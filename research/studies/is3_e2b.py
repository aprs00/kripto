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


if __name__ == "__main__":
    main()
