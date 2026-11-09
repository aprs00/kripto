HEALTH: WARN — fixed a critical bug: all research from 2026-11-08 was invalid (timestamp-unit bug); re-run scheduled for today's research session.

_Updated 2026-11-09 04:40 UTC (review session)._

## What happened
`rebalance_rows` assumed nanosecond timestamps, but pandas 3 loads microseconds. Effects: live strategies never rebalanced (books stayed flat),
and every backtest from 2026-11-08 rebalanced in long blocks and then froze. Fixed and covered by a regression test. The shadow books took their first
positions at 04:26 UTC. **Every verdict in research/findings.md (ALIVE and DEAD) is provisional until the re-run (backlog T0).**

## Main book ($200 paper)
Equity $200.00, +0.00%. Flat: no strategy is in incubation/active.

| book | equity | return | positions | fills | fees | funding |
|---|---|---|---|---|---|---|
| main | $200.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |
| shadow:tsmom | $1999.27 | −0.04% | 11 | 11 | $0.57 | $0.00 |
| shadow:xsmom | $1997.89 | −0.11% | 28 | 28 | $1.13 | $0.00 |
| shadow:carry (retired, frozen) | $2000.00 | +0.00% | 0 | 0 | $0.00 | $0.00 |

First fills: fees 4.5 bp (taker), slippage averages 0.5–0.9 bp (max 2.8 bp). Plausible.

## Strategies (numbers from 2026-11-08 are INVALID, kept only for reference)
| strategy | status | old (invalid) evidence |
|---|---|---|
| tsmom | candidate | BN 1.26 / HL 0.55 |
| xsmom | candidate | BN 0.63 / HL 0.71 |
| carry | retired (re-check in re-run) | BN 1.35 / HL −0.58 |
| xsrev, lowvol, funding_contra | rejected (re-check in re-run) | negative |

## Next
* Research (06:40): **T0: re-run all pre-registered grids with the fixed code**, then re-decide every verdict and status.
* Review: check tsmom rebalances daily at the 00:00 bar and xsmom every 3 days; funding accrual is now active for held positions.
