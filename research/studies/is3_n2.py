"""N2 spot vs perp delta (InSilico R13; notes.md section N2). Daily, 30 coins with Binance spot 1h archives (is3_n2_download).

Features per coin-day (decision at the UTC day close, perp prices, simple returns):
  ip / is = taker imbalance 2*tbqv/qv - 1 of perp / spot; zp / zs = z-score vs the coin's own trailing 30 days (shifted);
  D = zs - zp (spot-led when high); r1 = the day's perp return, r3 = 3-day perp return.
Forms: a = rally (r3 in the coin's top tercile vs trailing 90 d) with D in the top quintile -> long, matched = same coin, same rally size bin;
       b = his exact case: rally with zp < -1 and zs > 0 (vs rally with zp < -1 and zs <= 0);
       c = cross-sectional daily rank of D (long top, short bottom quintile), and D as a filter on perp flow momentum.

    nice -n 19 .venv/bin/python -m research.studies.is3_n2 explore
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]


def panel() -> dict:
    cl, hi, lo, qv, tb, sqv, stb, sc = ({} for _ in range(8))
    for f in sorted((ROOT / "data/bn/spot_1h").glob("*.parquet")):
        sym = f.stem
        coin = sym[:-4]
        p = pd.read_parquet(ROOT / "data/bn/klines_1d_all" / f.name)
        p.index = pd.to_datetime(p.t, unit="ms", utc=True)
        s = pd.read_parquet(f)
        s.index = pd.to_datetime(s.t, unit="ms", utc=True)
        sd = s.resample("1D").agg({"c": "last", "qv": "sum", "tbqv": "sum", "n": "count"})
        sd = sd[s.resample("1D").size() >= 23]                     # whole spot days only
        cl[coin], hi[coin], lo[coin], qv[coin], tb[coin] = p.c, p.h, p.l, p.qv, p.tbqv
        sqv[coin], stb[coin], sc[coin] = sd.qv, sd.tbqv, sd.c
    fr = lambda d: pd.DataFrame(d).sort_index().astype(float)
    out = {"close": fr(cl), "high": fr(hi), "low": fr(lo), "volume": fr(qv), "tb": fr(tb)}
    idx, cols = out["close"].index, out["close"].columns
    out |= {k: fr(v).reindex(index=idx, columns=cols) for k, v in (("svol", sqv), ("stb", stb), ("sclose", sc))}
    bad = (out["sclose"] / out["close"] - 1).abs() > 0.02              # spot and perp are not the same instrument that day
    for k in ("svol", "stb"):
        out[k] = out[k].mask(bad)
    out["volume"] = out["volume"].mask(out["volume"] <= 0)
    return out


def feats(p: dict) -> dict:
    c = p["close"]
    ip = 2 * p["tb"] / p["volume"] - 1
    is_ = 2 * p["stb"] / p["svol"] - 1
    z = lambda x: (x - x.rolling(30, min_periods=20).mean().shift(1)) / x.rolling(30, min_periods=20).std().shift(1)
    zp, zs = z(ip), z(is_)
    r1 = c / c.shift(1) - 1
    r3 = c / c.shift(3) - 1
    # rally size bin: the 3-day return's rank within the coin's own trailing 90 days (causal), terciles 0..2
    rk = r3.rolling(90, min_periods=60).rank(pct=True)
    fwd = {h: c.shift(-h) / c - 1 for h in (1, 3)}
    return {"zp": zp, "zs": zs, "D": zs - zp, "r1": r1, "r3": r3, "rk": rk, "fwd": fwd, "ip": ip, "is": is_}


def long_df(f: dict, h: int) -> pd.DataFrame:
    """One row per coin-day with every feature and the h-day forward return (decision time = bar start + 1 day = the close)."""
    cols = {k: f[k].stack(future_stack=True) for k in ("zp", "zs", "D", "r1", "r3", "rk")}
    cols["fwd"] = f["fwd"][h].stack(future_stack=True)
    d = pd.DataFrame(cols).dropna().reset_index()
    d.columns = ["day", "coin", *cols.keys()]
    d["time"] = d["day"] + pd.Timedelta("1D")
    return d


def cut(d: pd.DataFrame, sample: str, h: int) -> pd.DataFrame:
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    return d[(d.time >= lo) & (d.time + pd.Timedelta(days=h) < hi)]       # the whole hold inside the sample


def ev(d: pd.DataFrame, mask, side: int, m) -> pd.DataFrame:
    e = d[mask].copy()
    e["side"] = side
    e["gross"] = side * e["fwd"]
    e["m"] = m[mask] if not np.isscalar(m) else m
    return e[["time", "coin", "side", "gross", "m", "D", "zp", "zs", "r3", "rk"]].reset_index(drop=True)


def pool(d: pd.DataFrame, side: int, m) -> pd.DataFrame:
    return ev(d, np.ones(len(d), bool), side, m)


def rally_bin(d):  # 3 bins inside the rally (rk >= 2/3) region, by rk
    return np.minimum((d["rk"] * 9).astype(int), 8)


# ------------------------------------------------------------------ forms as event functions (for null / causal checks)
def fn_a(p: dict, h: int = 3) -> pd.DataFrame:
    d = long_df(feats(p), h)
    rally = d.rk >= 2 / 3
    mask = rally & (d.D >= d.loc[rally, "D"].quantile(0.8)) if rally.any() else rally
    return ev(d, mask.to_numpy(), 1, rally_bin(d).to_numpy())


def fn_b(p: dict, h: int = 3) -> pd.DataFrame:
    d = long_df(feats(p), h)
    mask = (d.rk >= 2 / 3) & (d.zp < -1) & (d.zs > 0)
    return ev(d, mask.to_numpy(), 1, rally_bin(d).to_numpy())


def curves(d: pd.DataFrame, label: str) -> None:
    rally = d[d.rk >= 2 / 3]
    print(f"\n{label}: rally coin-days {len(rally)}, all {len(d)}; mean fwd bp by quintile (rally days):")
    for k in ("D", "zp", "zs"):
        g = rally.groupby(pd.qcut(rally[k], 5, labels=False))["fwd"]
        print(f"  {k:3s}", " ".join(f"{x * 1e4:+7.1f}" for x in g.mean()), "| n", g.size().min(),
              "| yearly top-bottom:", {int(y): round(float(x.groupby(pd.qcut(x[k], 5, labels=False))['fwd'].mean().pipe(lambda s: s.iloc[-1] - s.iloc[0]) * 1e4), 1)
                                       for y, x in rally.groupby(rally.time.dt.year)})
    g = d.groupby(pd.qcut(d["D"], 5, labels=False))["fwd"]
    print("  D (all days)", " ".join(f"{x * 1e4:+7.1f}" for x in g.mean()))


def explore() -> None:
    p = panel()
    print("panel", {k: v.shape for k, v in p.items()}, "spot days used", int(p["svol"].notna().sum().sum()))
    print("form a:"); L.null_check(fn_a, p, n=20); L.check_causal(fn_a, p, "2023-06-01", "5D")
    print("form b:"); L.null_check(fn_b, p, n=20); L.check_causal(fn_b, p, "2023-06-01", "5D")
    f = feats(p)
    for h in (1, 3):
        d = cut(long_df(f, h), "explore", h)
        curves(d, f"h={h}d explore")
        m = rally_bin(d).to_numpy()
        po = pool(d, 1, m)
        rally = (d.rk >= 2 / 3).to_numpy()
        # a: spot-led rally, top quintile of D among rally days (threshold from the explore rally days)
        thr = d.loc[rally, "D"].quantile(0.8)
        ea = ev(d, rally & (d.D >= thr).to_numpy(), 1, m)
        L.card(f"N2a_spotled_h{h}", ea, "explore", base=L.matched(ea, po),
               note=f"rally rk>=2/3, D>=q80 ({thr:.2f}); matched same coin same rally bin")
        # perp-led rally as the mirror: short the bottom quintile of D
        thr2 = d.loc[rally, "D"].quantile(0.2)
        ea2 = ev(d, rally & (d.D <= thr2).to_numpy(), -1, m)
        L.card(f"N2a_perpled_short_h{h}", ea2, "explore", base=L.matched(ea2, pool(d, -1, m)),
               note="rally with D<=q20, short; matched same coin same rally bin")
        # b: his exact case
        eb = ev(d, (rally & (d.zp < -1) & (d.zs > 0)).to_numpy(), 1, m)
        bb = ev(d, (rally & (d.zp < -1) & (d.zs <= 0)).to_numpy(), 1, m)
        L.card(f"N2b_neg_perp_spot_buy_h{h}", eb, "explore", base=L.matched(eb, po),
               note="rally, zp<-1, zs>0; matched same coin same rally bin")
        L.card(f"N2b_vs_negperp_nospot_h{h}", eb, "explore", base=bb, note=f"baseline = rally, zp<-1, zs<=0 (n={len(bb)})")




# ------------------------------------------------------------------ null on the event-minus-matched difference (long-only simple returns
# earn sigma^2/2 on sign-flipped data by convexity, so the raw null is not ~0 for ANY long-only rule; the difference must be)
def _minus_pool(e: pd.DataFrame, d: pd.DataFrame, m) -> pd.DataFrame:
    po = pool(d, int(e.side.iloc[0]) if len(e) else 1, m)
    mu = po.groupby(["coin", "m"])["gross"].mean()
    e = e.copy()
    e["gross"] = e["gross"].to_numpy() - mu.reindex(list(zip(e.coin, e.m))).to_numpy()
    return e.dropna(subset=["gross"])


def fn_a_fixed(p: dict, h: int = 3, thr: float = 0.89) -> pd.DataFrame:
    d = long_df(feats(p), h)
    m = rally_bin(d).to_numpy()
    return ev(d, ((d.rk >= 2 / 3) & (d.D >= thr)).to_numpy(), 1, m)


def fn_a_diff(p, h=3):
    d = long_df(feats(p), h)
    return _minus_pool(fn_a_fixed(p, h), d, rally_bin(d).to_numpy())


def fn_b_diff(p, h=3):
    d = long_df(feats(p), h)
    return _minus_pool(fn_b(p, h), d, rally_bin(d).to_numpy())


def checks() -> None:
    p = panel()
    if "hand" not in sys.argv:
        for nm, fn in (("a raw", fn_a_fixed), ("a minus matched", fn_a_diff), ("b minus matched", fn_b_diff)):
            print(nm); L.null_check(fn, p, n=20)
        L.check_causal(fn_a_fixed, p, "2023-06-01", "5D")
    # one hand-checked event, bar by bar
    d = long_df(feats(p), 3)
    eb = fn_b(p); e = eb[eb.time < pd.Timestamp('2022-01-01', tz='UTC')].iloc[0]
    c = p["close"][e.coin]
    t0 = e.time - pd.Timedelta("1D")
    print("hand check", e.coin, e.time, "gross", round(e.gross, 4), "close path", c.loc[t0 - pd.Timedelta("3D"): t0 + pd.Timedelta("3D")].round(4).tolist(),
          "recomputed", round(c.loc[t0 + pd.Timedelta("3D")] / c.loc[t0] - 1, 4),
          "ip/is that day", round(float((2 * p['tb'][e.coin] / p['volume'][e.coin] - 1).loc[t0]), 3), round(float((2 * p['stb'][e.coin] / p['svol'][e.coin] - 1).loc[t0]), 3))


if __name__ == "__main__":
    {"explore": explore, "checks": checks, "c": lambda: None, "d": lambda: None}[sys.argv[1]]()


# ------------------------------------------------------------------ form c: cross-sectional
def xs(d: pd.DataFrame) -> pd.DataFrame:
    d = d[d.groupby("time")["coin"].transform("size") >= 10].copy()
    g = d.groupby("time")
    for k in ("D", "zp", "zs"):
        d[f"q{k}"] = g[k].rank(pct=True)
    d["mp"] = np.minimum((d.qzp * 5).astype(int), 4)          # cross-sectional perp-flow quintile = the matching bin
    return d


def fn_c(p: dict, h: int = 1) -> pd.DataFrame:
    d = xs(long_df(feats(p), h))
    return pd.concat([ev(d, (d.qD > 0.8).to_numpy(), 1, d.mp.to_numpy()), ev(d, (d.qD <= 0.2).to_numpy(), -1, d.mp.to_numpy())])


def form_c() -> None:
    p = panel()
    print("null c (L/S, no convexity issue):"); L.null_check(fn_c, p, n=20); L.check_causal(fn_c, p, "2023-06-01", "3D")
    f = feats(p)
    for h in (1, 3):
        d = xs(cut(long_df(f, h), "explore", h))
        mp = d.mp.to_numpy()
        for k in ("D", "zs"):
            lo_, hi_ = d[f"q{k}"] <= 0.2, d[f"q{k}"] > 0.8
            el, es = ev(d, hi_.to_numpy(), 1, mp), ev(d, lo_.to_numpy(), -1, mp)
            base = pd.concat([L.matched(el, pool(d, 1, mp)), L.matched(es, pool(d, -1, mp))])
            L.card(f"N2c_xs_{k}_h{h}", pd.concat([el, es]), "explore", base=base,
                   note=f"daily XS rank of {k}: long top / short bottom quintile; matched = same coin, same XS perp-flow quintile, same side")
            print("   ", k, "quintile curve (fwd bp, all coin-days):", " ".join(f"{x * 1e4:+.1f}" for x in d.groupby(np.minimum((d[f'q{k}'] * 5).astype(int), 4))["fwd"].mean()))
        # flow momentum (perp taker z, XS top quintile long / bottom short) split by whether spot agrees
        top, bot = d.qzp > 0.8, d.qzp <= 0.2
        agree = pd.concat([ev(d, (top & (d.zs > 0)).to_numpy(), 1, mp), ev(d, (bot & (d.zs < 0)).to_numpy(), -1, mp)])
        disagree = pd.concat([ev(d, (top & (d.zs <= 0)).to_numpy(), 1, mp), ev(d, (bot & (d.zs >= 0)).to_numpy(), -1, mp)])
        L.card(f"N2c_flow_spot_agree_h{h}", agree, "explore", base=disagree,
               note=f"perp flow XS quintile trade where spot delta agrees; baseline = same trade where spot disagrees (n={len(disagree)})")
        allflow = pd.concat([ev(d, top.to_numpy(), 1, mp), ev(d, bot.to_numpy(), -1, mp)])
        print(f"    flow alone h{h}: n={len(allflow)} mean {allflow.gross.mean() * 1e4:+.1f} bp; by year",
              allflow.groupby(allflow.time.dt.year).gross.mean().mul(1e4).round(1).to_dict())


if __name__ == "__main__" and sys.argv[1] == "c":
    form_c()


# ------------------------------------------------------------------ form d: funding as the carry condition
def funding_daily(cols, idx) -> pd.DataFrame:
    out = {}
    for c in cols:
        f = pd.read_parquet(ROOT / "data/bn/funding_all" / f"{c}USDT.parquet")
        s = pd.Series(f.fundingRate.to_numpy(float), pd.to_datetime(f.time, unit="ms", utc=True))
        out[c] = s.resample("1D").sum(min_count=1)          # payments stamped inside the UTC day (known at its close)
    return pd.DataFrame(out).reindex(idx)


def form_d() -> None:
    p = panel()
    f = feats(p)
    fd = funding_daily(p["close"].columns, p["close"].index)
    rich = (fd > fd.rolling(30, min_periods=20).median().shift(1)).astype(float).where(fd.notna())
    for h in (1, 3):
        d = long_df(f, h)
        d = d.merge(rich.stack(future_stack=True).rename("rich").reset_index().set_axis(["day", "coin", "rich"], axis=1), on=["day", "coin"], how="left").dropna(subset=["rich"])
        d = cut(d, "explore", h)
        m = rally_bin(d).to_numpy()
        po = pool(d, 1, m)
        base_mask = ((d.rk >= 2 / 3) & (d.zp < -1)).to_numpy()
        er = ev(d, base_mask & (d.rich == 1).to_numpy(), 1, m)
        ep = ev(d, base_mask & (d.rich == 0).to_numpy(), 1, m)
        L.card(f"N2d_negperp_richfund_h{h}", er, "explore", base=L.matched(er, po), note="rally, zp<-1, funding above own 30d median; matched same coin same rally bin")
        L.card(f"N2d_rich_vs_poor_h{h}", er, "explore", base=ep, note=f"baseline = same with funding at/below median (n={len(ep)})")
        es = ev(d, base_mask & (d.rich == 1).to_numpy() & (d.zs > 0).to_numpy(), 1, m)
        L.card(f"N2d_negperp_richfund_spot_h{h}", es, "explore", base=L.matched(es, po), note="rally, zp<-1, zs>0, rich funding; matched same coin same rally bin")


if __name__ == "__main__" and sys.argv[1] == "d":
    form_d()
