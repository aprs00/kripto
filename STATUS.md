HEALTH: OK — 16:25 review: trader runs hourly, data fresh, no errors; no edge good enough for the main book yet.

_Updated 2026-11-09 16:30 UTC (review session)._

## Main book ($200 paper)
Equity $200.00, +0.00%. Flat: no strategy passes the incubation gate (HL walk-forward OOS Sharpe > 0.8, positive on Binance,
DSR > 0.9, survives 2× costs).

| book | equity | return | positions | note |
|---|---|---|---|---|
| main | $200.00 | +0.00% | 0 | flat by design |
| shadow:tsmom | $2000.22 | +0.01% | 11 | live since 11-09 04:26 |
| shadow:xsmom | $1983.80 | −0.81% | 28 | live since 11-09 04:26 |
| shadow:listing_short | $2000.00 | 0.00% | 0 | new today; flat until the next HL listing with ≥ $1M/day volume |
| shadow:carry (retired) | $2000.00 | 0.00% | 0 | frozen |

Live P&L of a few hours means nothing statistically (see findings). The live books exist to check fills, costs and bugs.

## Strategies (walk-forward out-of-sample Sharpe, net of costs)
| strategy | status | HL | Binance (82 coins) | Binance all 923 incl. delisted (new) |
|---|---|---|---|---|
| tsmom (trend) | candidate | 0.43–0.55 | 1.31 | 0.97 |
| xsmom (x-sec momentum) | candidate | 0.42 | 0.55 | 1.27 (needs many positions) |
| listing_short (short new listings) | candidate (new) | 0.75 (3y) | −0.18 (survivor-biased) | 0.44 at small band (1.08 was an artifact) |
| carry, carry_trend | retired / dead | −0.9 | 1.06 / 0.65 | — |
| xsrev, lowvol, funding_contra, smoothing | dead | negative | negative/not robust | — |

## Today
* Re-ran every 11-08 grid with the fixed code: same verdicts.
* New data: the full Binance perp history including 160 delisted coins (removes survivorship bias).
* Tested 3 new ideas. Short-new-listings is real but modest. Trend-filtered carry and signal smoothing are dead.
* Caught a backtest artifact before acting on it: the $200 min-order band can turn a hedged book into "long BTC". The
  inspection tool now checks for this automatically.

## Next
* ≈ 2026-11-16: build the live-vs-backtest tracking check (T0a) once books have 7 days.
* xsmom with only 3–5 names per side (T11), so it fits a $200 account. listing_short follow-ups (T2b). bnall monthly refresh (T10).
