"""AL2b (design.md 2026-11-26): monthly vol multiplier for each main book. The main books mix separately vol-targeted entries 1/N
(by alloc); diversification between them makes the mix realise less than the steady-mode target. Rule (research/studies/al2_mix_vol.py,
form b, pre-registered): s = clip(0.25 / realised vol of the CURRENT live mix's net daily backtest returns over the trailing 365 days,
0.5, 2.0); >= 120 days of returns else 1. Research data: HL main on `hl` 1d, main_bn on `bnall` 1d (the live panels hold 220 days).
Run on the first days of each month (the watchdog WARNs when `main_scale_due` in config/risk.json has passed).

    nice -n 19 .venv/bin/python -m scripts.main_scale            # print
    nice -n 19 .venv/bin/python -m scripts.main_scale --write    # also write risk.json main_scale + main_scale_due
"""
import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt, data, paper as P
from kripto.research import bars_per_day, default_band
from kripto.strategies import _ffill_targets

TARGET, LO, HI, DAYS, MIN_DAYS = 0.25, 0.5, 2.0, 365, 120
BOOKS = {"main": ("hl", "hl"), "main_bn": ("bn", "bnall")}


def scale_from_returns(r: pd.Series) -> tuple[float, float]:
    """(multiplier, realised vol) from a daily net return series (only the trailing DAYS are used)."""
    r = r.dropna()
    r = r[r.index >= r.index[-1] - pd.Timedelta(days=DAYS - 1)] if len(r) else r
    if len(r) < MIN_DAYS:
        return 1.0, float("nan")
    vol = float(r.std() * np.sqrt(365))
    return float(np.clip(TARGET / vol, LO, HI)) if vol > 0 else 1.0, vol


def mix_returns(cfg: dict, venue: str, panel: dict) -> pd.Series:
    live = {n: sc for n, sc in cfg.items() if P.venue_of(sc) == venue and sc.get("status") in ("incubation", "active")
            and sc.get("alloc", 0) > 0}
    w = sum(sc["alloc"] * _ffill_targets(P.strategy_fn(n, sc)(panel, **sc.get("params", {})))
            .reindex(columns=panel["close"].columns).fillna(0.0) for n, sc in live.items())
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    r = bt.run(w, panel["close"], panel.get("funding"), slip, band=default_band()).returns
    on = (w.abs().sum(axis=1) > 0).cummax()
    return r[on.reindex(r.index).fillna(False)]


def main():
    cfg, risk = P.load_cfg()
    out = {}
    for book, (venue, ds) in BOOKS.items():
        r = mix_returns(cfg, venue, data.load_panel(ds, "1d"))
        s, vol = scale_from_returns(r)
        out[book] = round(s, 3)
        print(f"{book}: mix realised vol {vol:.1%} over the last {min(len(r), DAYS)} days (data to {r.index[-1]:%Y-%m-%d}) -> scale {s:.2f}")
    if "--write" in sys.argv:
        risk["main_scale"] = out
        nxt = (pd.Timestamp.now("UTC").normalize() + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
        risk["main_scale_due"] = nxt
        P.RISK.write_text(json.dumps(risk, indent=2) + "\n")
        print("written to", P.RISK, "next due", nxt)


if __name__ == "__main__":
    main()
