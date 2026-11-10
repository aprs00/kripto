HEALTH: OK — trader (HL + Binance), collector and timers healthy; one new candidate (cross-venue funding capture) and the blend survived its hindsight test; nothing passes the gate yet, main books flat.

_Updated 2026-11-10 08:40 UTC (daily review). Research results below are from the 06:40 session._

**Review 08:40:** everything ran. Trader 33 runs in 25 h with no errors or warnings, data 4 h old, nightly data job and the
research session succeeded, collector 0 errors (3 days of market context, 2 days of positions and order books), disk 64%.
Fills look right: about 1 bp slippage, fees 4.5 bp on HL and 5 bp on Binance. One small fix: the status report still showed the
closed HL `xsmom` book with its old 30 positions; it now shows it closed ($1,975.42, −1.2%). No lifecycle changes.

## Today's research results (3 tests, all pre-registered before running)
1. **Is the blend's good number just hindsight? Mostly no.** I re-ran it with the component choice made by a fixed rule using
   only past data (every 60 days, keep the 3 best of 10 strategies so far). Hyperliquid out-of-sample Sharpe **1.87** over 2.2 years
   (worst stress case 1.29); Binance (all 923 perps, 5.4 years) **1.16**. The rule picks listing shorts + trend + low-volatility on HL.
   New shadow book `blend_nested` trades that choice.
2. **Cheaper (maker) orders don't save the day.** Resting orders cut fees by ~70%, but the orders that don't fill are the ones that
   run away, and the ones that do fill come as the price moves against you. Over 6 years of Binance data that took back as much as the
   fees saved. Conclusion: the way to cut costs is to trade less, not to trade differently.
3. **Trading less turned a dead idea into the cleanest candidate so far.** Hold a coin short on HL and long on Binance (or the reverse)
   when HL's funding is well above Binance's, and keep the pair until the gap flips. Price risk cancels. Out-of-sample: **+8.4%/yr,
   Sharpe 1.26, worst drawdown −1.7%** (1.7 years); all 6 settings tested are positive; every year positive. It earns from crowded
   leveraged longs on HL (we're short HL 95% of the time). Not yet traded on paper: it needs a book that holds positions on both
   venues at once, which I build next.

## Books
| book | size | state |
|---|---|---|
| main (HL), main_bn (Binance) | $1,000 each | flat by design: nothing has passed the gate |
| shadow: tsmom, listing_short, xsmom_k, blend, **blend_nested (new)** (HL) | $2,000 each | 0–2 days old: tsmom +0.8%, blend −0.2%, blend_nested +0.1%, xsmom_k −0.1%, listing_short flat (no new listing to short) (noise) |
| shadow: xsmom_k@bn, flow@bn, tsmom@bn, xsmom@bn, blend@bn | $2,000 each | first trades today, −0.7% to +0.1% (noise) |
| retired today: HL xsmom shadow (dead on HL; the Binance version keeps running) | | closed at $1,975.42 (−1.2%) |

## Candidates (walk-forward out-of-sample Sharpe, net of costs; worst = lowest of the stress tests)
| strategy | Hyperliquid | Binance (all perps, 6 y) | worst | fails |
|---|---|---|---|---|
| **funding capture, hold-until-flip** (both venues) | 1.26 (1.7 y, +8.4%/yr, DD −1.7%) | n/a | 1.43 | multiple-testing check: 1.7 years is too short to prove it |
| **blend, components chosen by rule** | **1.87** | 1.16 | 1.29 / 0.98 | multiple-testing check (0.63) |
| blend (hand-picked components) | 1.61 | 1.30 | 1.15 / 0.99 | multiple-testing check (0.81) |
| flow (Binance taker flow) | n/a | 1.42 | 0.75 | multiple-testing check (0.88) |
| broad momentum | −0.09 | 1.34 | 1.03 | negative on HL |
| listing shorts | 0.89 | 0.86 | 1.33 / 0.85 | multiple-testing check |

**Honest reading.** The blend now has a fairer test behind it, and the funding trade is a small-account edge of the kind the owner
asked for: low return, very low risk, and big funds don't bother with it. None of this proves an edge yet. Backtests on HL cover
only ~2 years, and the funding trade has 1.7 years. Untested risks for the funding trade: margin has to sit on two exchanges (≈ 2×
leverage on each), and a sudden price gap between the venues on a thin coin. If the edges are real: blend-type books ≈ 12–27%/yr at
20–30% drawdowns; funding capture ≈ 5–9%/yr at small drawdowns. No real money should go in before the paper books have tracked
their backtests for 2–3 months. That decision is the owner's.

## Next
* Thu 11-12 research: build the two-venue paper book so funding capture starts trading on paper (backlog X2). The forward ledger
  scores it from today either way.
* ≈ 11-16: first live-vs-backtest tracking check. First forward-ledger reading ≈ 12-09. blend_nested component refit 2027-01-02
  (the watchdog reminds me).
