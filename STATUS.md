HEALTH: OK — trader ran every hour (latest 00:03–00:09 UTC, 2026-11-09); no failed units, no ERROR events; data fresh (last_bar 20:00 = latest closed 4h bar); disk 64%.

_Updated 2026-11-09 00:27 UTC (review session). Added scripts/sql.py since the sqlite3 CLI isn't installed._

## Main book ($200 paper)
Equity $200.00, return since start +0.00%. Flat: no strategy is in incubation/active (none passed the HL gate).

| book | equity | return | positions | fills | fees | funding |
|---|---|---|---|---|---|---|
| main | $200.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |
| shadow:tsmom | $2000.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |
| shadow:xsmom | $2000.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |
| shadow:carry (retired, frozen) | $2000.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |

Shadow books have no positions yet by design: strategies rebalance on an epoch-anchored grid (tsmom
daily at the 00:00 UTC bar, xsmom every 3 days). The first targets are expected from the ~04:00 UTC run on 2026-11-09.

## Strategies
| strategy | status | evidence |
|---|---|---|
| tsmom (trend, L/S) | candidate | BN OOS Sharpe 1.26; HL OOS 0.55, grid median 0.89 |
| xsmom | candidate | BN 0.63, HL 0.71 |
| carry (funding) | **retired** | BN +1.35 but HL −0.58: on HL high-funding coins keep squeezing up (journal 2026-11-08) |
| xsrev, lowvol, funding_contra | rejected | negative after costs |

## Last research result
Hyperliquid has the trend signal, but costs eat most of it. The $10 minimum order rules out diversified books at $200.

## Next
* Review: confirm the shadow books take their first positions after the 00:00 UTC bar, and check that fills and slippage look plausible.
* Research: cost reduction + small-account construction for trend (T1c); trend-conditioned carry (T1d).
