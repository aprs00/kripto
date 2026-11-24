"""T3b: 'spring strength' after a climax minute as a continuous predictor (tg:167 'can determine how strong the bounce or
dive will be from initial mechanical spring after liqs').

Events = every 'any' climax row of data/is3/lshock.parquet (is3_lshock trigger: |r| >= 4 sigma on >= 5x volume, both
directions; side +1 = fade a dump, -1 = fade a pump), explore coins (COINS10) and dates only. Climax minute q = time - 1 min.
Origin O = 10-min extreme before q (as in is3_lshock). At decision time q+3 (close):
    X = extreme of q..q+3, spring = side * (c[q+3] - X) / |O - X|   (0 = still at the extreme, 1 = back at the origin)
Target = side * (c[q+3+H] / c[q+3] - 1), H = 15 / 60 / 240 min (simple). Weak spring -> the fade loses = trade the
continuation (form b says both directions). Dose: spring deciles (day-block bootstrap CI per decile). Card: top spring decile
(fade) and bottom decile (continuation, side flipped) vs matched climaxes of the same coin and fall-size decile.

    nice -n 19 .venv/bin/python -m research.studies.is3_t3b     -> research/is3/T3b__spring.json + cards
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "is3" / "T3b__spring.json"
HZ = (15, 60, 240)
LO, HI = "2021-01-01", "2024-01-01"


def events() -> pd.DataFrame:
    t = pd.read_parquet(ROOT / "data/is3/lshock.parquet", columns=["time", "kind", "side", "coin", "z", "fall"])
    t = t[(t.kind == "any") & t.coin.isin(L.COINS10) & (t.time >= LO) & (t.time < HI)].copy()
    rows = []
    for coin, g in t.groupby("coin"):
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c"])
        tm, h, l, c = k.t.to_numpy(), k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy()
        q = np.searchsorted(tm, (g.time.astype("int64") // 10**6).to_numpy() - 60_000)
        ok = (q >= 11) & (q + 3 + max(HZ) < len(tm))
        ok[ok] &= tm[q[ok] + 3] - tm[q[ok]] == 180_000          # gap-free first 3 minutes
        for i in np.flatnonzero(ok):
            qi, s = q[i], int(g.side.iloc[i])
            O = h[qi - 10:qi].max() if s > 0 else l[qi - 10:qi].min()
            X = l[qi:qi + 4].min() if s > 0 else h[qi:qi + 4].max()
            if abs(O - X) <= 0:
                continue
            p = c[qi + 3]
            row = {"time": pd.Timestamp(tm[qi + 3], unit="ms", tz="UTC"), "coin": coin, "side": s, "z": g.z.iloc[i],
                   "fall": g.fall.iloc[i], "spring": s * (p - X) / abs(O - X), "spring1": s * (c[qi + 1] - X) / abs(O - X)}
            for H in HZ:
                row[f"h{H}"] = s * (c[qi + 3 + H] / p - 1)
            rows.append(row)
    e = pd.DataFrame(rows)
    e["m"] = e.groupby("coin").fall.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    return e


def curve(e: pd.DataFrame, col: str, H: int) -> list[dict]:
    e = e.assign(dec=pd.qcut(e[col].rank(method="first"), 10, labels=False))
    out = []
    for d, g in e.groupby("dec"):
        s = L.stats(g.assign(gross=g[f"h{H}"])[["time", "coin", "side", "gross"]], reps=500)
        out.append({"dec": int(d), "lo": round(float(g[col].min()), 3), "hi": round(float(g[col].max()), 3), "n": s["n"],
                    "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]})
    return out


def main() -> None:
    e = events()
    print(f"events {len(e)} (fade dumps {int((e.side > 0).sum())}, fade pumps {int((e.side < 0).sum())}); spring median {e.spring.median():.2f}")
    res = {"n": int(len(e)), "curves": {}}
    for H in HZ:
        cv = curve(e, "spring", H)
        res["curves"][f"h{H}"] = cv
        print(f"+{H} min by spring decile: " + " | ".join(f"{c['lo']:+.2f}..{c['hi']:+.2f}: {c['mean_bp']:+.1f} [{c['ci95_bp'][0]:+.0f},{c['ci95_bp'][1]:+.0f}]" for c in cv))
    sp = e.spring.rank(pct=True)
    pool = e.assign(gross=e.h60)
    top = pool[sp >= 0.9]
    bot = pool[sp <= 0.1].assign(side=lambda x: -x.side, gross=lambda x: -x.gross)
    base_top = L.matched(top, pool[sp < 0.9], k=3)
    base_bot = L.matched(bot, pool[sp > 0.1].assign(side=lambda x: -x.side, gross=lambda x: -x.gross), k=3)
    cols = ["time", "coin", "side", "gross"]
    res["card_top"] = L.card("T3b_spring_top_h60", top[cols], "explore", base_top[cols], note="fade after a strong spring (top decile), 60 min")
    res["card_bot"] = L.card("T3b_spring_bot_h60", bot[cols], "explore", base_bot[cols], note="continuation after a weak spring (bottom decile), 60 min")
    OUT.write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
