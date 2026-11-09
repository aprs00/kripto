HEALTH: OK — trader + new HL data collector run hourly without errors; best idea so far (a blend) fails one gate clause, main book stays flat.

_Updated 2026-11-09 18:00 UTC (research session, afternoon)._

## Main book ($200 paper)
Equity $200.00, +0.00%. Flat: no strategy passes the incubation gate yet.

| book | equity | return | positions | note |
|---|---|---|---|---|
| main | $200.00 | +0.00% | 0 | flat by design |
| shadow:tsmom | $2009.87 | +0.49% | 11 | live since 11-08 |
| shadow:xsmom | $1987.30 | −0.63% | 28 | live since 11-08 |
| shadow:listing_short | $2000.00 | 0.00% | 0 | flat until a new HL listing with ≥ $1M/day volume |
| shadow:blend (new) | $2000.00 | 0.00% | 0 | first trade at the 11-10 00:00 bar |
| shadow:xsmom_k (new) | $2000.00 | 0.00% | 0 | weekly rebalance; first trade at its next weekly bar |
| shadow:carry (retired) | $2000.00 | 0.00% | 0 | frozen |

A few hours of live P&L means nothing statistically. The live books exist to check fills, costs and bugs.

## Strategies (walk-forward out-of-sample Sharpe, net of costs)
| strategy | status | HL | Binance all 923 incl. delisted |
|---|---|---|---|
| **blend** (trend + small x-sec momentum + listing shorts, equal risk) | candidate (new) | **1.57** (3 y) | 1.02 (6 y) |
| xsmom_k (x-sec momentum, 3–5 names per side, fits $200) | candidate (new) | 0.55 | 1.37 |
| tsmom (trend) | candidate | 0.43–0.55 | 0.97 |
| xsmom (x-sec momentum, broad) | candidate | 0.42 | 1.27 |
| listing_short (short new listings) | candidate | 0.75 | 0.44 |
| carry, carry_trend, xsrev, lowvol, funding_contra, smoothing | dead | — | — |

## This afternoon
* **Blend.** Mixing the three weak candidates with equal risk gives HL 1.57 and survives double costs (1.54). They are
  nearly uncorrelated (0.02–0.28), so the mix is far better than any one of them. It passes 4 of the 5 incubation gate
  clauses but fails the multiple-testing check on the long Binance history (0.62, needs 0.9). It's also partly BTC-beta there.
  Caveat: I chose the components' settings after seeing their results, so the next test re-does this without that bias.
  → candidate + live shadow book.
* **Small x-sec momentum** (3–5 names per side, executable at $200): works on Binance (1.37), weak on HL after costs (0.55).
  → candidate + shadow book.
* **New data collection (can't be backfilled):** every hour we now snapshot the positions of the largest public HL
  accounts and the top-10 order books (public read-only data, ~56 extra requests/hour within the shared rate limit).

## Next
* Re-test the blend with each component's settings chosen out-of-sample (T4b), plus a ≤ 10-name version that fits $200 (T12).
* ≈ 2026-11-16: live-vs-backtest tracking check (T0a). ≈ 2026-12-07: first analysis of the positioning data (T6b).
