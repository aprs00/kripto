HEALTH: OK — trader (HL + Binance), collector and timers healthy; harness rebuilt and candidates re-measured; nothing passes the gate yet, main books flat.

_Updated 2026-11-09 23:30 UTC (interactive session with the owner)._

## What changed today (owner: "$200-level earnings won't cut it"; $1,000 available; steady risk)
* **Main paper books are now $1,000** (one on HL, one on Binance: alternative homes for the same $1,000). The $10 minimum
  order is 1% of the account instead of 5%, so 20–30 name books can actually be traded.
* **Tests no longer depend on which day a schedule starts.** A strategy that rebalances every n days now trades as n
  staggered slices, in the backtest and live. Before, one lucky start day made small momentum look twice as good as it is.
* **Every result carries its own stress test** (double costs, one bar late, first 6/12 months dropped); the gate reads the
  worst case.
* **Forward ledger:** every tested configuration, alive or dead, is frozen and scored only on data that arrives after it
  was tested. This is the evidence that cannot be overfitted. It needs ≥ 30 days before it says anything.
* **Fewer Claude sessions:** research Tue + Thu, retrospective Sun, one review a day. An hourly script (no Claude) watches
  health, calls a review when something breaks, and writes an ALERT here itself if Claude stops working.

## Books
| book | size | state |
|---|---|---|
| main (HL), main_bn (Binance) | $1,000 each | flat by design: nothing has passed the gate |
| shadow: tsmom, xsmom, listing_short, xsmom_k, blend (HL) | $2,000 each | tsmom +0.25%, xsmom −0.87% after one day (noise); others start at the 11-10 00:00 bar |
| shadow: xsmom_k@bn, flow@bn, tsmom@bn, **xsmom@bn, blend@bn (new)** | $2,000 each | first Binance trades on the 11-10 00:00 bar |

## Candidates, re-measured with the stricter harness (walk-forward out-of-sample Sharpe, net of costs)
| strategy | Hyperliquid (3 y) | Binance, all 923 perps (6 y) | worst-case stress | fails |
|---|---|---|---|---|
| **blend** (trend + small momentum + listing shorts) | **1.61** | **1.30** | 1.15 / 0.99 | multiple-testing check (0.81, needs 0.90) |
| flow (follow taker buying/selling) | not testable | **1.42** | 0.75 | multiple-testing check (0.88) |
| broad momentum | −0.09 | **1.34** | 1.03 | multiple-testing check (0.85); negative on HL |
| small momentum | 0.73 | 1.12 | 0.31 / 0.94 | weak and fragile on HL |
| listing shorts | 0.89 | 0.86 | 1.33 / 0.85 | multiple-testing check; funding data incomplete |
| trend | 0.08 | 0.65 | 0.49 / 0.97 | weak alone |

**Honest reading.** Three candidates are close to the gate and none passes. The blend's 1.61 still has a known flaw: its
three components were picked with hindsight; choosing them out-of-sample gave 0.6–1.2 in a first check. If the edge is real
at Sharpe 0.6–1.2, a $1,000 account at this risk level grows about 12–27% a year ($10–22 a month), with 20–30% drawdowns.
No real money should go in before the paper books have tracked their backtests for 2–3 months. That decision is the owner's.

## Next
* Tue 11-10 research: the blend with components chosen out-of-sample (H4). This decides whether 1.61 is real.
* ≈ 11-16: first live-vs-backtest tracking check. Then: cheaper (passive) execution on HL, funding on listing shorts,
  HL-vs-Binance funding capture. First forward-ledger reading ≈ 12-09.
