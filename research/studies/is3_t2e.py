"""T2e: InSilico's (or his template author's) 107 hand-drawn levels with creation timestamps (S1d), Jun 2020 - Apr 2021.

Fixed before the run (research/is3/notes.md, T2 e think-through): side from the creation-minute close; FIRST touch within
30 d after creation; reaction = simple return from the level at +15/60/240 min in the bounce direction; placebos = the
mirror level (same distance, other side, side flipped) and the same side at 0.63x / 1.37x the distance. Duplicates
(same symbol, price within 0.1 %) counted once (the earliest). Prices: Binance USDT perps (proxy for BitMEX/Bybit inverse).

    nice -n 19 .venv/bin/python -m research.studies.is3_t2e     -> research/is3/T2e__levels.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "is3" / "T2e__levels.json"
HZ = [15, 60, 240]
WINDOW = pd.Timedelta(days=30)


def coin_of(sym: str) -> str:
    s = sym.split("-")[1]
    return {"XBTUSD": "BTC", "BTCUSD": "BTC", "ETHUSD": "ETH"}.get(s, s.replace("USDT", ""))


def klines(coin: str) -> pd.DataFrame:
    a = pd.read_parquet(ROOT / "data/is3/k1m_2020" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c"])
    b = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c"])
    b = b[(b.t >= a.t.max() + 1) & (b.t < pd.Timestamp("2021-06-01").value // 10**6)]
    k = pd.concat([a, b]).drop_duplicates("t").sort_values("t")
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    return k.drop(columns="t")


def label(text: str) -> str:
    t = text.lower()
    for key, lab in (("poc", "naked POC/VA"), ("vah", "naked POC/VA"), ("val", "naked POC/VA"), ("single", "single print"),
                     ("sp", "single print"), ("hvn", "HVN"), ("tail", "tail")):
        if key in t:
            return lab
    return "plain"


def react(k: pd.DataFrame, t0: pd.Timestamp, price: float, side: int) -> dict | None:
    """side +1 = support (touch from above, bounce up), -1 = resistance."""
    w = k.loc[t0 + pd.Timedelta(minutes=1): t0 + WINDOW]
    hit = w.l <= price if side > 0 else w.h >= price
    if not hit.any():
        return None
    th = hit.idxmax()
    out = {"touch": th, "wait_h": (th - t0) / pd.Timedelta(hours=1)}
    for m in HZ:
        c = k.c.asof(th + pd.Timedelta(minutes=m))
        out[f"r{m}"] = side * (c / price - 1)
    return out


def main() -> None:
    lv = json.loads((ROOT / "research/is3/S1d__notes.json").read_text())["levels"]
    df = pd.DataFrame(lv)
    df["coin"] = df.symbol.map(coin_of)
    df["t0"] = pd.to_datetime(df.created, unit="ms", utc=True).dt.floor("min")
    df = df.sort_values("t0")
    keep, seen = [], []
    for i, r in df.iterrows():
        if any(c == r.coin and abs(p / r.price - 1) < 0.001 for c, p in seen):
            continue
        seen.append((r.coin, r.price)); keep.append(i)
    df = df.loc[keep].reset_index(drop=True)
    kl = {c: klines(c) for c in df.coin.unique()}
    rows = []
    for _, r in df.iterrows():
        k = kl[r.coin]
        if r.t0 not in k.index:
            continue
        p0 = float(k.c.loc[r.t0])
        side = 1 if r.price < p0 else -1
        dist = r.price - p0
        variants = {"his": (r.price, side), "mirror": (p0 - dist, -side), "x0.63": (p0 + 0.63 * dist, side), "x1.37": (p0 + 1.37 * dist, side)}
        for v, (px, sd) in variants.items():
            x = react(k, r.t0, px, sd)
            rows.append({"v": v, "coin": r.coin, "text": r.text, "lab": label(r.text), "created": r.t0, "dist": abs(dist) / p0, "side": sd,
                         **({"touched": False} if x is None else {"touched": True, **x})})
    R = pd.DataFrame(rows)
    res = {"levels_unique": int(len(df)), "by_variant": {}, "by_label": {}}
    for v, g in R.groupby("v"):
        t = g[g.touched]
        res["by_variant"][v] = {"n": int(len(g)), "touched": int(len(t)), "median_wait_h": float(t.wait_h.median()) if len(t) else None,
                                **{f"mean_r{m}_bp": round(float(t[f"r{m}"].mean()) * 1e4, 1) for m in HZ},
                                **{f"win_r{m}": round(float((t[f"r{m}"] > 0).mean()), 3) for m in HZ}}
    his = R[(R.v == "his") & R.touched].copy()
    pla = R[(R.v != "his") & R.touched].copy()
    for m in HZ:
        e = his.assign(time=his.touch, gross=his[f"r{m}"])[["time", "coin", "side", "gross"]]
        b = pla.assign(time=pla.touch, gross=pla[f"r{m}"])[["time", "coin", "side", "gross"]]
        s = L.stats(e, b, reps=2000)
        res[f"stats_r{m}"] = {k: s[k] for k in ("n", "days", "mean_bp", "ci95_bp", "p", "mde80_bp", "mean_ex_top3_bp", "base_n", "base_bp", "vs_base_bp", "p_vs_base", "by_year", "by_side")}
        print(f"+{m:>3} min: his n={s['n']} mean {s['mean_bp']:+.1f} bp (p {s['p']:.3f}, mde {s['mde80_bp']:.0f}) | placebo n={s['base_n']} {s['base_bp']:+.1f} | diff {s['vs_base_bp']:+.1f} (p {s['p_vs_base']:.3f}) | ex-top3 {s['mean_ex_top3_bp']} | sides {s['by_side']}")
    for lab, g in his.groupby("lab"):
        res["by_label"][lab] = {"n": int(len(g)), "mean_r60_bp": round(float(g.r60.mean()) * 1e4, 1), "win_r60": round(float((g.r60 > 0).mean()), 3)}
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["by_variant"], indent=0))
    print("by label:", res["by_label"])


if __name__ == "__main__":
    main()
