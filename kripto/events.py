"""Event-driven intraday strategies: orders with limit prices, targets and stops, simulated bar by bar.

The portfolio backtest (kripto/backtest.py) trades target weights at bar closes, so it cannot express "rest a bid at the old
range high, take profit one candle higher, stop below". Strategies here return ORDER INTENTS; `simulate` fills them under
deliberately unfavourable conventions and `to_result` turns the trades into the same BTResult (daily) the research harness
uses, so walk-forward, robustness block and registry logging are identical (research.evaluate dispatches on EVENTS).

Fill conventions (all against us where the bar leaves it open):
* market order: the close of the signal bar (+ `lag` bars), taker fee + modelled slippage;
* resting limit: filled at its price only if the bar trades THROUGH it by THROUGH (price priority guarantees the fill
  whatever the queue position; a touch does not count), maker fee;
* stop: a market order at the stop price (or the bar's open if it gapped beyond), taker fee + slippage;
* a bar that reaches both the stop and a target counts as the stop; a target cannot fill in the bar of entry.
Fees are Binance USDT-M VIP0 (the data is Binance): taker 5 bp, maker 2 bp. Funding is ignored (holds are minutes to hours).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import BTResult

FEE_TAKER, FEE_MAKER, THROUGH = 5e-4, 2e-4, 1e-4
EVENTS: dict[str, callable] = {}


def event(fn):
    EVENTS[fn.__name__] = fn
    return fn


def slip_per_day(volume: pd.DataFrame) -> pd.DataFrame:
    """Slippage (fraction) per coin per UTC day from the PREVIOUS 7 days' mean USD volume; same curve as
    backtest.slippage_model (1.5 bp for BTC-like volume, 25 bp cap)."""
    dv = volume.resample("1D").sum()
    dvm = dv.rolling(7, min_periods=1).mean().shift(1)
    return ((3.0 * np.sqrt(50e6 / dvm.clip(lower=1e4))).clip(1.5, 25.0) / 1e4).fillna(25e-4)


def simulate(intents: list[dict], o: np.ndarray | None, h: np.ndarray, l: np.ndarray, c: np.ndarray, slip: np.ndarray,
             cost_mult: float = 1.0, lag: int = 0, max_open: int = 2) -> list[dict]:
    """intents: dicts {coin, t, side (+1/-1), limit (price or None = market at close[t]), ttl (bars a limit rests),
    targets [(price, fraction)], stop (price or None), hold (bars after entry)}. o/h/l/c/slip: (T, N) arrays;
    o=None means a bar opens at the previous close (perps trade continuously; saves a (T, N) array).
    One position or resting order per coin at a time; at most `max_open` positions overall. Returns one dict per trade:
    coin, t_in, t_out, side, gross (price return of the trade, weighted over its exits), cost (fees + slippage, both sides)."""
    T = c.shape[0]
    busy = {}                      # coin -> last bar its order/position occupies
    open_until: list[int] = []
    trades = []
    for it in sorted(intents, key=lambda x: x["t"]):
        k, side, t0 = it["coin"], it["side"], it["t"] + lag
        if t0 >= T - 1 or busy.get(k, -1) >= it["t"]:
            continue
        open_until = [x for x in open_until if x >= it["t"]]
        if len(open_until) >= max_open:
            continue
        stop, lim = it.get("stop"), it.get("limit")
        if lim is None:
            te, pe = t0, float(c[t0, k])
            cost = float(FEE_TAKER + slip[te, k]) * cost_mult
            first = te + 1
            if not np.isfinite(pe) or (stop is not None and side * (pe - stop) <= 0):
                continue
        else:
            te = -1
            last = min(t0 + it["ttl"], T - 1)
            for j in range(t0 + 1, last + 1):
                if (side > 0 and l[j, k] <= lim * (1 - THROUGH)) or (side < 0 and h[j, k] >= lim * (1 + THROUGH)):
                    te = j
                    break
            if te < 0:
                busy[k] = last
                continue
            pe, cost, first = lim, FEE_MAKER * cost_mult, te      # the stop can already trigger in the bar of the fill
        rem, gross, tx = 1.0, 0.0, te
        tgs = [list(x) for x in it.get("targets", ())]
        end = min(te + it["hold"], T - 1)
        for j in range(first, end + 1):
            if stop is not None and ((side > 0 and l[j, k] <= stop) or (side < 0 and h[j, k] >= stop)):
                op = float(c[j - 1, k] if o is None else o[j, k])
                px = min(stop, op) if side > 0 else max(stop, op)
                if j == te:
                    px = stop
                gross += rem * side * (px / pe - 1)
                cost += rem * (FEE_TAKER + slip[j, k]) * cost_mult
                rem, tx = 0.0, j
                break
            if j > te:
                for tg in tgs:
                    tp, frac = tg
                    if frac > 0 and rem > 1e-12 and ((side > 0 and h[j, k] >= tp * (1 + THROUGH)) or
                                                     (side < 0 and l[j, k] <= tp * (1 - THROUGH))):
                        f = min(frac, rem)
                        gross += f * side * (tp / pe - 1)
                        cost += f * FEE_MAKER * cost_mult
                        rem -= f
                        tg[1] = 0.0
                        tx = j
            if rem <= 1e-12:
                break
        if rem > 1e-12:
            gross += rem * side * (c[end, k] / pe - 1)
            cost += rem * (FEE_TAKER + slip[end, k]) * cost_mult
            tx = end
        busy[k] = tx
        open_until.append(tx)
        trades.append({"coin": k, "t_in": te, "t_out": tx, "side": side, "gross": float(gross), "cost": float(cost)})
    return trades


def to_result(trades: list[dict], index: pd.DatetimeIndex, size: float, band: float = 0.0) -> BTResult:
    """Trades -> daily BTResult. Each trade risks `size` of equity; its P&L is booked on the UTC day it closes.
    band = min order / equity: a book whose trade size is below it cannot trade at all."""
    days = pd.date_range(index[0].floor("D"), index[-1].floor("D"), freq="1D")
    z = lambda: pd.Series(0.0, days)
    ret, gross, to, costs = z(), z(), z(), z()
    df = pd.DataFrame(trades)
    if len(df) and size >= band:
        bar = (index[1] - index[0]) / pd.Timedelta(days=1)
        d = index[df["t_out"].to_numpy()].floor("D")
        ret = ret.add(pd.Series(size * (df["gross"] - df["cost"]).to_numpy(), d).groupby(level=0).sum(), fill_value=0.0)
        costs = costs.add(pd.Series(size * df["cost"].to_numpy(), d).groupby(level=0).sum(), fill_value=0.0)
        to = to.add(pd.Series(2.0 * size, d).groupby(level=0).sum(), fill_value=0.0)
        held = (df["t_out"] - df["t_in"] + 1).to_numpy() * bar * size
        gross = gross.add(pd.Series(held, d).groupby(level=0).sum(), fill_value=0.0)
        df = df.assign(time=index[df["t_in"].to_numpy()])
    res = BTResult(ret, gross, to, costs, z(), pd.DataFrame(index=days))
    res.trades = df
    return res


def _finish(panel, intents, size, max_open, cost_mult, lag, band):
    c = panel["close"]
    day = np.asarray((c.index - c.index[0].floor("D")) // pd.Timedelta(days=1), dtype=np.int64)
    sd = slip_per_day(panel["volume"])                       # (days, N); looked up per bar instead of a (T, N) copy

    class Slip:
        a = sd.to_numpy(dtype=np.float64)

        def __getitem__(self, tk):
            return self.a[day[tk[0]], tk[1]]
    get = lambda k: panel[k].to_numpy(dtype=np.float32, copy=False)
    trades = simulate(intents, None, get("high"), get("low"), get("close"), Slip(), cost_mult, lag, max_open)
    return to_result(trades, c.index, size, band or 0.0)


def bars_per_day(idx: pd.DatetimeIndex) -> int:
    return int(round(pd.Timedelta(days=1) / (idx[1] - idx[0])))


# --------------------------------------------------------------------------- R5 liquidation fade
@event
def lshock(panel, z=4.0, m=5.0, e=1.0, side="long", entry="taker", size=0.5, max_open=2, hold=60,
           cost_mult=1.0, lag=0, band=None) -> BTResult:
    """L-shock (research/insilico_rules.md R5): a high-volume liquidation bar, then an opposite bar on lower volume that
    takes back at least `e` of it. Enter at that bar's close, half off halfway back to the origin, half at the origin,
    stop under the low, out after `hold` bars. side: "long" (after dumps), "short" (after spikes) or "both".
    entry="maker": rest a limit at the signal close for 3 bars instead of crossing."""
    close, high, low, vol = panel["close"], panel["high"], panel["low"], panel["volume"]
    bpd = bars_per_day(close.index)
    intents = []
    for k, coin in enumerate(close.columns):
        c, h, l, v = (x[coin].astype("float64") for x in (close, high, low, vol))
        r = np.log(c).diff()
        sig = r.rolling(bpd, min_periods=bpd // 2).std().shift(1)
        vbar = v.rolling(bpd, min_periods=bpd // 2).mean().shift(1)
        body = c.shift(2) - c.shift(1)                   # climax bar's fall (positive for a dump)
        v1 = v.shift(1)
        big = v1 >= m * vbar.shift(1)
        for sd in ((1,) if side == "long" else (-1,) if side == "short" else (1, -1)):
            climax = (sd * r.shift(1) <= -z * sig.shift(1)) & big
            rev = (sd * r > 0) & (v < v1) & (sd * (c - c.shift(1)) >= e * sd * body)
            ext = np.minimum(l, l.shift(1)) if sd > 0 else np.maximum(h, h.shift(1))
            org = (h.rolling(10).max().shift(1) if sd > 0 else l.rolling(10).min().shift(1))
            for t in np.flatnonzero((climax & rev).to_numpy()):
                p, O, X = c.iloc[t], org.iloc[t], ext.iloc[t]
                if not np.isfinite(O) or sd * (O - p) <= 5e-4 * p:
                    continue
                mid = X + 0.5 * (O - X)
                tg = [(mid, 0.5), (O, 0.5)] if sd * (mid - p) > 0 else [(O, 1.0)]
                intents.append({"coin": k, "t": int(t), "side": sd, "limit": p if entry == "maker" else None, "ttl": 3,
                                "targets": tg, "stop": X * (1 - sd * 1e-4), "hold": hold})
    return _finish(panel, intents, size, max_open, cost_mult, lag, band)


# --------------------------------------------------------------------------- R19 range -> impulse -> range
@event
def range_retest(panel, n=15, tight=0.75, s=1.0, size=0.5, max_open=2, cost_mult=1.0, lag=0, band=None) -> BTResult:
    """Bid the previous range high after a breakout (offer the range low after a breakdown), target one average candle,
    stop `s` candles through the level, one attempt (R19). Passive entry and target; see the module docstring for fills."""
    close, high, low = panel["close"], panel["high"], panel["low"]
    intents = []
    for k, coin in enumerate(close.columns):
        c, h, l = (x[coin].astype("float64") for x in (close, high, low))
        rng = h - l
        atr = rng.rolling(60).mean().shift(1)
        rh, rl = h.rolling(n).max().shift(1), l.rolling(n).min().shift(1)
        ok = ((rh - rl) <= tight * np.sqrt(n) * atr) & (rng >= 1.5 * atr) & (atr > 0)
        for sd, brk, lvl in ((1, c > rh, rh), (-1, c < rl, rl)):
            for t in np.flatnonzero((ok & brk).to_numpy()):
                p, a = lvl.iloc[t], atr.iloc[t]
                intents.append({"coin": k, "t": int(t), "side": sd, "limit": p, "ttl": n,
                                "targets": [(p + sd * a, 1.0)], "stop": p - sd * s * a, "hold": n})
    return _finish(panel, intents, size, max_open, cost_mult, lag, band)


# --------------------------------------------------------------------------- R4 mousetrap
@event
def mousetrap(panel, n=48, hold=6, vol_mult=2.0, size_split=True, side="long", size=0.5, max_open=2,
              cost_mult=1.0, lag=0, band=None) -> BTResult:
    """Failed break of the n-bar low on heavy volume where small trades sold and large trades bought (R4). Enter at the
    bar's close, stop under its low, out after `hold` bars. size_split=False drops the size condition (the control).
    Needs panel["d_small"], panel["d_large"] (taker delta of small / large trades per bar, kripto/tsize.py)."""
    close, high, low, vol = panel["close"], panel["high"], panel["low"], panel["volume"]
    bpd = bars_per_day(close.index)
    intents = []
    for k, coin in enumerate(close.columns):
        c, h, l, v = (x[coin].astype("float64") for x in (close, high, low, vol))
        heavy = v >= vol_mult * v.rolling(bpd, min_periods=bpd // 2).mean().shift(1)
        ds, dl = panel["d_small"][coin], panel["d_large"][coin]
        for sd in ((1,) if side == "long" else (-1,) if side == "short" else (1, -1)):
            if sd > 0:
                lvl = l.rolling(n).min().shift(1)
                trap = (l < lvl) & (c > lvl)
            else:
                lvl = h.rolling(n).max().shift(1)
                trap = (h > lvl) & (c < lvl)
            cond = trap & heavy
            if size_split:
                cond &= (sd * ds < 0) & (sd * dl > 0)
            ext = l if sd > 0 else h
            for t in np.flatnonzero(cond.to_numpy()):
                intents.append({"coin": k, "t": int(t), "side": sd, "limit": None, "ttl": 0, "targets": [],
                                "stop": ext.iloc[t] * (1 - sd * 1e-4), "hold": hold})
    return _finish(panel, intents, size, max_open, cost_mult, lag, band)
