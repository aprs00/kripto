"""X1d (2026-11-12, pre-registered here before running; descriptive, nothing registered):
fspread_hold live params (lookback 14, enter 0.1) on the pair dataset, positions held in TWO accounts (HL, Binance).
Grid fixed in advance: gross in {0.5, 1.0, 2.0} (weights scaled from the strategy's 2.0, same pairs) x collateral re-split
every {1, 7} days x maintenance margin {5%, 10%} of the venue's gross notional.
Worst case each day: every HL leg at its adverse intraday extreme (high for shorts, low for longs), same for Binance.
Liquidation = account equity at that extreme < maintenance x notional. Report: liquidations, min buffer (equity/maintenance).
Decision rule: deployable gross = the largest with 0 liquidations at 10% maintenance and weekly re-split (operationally
realistic: weekly transfers), else at daily re-split."""
import numpy as np, pandas as pd
from kripto import data, strategies as S

p = data.load_panel("pair", "1d")
w2 = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).fillna(0.0)
c = p["close"]
hl1, bn1 = data.load_hl_panel("1d"), data.load_bn_all_panel()
def hilo(col, kind):
    coin, v = col[:-3], col[-2:]
    src = hl1 if v == "hl" else bn1
    name = coin if v == "hl" else data.hl_to_bn(coin)
    return src[kind][name].reindex(c.index) if name in src[kind] else c[col]
hi = pd.DataFrame({x: hilo(x, "high") for x in c.columns}).fillna(c)
lo = pd.DataFrame({x: hilo(x, "low") for x in c.columns}).fillna(c)
fund = p["funding"].fillna(0.0)
start = w2.index[(w2.abs().sum(axis=1) > 0)][0]
idx = c.index[c.index >= start]
for gross in [float(g) for g in __import__("os").environ.get("X1D_GROSS", "0.5 1.0 2.0").split()]:
    for every in (1, 7):
        for mm in (0.05, 0.10):
            w = w2 * gross / 2.0
            E = 1.0
            acc = {"hl": 0.5, "bn": 0.5}
            liq, minbuf, worst_day = 0, np.inf, 0.0
            units = None
            for k, t in enumerate(idx[:-1]):
                t1 = idx[k + 1]
                if units is None or k % every == 0:
                    tot = acc["hl"] + acc["bn"]
                    acc = {"hl": tot / 2, "bn": tot / 2}            # collateral re-split (transfer at the close)
                units = (w.loc[t] * (acc["hl"] + acc["bn"]) / c.loc[t]).fillna(0.0)   # daily rebalance to target weights
                for v in ("hl", "bn"):
                    cols = [x for x in c.columns if x.endswith("@" + v) and units[x] != 0]
                    if not cols:
                        continue
                    u = units[cols]
                    adverse = np.where(u < 0, hi.loc[t1, cols], lo.loc[t1, cols])
                    pnl_worst = float((u * (adverse - c.loc[t, cols])).sum())
                    notional = float((u.abs() * adverse).sum())
                    eq_w = acc[v] + pnl_worst
                    buf = eq_w / (mm * notional) if notional else np.inf
                    minbuf = min(minbuf, buf)
                    if pnl_worst / acc[v] < worst_day:
                        worst_day, worst_at = pnl_worst / acc[v], (str(t1.date()), v, len(cols), round(notional / acc[v], 2), {x: round(float(adverse[i] / c.loc[t, x] - 1), 2) for i, x in enumerate(cols) if abs(adverse[i] / c.loc[t, x] - 1) > 0.2})
                    if eq_w < mm * notional:
                        liq += 1
                    pnl = float((u * (c.loc[t1, cols] - c.loc[t, cols])).sum()) - float((u * c.loc[t, cols] * fund.loc[t1, cols]).sum())
                    acc[v] += pnl
            yrs = (idx[-1] - idx[0]).days / 365.25
            cagr = (acc["hl"] + acc["bn"]) ** (1 / yrs) - 1
            print(f"gross {gross:3.1f} re-split every {every}d mm {mm:.0%}: liquidations {liq:3d}  min buffer {minbuf:5.2f}x  "
                  f"worst intraday account day {worst_day:+.0%}  cagr(no costs) {cagr:+.1%} worst at {worst_at}")
