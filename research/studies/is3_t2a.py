"""T2a: table of InSilico's dated examples (from the S1/S2 per-image notes) and the 1-min Binance path after each.

Descriptive only (n ~ 12, examples he chose, winners only). For each example: entry price (rule below), simple returns at
+15/60/240 min and +1/3/5 days in his direction, MFE/MAE within 240 min, and the percentile of the +60-min and +1-day
return among ALL minutes of the same coin and calendar month (placebo distribution, same direction).
Anchors are UTC; where the source chart was in his local time (EET/EEST) it was converted by hand and hand-checked
on the 1-min bars (S2 notes). Examples before 2021 have no minute data here (T2e downloads 2020).

    nice -n 19 .venv/bin/python -m research.studies.is3_t2a      -> research/is3/T2a__table.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
K1M = ROOT / "data" / "bn" / "klines_1m"
OUT = ROOT / "research" / "is3" / "T2a__table.json"

# id, source, symbol, anchor UTC (entry = CLOSE of this minute), direction, family, what he says / what is drawn
EX = [
    ("L1-0215", "tg:165", "BTCUSDT", "2021-02-15 02:22", +1, "L1/T5f",
     "liq cascade low 45,349 at 02:21 on the 2 biggest red bars, green bounce on smaller volume; TPs +1.7/+2.6%/origin"),
    ("L1-0323", "tg:173", "BTCUSDT", None, +1, "L1/T5f",
     "23 Mar 2021 08:20-08:57: red on a volume spike, then green on tiny volume -> rally ('much effort GTFO by little effort')"),
    ("M5-0408", "tg:229", "ETHUSDT", "2021-04-08 23:35", +1, "M5",
     "bid at the range high 2074.96 (22:26) after the 23:03 breakout; retest wick 2071.37 ~23:35; target = avg candle size"),
    ("M4e-0720", "tg:274", "BTCUSDT", "2021-07-20 23:59", +1, "M4e",
     "daily: all TSize groups strongly negative on the low day 29.2k = 'likely the bottom' (in a trend)"),
    ("M4e-1126", "wa 18.10.55(1)", "BTCUSDT", "2021-11-26 23:59", +1, "M4e",
     "daily: all buckets -21..-3% on the 53.5k low day (range 5.6k) -> next days up"),
    ("M4e-1213", "wa 18.10.56", "BTCUSDT", "2021-12-13 23:59", +1, "M4e",
     "daily: all buckets -16..-3% on the 45.6k low day (range 4.6k) -> next day up"),
    ("M4e-0107", "wa 18.10.57", "BTCUSDT", "2022-01-07 23:59", +1, "M4e",
     "daily: all buckets -12..-2% on the 40.5k day; low retested 2 days later before a rally to 44.4k (less clean)"),
    ("N5-1110", "wa 18.11.00(1)", "BTCUSDT", None, -1, "N5b",
     "ATH 10 Nov 2021: 'really clear spike in volume, at that moment we knew, bulls fucked up' -> top"),
    ("P2g-0921", "wa 18.10.26", "BTCUSDT", "2021-09-21 23:59", 0, "P2g (stay out)",
     "21 Sep 2021 wick low on thin volume: 'Does this look like VOLUME to you? Issa fart' -> NOT a bottom (no long)"),
    ("M2e-1113", "wa 18.10.41(2)", "BTCUSDT", None, +1, "M2e",
     "~13 Nov 2020 BTC 16k: highest trade count (701 vs 100-250) at the V low -> up 20 bars (2020: no minute data here)"),
]
H_MIN = [15, 60, 240]
H_DAY = [1, 3, 5]


def load(sym: str) -> pd.DataFrame:
    t = pq.read_table(K1M / f"{sym}.parquet", columns=["t", "h", "l", "c", "qv", "n"]).to_pandas()
    t.index = pd.to_datetime(t.t, unit="ms", utc=True)
    return t.drop(columns="t")


def find_anchor(ex_id: str, k: pd.DataFrame) -> pd.Timestamp | None:
    """Anchors that are defined by a rule on the bars instead of a hand-read minute (decided before looking at returns)."""
    if ex_id == "L1-0323":  # last green minute after the 08:50-08:58 red volume spike (his second marked event)
        w = k.loc["2021-03-23 08:50":"2021-03-23 09:00"]
        red = w[w.c < w.c.shift(1)]
        spike = red.qv.idxmax()
        after = w.loc[spike:].iloc[1:]
        green = after[after.c > after.c.shift(1).fillna(after.c.iloc[0])]
        return green.index[0] if len(green) else None
    if ex_id == "N5-1110":  # largest-volume minute within 30 min of the 2021-11-10 high
        d = k.loc["2021-11-10"]
        top = d.h.idxmax()
        w = d.loc[top - pd.Timedelta("30min"): top + pd.Timedelta("30min")]
        return w.qv.idxmax()
    return None


def path(k: pd.DataFrame, t0: pd.Timestamp, side: int) -> dict:
    c0 = float(k.c.loc[t0])
    s = side if side != 0 else 1   # stay-out examples are described as if long
    out = {"entry_time": str(t0), "entry": c0}
    for m in H_MIN:
        t1 = t0 + pd.Timedelta(minutes=m)
        out[f"r{m}m"] = s * (float(k.c.asof(t1)) / c0 - 1) if t1 <= k.index[-1] else None
    for d in H_DAY:
        t1 = t0 + pd.Timedelta(days=d)
        out[f"r{d}d"] = s * (float(k.c.asof(t1)) / c0 - 1)
    w = k.loc[t0 + pd.Timedelta(minutes=1): t0 + pd.Timedelta(minutes=240)]
    fav, adv = (w.h / c0 - 1, w.l / c0 - 1) if s > 0 else (1 - w.l / c0, 1 - w.h / c0)
    out["mfe240"], out["mae240"] = float(fav.max()), float(adv.min())
    # placebo: every minute of the same calendar month, same direction
    mo = k.loc[t0.strftime("%Y-%m")]
    c = mo.c.to_numpy()
    for lab, step in (("r60m", 60), ("r1d", 1440)):
        fut = k.c.reindex(mo.index + pd.Timedelta(minutes=step)).to_numpy()
        pl = s * (fut / c - 1)
        pl = pl[np.isfinite(pl)]
        v = out[lab]
        out[f"pct_{lab}"] = float((pl < v).mean()) if v is not None and len(pl) else None
        out[f"placebo_med_{lab}"] = float(np.median(pl)) if len(pl) else None
    return out


def main() -> None:
    rows, cache = [], {}
    for ex_id, src, sym, anchor, side, fam, what in EX:
        row = {"id": ex_id, "src": src, "symbol": sym, "family": fam, "side": side, "what": what}
        if sym not in cache:
            cache[sym] = load(sym)
        k = cache[sym]
        t0 = pd.Timestamp(anchor, tz="UTC") if anchor else find_anchor(ex_id, k)
        if t0 is None or t0 < k.index[0]:
            row["status"] = "no minute data (before 2021-01-01)" if ex_id == "M2e-1113" else "anchor not found"
        else:
            row.update(path(k, t0, side))
            row["status"] = "ok"
        rows.append(row)
    OUT.write_text(json.dumps({"form": "T2a", "rows": rows}, indent=1, default=float))
    cols = ["id", "entry_time", "side", "r15m", "r60m", "r240m", "r1d", "r3d", "r5d", "mfe240", "mae240", "pct_r60m", "pct_r1d"]
    df = pd.DataFrame(rows).reindex(columns=cols)
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
