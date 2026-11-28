"""T9G forward ledger (insilico T9W 2026-11-28): shadow:flow@bn's live taker orders replayed as post-only orders at the decision mid, FROZEN spec
(T9P/T9G): k = 0 (rest at the mid), filled only if the market trades THROUGH the mid by > 3 bp within 24 h, the 4h bar containing the order excluded
(a fill inside it cannot be proven), unfilled orders skipped (the signal's 24-h move is forgone, the taker cost saved). Bars: data/bn/live_4h (kept by the
Binance venue; no extra requests). Only orders placed at/after --since (default 2026-11-29 = after the freeze) whose 24 h window has passed count.
Net per traded unit vs the live taker fill (bp): filled = taker fee 5 - maker fee 2 + the live slippage; unfilled = -(move24 - 5 - slip).
  .venv/bin/python -m scripts.maker_ledger [--since YYYY-MM-DD] [--book shadow:flow@bn] [--out research/maker_forward.json]"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TAKER, MAKER, Q_BP = 5.0, 2.0, 3.0


def replay(fills: pd.DataFrame, bars: dict[str, pd.DataFrame | None], now: pd.Timestamp | None = None, include_first: bool = False) -> pd.DataFrame:
    """fills: ts (utc), coin (no suffix), size, px, mid, slip_bps. bars: coin -> 4h OHLC frame (index = bar open, cols h l c) or None.
    include_first=True: the optimistic bound (the containing bar counts, though part of its range may predate the order)."""
    rows = []
    for _, r in fills.iterrows():
        b = bars.get(r["coin"])
        if b is None or not np.isfinite(r["mid"]) or r["mid"] <= 0:
            continue
        if now is not None and r["ts"] + pd.Timedelta(hours=24) > now:
            continue                                                       # window not complete yet
        t0 = r["ts"].floor("4h") if include_first else r["ts"].ceil("4h")
        w = b[(b.index >= t0) & (b.index < r["ts"] + pd.Timedelta(hours=24))]
        if len(w) < 5:
            continue
        side = float(np.sign(r["size"]))
        ext = float(w["l"].min()) if side > 0 else float(w["h"].max())
        rows.append({"ts": r["ts"], "coin": r["coin"], "side": side, "notional": abs(r["size"] * r["px"]),
                     "thru_bp": side * (r["mid"] - ext) / r["mid"] * 1e4, "move24": side * (float(w["c"].iloc[-1]) / r["mid"] - 1) * 1e4,
                     "slip_bps": float(r["slip_bps"] or 0.0)})
    return pd.DataFrame(rows)


def score(d: pd.DataFrame) -> dict:
    if d.empty:
        return {"orders": 0}
    fill = d.thru_bp > Q_BP
    net = np.where(fill, TAKER - MAKER + d.slip_bps, -(d.move24 - TAKER - d.slip_bps))
    nd = pd.DataFrame({"n": d.notional, "net": net * d.notional, "day": d.ts.dt.normalize()}).groupby("day").sum()
    pdn = nd.net / nd.n
    wavg = lambda x, m: round(float(np.average(x[m], weights=d.notional[m])), 1) if m.any() else None
    return {"orders": int(len(d)), "days": int(len(nd)), "window": [str(d.ts.min()), str(d.ts.max())],
            "fill_share_notional": round(float(d.notional[fill].sum() / d.notional.sum()), 3),
            "move24_filled_bp": wavg(d.move24, fill), "move24_unfilled_bp": wavg(d.move24, ~fill),
            "net_bp_per_unit": round(float(nd.net.sum() / nd.n.sum()), 2),
            "day_t": round(float(pdn.mean() / pdn.std(ddof=1) * np.sqrt(len(pdn))), 2) if len(pdn) > 2 else None,
            "share_days_pos": round(float((pdn > 0).mean()), 2)}


def load(book: str, since: str):
    con = sqlite3.connect(ROOT / "state" / "paper.db")
    f = pd.read_sql("select ts, coin, size, px, mid, slip_bps from fills where book = ?", con, params=(book,))
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    f = f[f["ts"] >= pd.Timestamp(since, tz="UTC")].copy()
    f["coin"] = f["coin"].str.replace("@bn", "", regex=False)
    bars = {}
    for c in f["coin"].unique():
        fp = ROOT / "data" / "bn" / "live_4h" / f"{c}.parquet"
        b = None
        if fp.exists():
            b = pd.read_parquet(fp); b.index = pd.to_datetime(b["t"], unit="ms", utc=True); b = b[~b.index.duplicated()].sort_index()
        bars[c] = b
    return f, bars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-11-29")
    ap.add_argument("--book", default="shadow:flow@bn")
    ap.add_argument("--out", default="research/maker_forward.json")
    a = ap.parse_args()
    f, bars = load(a.book, a.since)
    now = pd.Timestamp.now(tz="UTC")
    out = {"book": a.book, "since": a.since, "spec": "k0 q3 skip, 24 h, 4h bars", "fills_since": int(len(f)),
           "conservative_first_bar_excluded": score(replay(f, bars, now=now)),
           "optimistic_first_bar_included": score(replay(f, bars, now=now, include_first=True)),
           "run": now.isoformat(timespec="seconds")}
    print(json.dumps(out, indent=1))
    if a.out:
        (ROOT / a.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
