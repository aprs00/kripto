"""E1H: lshock (frozen 2026-11-15: z=8 primary, z=6 reference; m=5, e=1, long, taker, hold 60, 50 % per trade, <= 2 open) on HL's own 1-min bars
from data/hl/flow (collector since 2026-11-12; unseen by every lshock test). Weekly forward re-run: the sample only grows. Not registered.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_e1h -> research/is3/e1h_ab.json"""
import json
import numpy as np, pandas as pd
from kripto import events as E
from kripto.data import DATA


def hl_minute_panel():
    parts = [pd.read_parquet(f, columns=["coin", "minute", "h", "l", "c", "buy_ntl", "sell_ntl"]) for f in sorted((DATA / "hl" / "flow").glob("*.parquet"))]
    x = pd.concat(parts)
    x["t"] = pd.to_datetime(x["minute"] * 60, unit="s", utc=True)
    x = x.drop_duplicates(["coin", "t"]).set_index(["t", "coin"])
    idx = pd.date_range(x.index.get_level_values(0).min(), x.index.get_level_values(0).max(), freq="1min")
    P = {}
    for k, col in (("close", "c"), ("high", "h"), ("low", "l")):
        P[k] = x[col].unstack().reindex(idx)
    P["volume"] = (x["buy_ntl"] + x["sell_ntl"]).unstack().reindex(idx).fillna(0.0)
    P["close"] = P["close"].ffill()
    empty = P["high"].isna()
    P["high"] = P["high"].where(~empty, P["close"]); P["low"] = P["low"].where(~empty, P["close"])
    return {k: v.astype("float64") for k, v in P.items()}


def summ(res):
    t = res.trades
    if t is None or len(t) == 0:
        return {"trades": 0}
    net = (t["gross"] - t["cost"]) * 1e4
    day = res.returns[res.returns != 0]
    o = {"trades": int(len(t)), "net_bp_per_trade_mean": round(float(net.mean()), 1), "median": round(float(net.median()), 1),
         "gross_bp_mean": round(float(t["gross"].mean() * 1e4), 1), "cost_bp_mean": round(float(t["cost"].mean() * 1e4), 1),
         "days_with_trades": int(len(day)), "win_share": round(float((net > 0).mean()), 2)}
    if len(day) > 2:
        o["day_t"] = round(float(day.mean() / day.std(ddof=1) * np.sqrt(len(day))), 2)
        o["top3_day_share"] = round(float(day.nlargest(3).sum() / day.sum()), 2) if day.sum() > 0 else None
    return o


if __name__ == "__main__":
    p = hl_minute_panel()
    out = {"coins": int(p["close"].shape[1]), "minutes": int(p["close"].shape[0]), "window": [str(p["close"].index[0]), str(p["close"].index[-1])]}
    for z in (8.0, 6.0):
        res = E.lshock(p, z=z, m=5.0, e=1.0, side="long", entry="taker", size=0.5, max_open=2, hold=60)
        out[f"z{z:g}"] = summ(res)
        if res.trades is not None and len(res.trades):
            tr = res.trades.assign(coin=lambda d: [p["close"].columns[k] for k in d["coin"]])
            out[f"z{z:g}"]["trade_list"] = [{"coin": r.coin, "time": str(r.time), "net_bp": round(float((r.gross - r.cost) * 1e4), 1)} for r in tr.itertuples()][:40]
        print(z, json.dumps({k: v for k, v in out[f"z{z:g}"].items() if k != "trade_list"}), flush=True)
    json.dump(out, open(DATA.parent / "research" / "is3" / "e1h_ab.json", "w"), indent=1)
