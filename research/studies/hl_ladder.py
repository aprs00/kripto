"""HLL1: the frozen ladder rule (ladder@bn: bid 30 sigma below the last 1-min close, fill only 30 bp through, exit 60 min later)
on Hyperliquid's own minute bars, from our websocket trade collection (data/hl/flow, non-backfillable, since 2026-11-12).

Question (descriptive, not registered): do HL's thinner books wick through 30-sigma bids more often than Binance on the same coin and minute,
and do those fills bounce like the Binance ladder's (+116 bp/fill gross one-bar-late, E2)? Pre-stated before the first run (2026-11-27):
* explore = flow data through 2026-11-27 00:00 UTC; confirm = 2026-11-28 onward (accrues; HL minute data cannot be backfilled). No tuning on confirm.
* frozen rule exactly as kripto/ladder.py: sigma = std of the last 1440 1-min log returns (>= 720), quote from close[m] valid from minute m+2
  (one bar late), fill if low <= bid * (1 - 30 bp), one fill per coin per 60 min, exit at close of fill minute + 60. HL fees: maker 1.5 bp in,
  taker 4.5 bp out + 5 bp exit slippage (pessimistic for thin names).
* minutes without trades have no row: closes are forward-filled for sigma (a zero return) and such minutes cannot fill; series are split at
  gaps > 30 min (coin out of the collected universe) and nothing is carried across a split.
* Binance check per event: same-minute Binance 1-min low of the same coin (public klines, one request per event), as depth below the HL bid's
  reference close. "HL-only" = Binance low did not reach the HL bid.
* verdict words: too few (< 30 fills) -> re-run at >= 60 days; else mean/median net per fill, day-clustered t, top-3-day share, HL-only split.

    nice -n 19 .venv/bin/python -m research.studies.hl_ladder [--confirm] [--no-bn]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "data" / "hl" / "flow"
OUT = ROOT / "research" / "studies" / "hl_ladder.json"
K, THROUGH, HOLD, WIN, MINP = 30.0, 30e-4, 60, 1440, 720
FEE_IN, FEE_OUT, SLIP_OUT = 1.5e-4, 4.5e-4, 5e-4
SPLIT = pd.Timestamp("2026-11-28", tz="UTC")
GAP = 30


def load() -> dict[str, pd.DataFrame]:
    d = pd.concat([pd.read_parquet(f, columns=["coin", "minute", "l", "c"]) for f in sorted(FLOW.glob("*.parquet"))])
    d = d.drop_duplicates(["coin", "minute"], keep="last")
    out = {}
    for c, g in d.groupby("coin"):
        g = g.set_index("minute").sort_index()
        # a coin leaves the collected top-60 and comes back days later: split at gaps > GAP minutes, never forward-fill across
        # them (first run 11-27 did, and every "fill" was a stale-price jump at the collector's 6-hourly universe refresh)
        seg = np.cumsum(np.diff(g.index.to_numpy(), prepend=g.index[0]) > GAP)
        for k, s in g.groupby(seg):
            idx = np.arange(s.index[0], s.index[-1] + 1)
            s = s.reindex(idx)
            if len(s) > MINP + HOLD:
                out[f"{c}#{k}"] = pd.DataFrame({"l": s["l"], "c": s["c"].ffill()})
    return out


def events(bars: pd.DataFrame) -> list[dict]:
    c, lo = bars["c"].to_numpy(float), bars["l"].to_numpy(float)
    r = np.diff(np.log(c), prepend=np.nan)
    sg = pd.Series(r).rolling(WIN, min_periods=MINP).std().to_numpy()
    bid = np.full(len(c), np.nan)
    bid[2:] = (c * (1 - K * sg))[:-2]                     # quote from close[m] valid for minute m+2
    out, lock = [], -1
    for t in np.where(lo <= bid * (1 - THROUGH))[0]:
        if t <= lock or t + HOLD >= len(c):
            continue
        ex = c[t + HOLD]
        gross = ex / bid[t] - 1
        out.append({"minute": int(bars.index[t]), "bid": float(bid[t]), "ref_close": float(c[t - 2]), "low": float(lo[t]),
                    "exit": float(ex), "gross": float(gross), "net": float(gross - FEE_IN - FEE_OUT - SLIP_OUT)})
        lock = t + HOLD
    return out


def bn_low(bn, coin: str, minute: int) -> float | None:
    from kripto import data
    try:
        rows = bn.klines(data.hl_to_bn(coin) + "USDT", "1m", start_ms=minute * 60_000, limit=1)
        return float(rows[0][3]) if rows and int(rows[0][0]) == minute * 60_000 else None
    except Exception:
        return None


def summarize(ev: pd.DataFrame) -> dict:
    if ev.empty:
        return {"n": 0}
    day = pd.to_datetime(ev["minute"] * 60_000, unit="ms", utc=True).dt.floor("1D")
    by = ev.groupby(day)["net"].sum()
    t = by.mean() / (by.std(ddof=1) / np.sqrt(len(by))) if len(by) > 1 and by.std() > 0 else float("nan")
    top3 = by.sort_values(ascending=False).head(3).sum() / by.sum() if by.sum() > 0 else float("nan")
    return {"n": int(len(ev)), "days": int(len(by)), "coins": int(ev["coin"].nunique()), "mean_net_bp": round(ev["net"].mean() * 1e4, 1),
            "median_net_bp": round(ev["net"].median() * 1e4, 1), "mean_gross_bp": round(ev["gross"].mean() * 1e4, 1),
            "hit": round(float((ev["net"] > 0).mean()), 2), "day_t": round(float(t), 2), "top3_day_share": round(float(top3), 2)}


def main():
    confirm, use_bn = "--confirm" in sys.argv, "--no-bn" not in sys.argv
    rows = []
    for coin, bars in load().items():
        for e in events(bars):
            rows.append({"coin": coin.split("#")[0], **e})
    ev = pd.DataFrame(rows)
    if ev.empty:
        print("no events")
        return
    ts = pd.to_datetime(ev["minute"] * 60_000, unit="ms", utc=True)
    ev = ev[ts >= SPLIT] if confirm else ev[ts < SPLIT]
    if use_bn and len(ev):
        from kripto.bn import BN
        bn = BN(min_interval=1.5)
        known = set()
        try:
            known = {s["symbol"] for s in bn.exchange_info()["symbols"]}
        except Exception:
            pass
        lows = []
        for _, r in ev.iterrows():
            from kripto import data
            sym = data.hl_to_bn(r["coin"]) + "USDT"
            lows.append(bn_low(bn, r["coin"], r["minute"]) if (not known or sym in known) else None)
        ev["bn_low"] = lows
        ev["bn_depth"] = ev["bn_low"] / ev["ref_close"] - 1
        ev["hl_only"] = ev["bn_low"].notna() & (ev["bn_low"] > ev["bid"])
    res = {"sample": "confirm" if confirm else "explore", "all": summarize(ev)}
    if "hl_only" in ev:
        res["hl_only"] = summarize(ev[ev["hl_only"]])
        res["both_venues"] = summarize(ev[ev["bn_low"].notna() & ~ev["hl_only"]])
        res["no_bn_market"] = summarize(ev[ev["bn_low"].isna()])
    res["top_coins"] = ev.groupby("coin")["net"].agg(["count", "mean"]).sort_values("count", ascending=False).head(8).round(4).to_dict("index")
    res["generated"] = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())
    print(json.dumps(res, indent=1))
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old[res["sample"]] = res
    OUT.write_text(json.dumps(old, indent=1))
    ev.to_csv(OUT.with_suffix(f".{res['sample']}.csv"), index=False)


if __name__ == "__main__":
    main()
