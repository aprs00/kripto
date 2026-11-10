HEALTH: OK — trader (HL + Binance), collector and timers healthy; one new candidate (cross-venue funding capture) and the blend survived its hindsight test; nothing passes the gate yet, main books flat.

_Updated 2026-11-10 17:40 UTC (interactive session with the owner). Research results below are from the 06:40 session._

## Mandate (owner, 2026-11-10): "the only rule is that it should create a profitable trading bot, rest is up to you"
Taken literally. Decided under it: (1) from Thursday the main paper books stop sitting flat and trade my best current estimate
(Hyperliquid: the rule-picked blend; Binance: flow + broad momentum + blend), at $1,000 and $200, so "the bot" has a real track
record to judge; the strict statistical gate stays and now governs one thing: when I tell you the evidence justifies real money.
(2) Live market-data streams are allowed, so Hyperliquid order flow gets collected (it cannot be backfilled). Unchanged, on
purpose: paper only until you yourself fund an account and create keys; nothing illegal; hands off the other project on the server.

## Evening session (owner: "why isn't it always live?", "why only daily data?", "this is not self-improving")
* **It is always on now.** A permanent process checks every position on both exchanges every 20 seconds and applies the safety
  stop within about 40 seconds instead of up to an hour. Trade decisions still happen when a bar closes, because:
* **Deciding more often was tested and loses.** Over 5.7 years, deciding every 4 hours or every hour earns 3–6% a year more
  before costs but trades 2–6 times as much; after costs the result is worse (trend: Sharpe 0.92 → 0.78 → 0.58).
* **The most important finding: our backtests have been charging too much for trading on Hyperliquid.** 234 real paper fills
  cost 5.4 bp each; the backtest assumed 9.6 bp. With realistic costs every HL number improves (blend 1.56 → 1.73) and the three
  ideas that "died on costs" become weakly positive (0.3–0.9). Two calm days are not enough to rewrite the model: it is re-fitted
  from two weeks of fills (from 11-24), and nothing is promoted on the strength of it before then.
* **Why the system did not find these itself:** it reviewed its own recent changes every week, never the choices it was born
  with. There is now a list of every such assumption with its evidence (docs/assumptions.md); the weekly retrospective must
  test the two weakest each week.

## $200 next to $1,000 (owner 17:10: "test also with 200 dollars")
Every book now has a $200 twin that receives the same targets (`small:` books; first trades at the 11-11 00:00 bar), and every
future result reports the $200 account next to the $1,000 one. First comparison, backtest of each candidate's chosen settings
over its full history (in-sample Sharpe, so higher than the out-of-sample numbers below; read the difference between the columns):

| strategy | $1,000 account | $200 account | names held ($1,000 → $200) |
|---|---|---|---|
| funding capture (both venues) | 1.89 | 2.21 | 19 → 19 |
| listing shorts (HL) | 1.56 | 1.47 | 8 → 4 |
| blend, hand-picked (HL) | 1.56 | 1.81 | 25 → 15 |
| trend (HL / Binance) | 0.87 / 1.16 | 0.93 / 1.23 | 19 → 15 |
| blend, rule-picked (HL / Binance) | 1.41 / 1.62 | 0.99 / 1.41 | 35 → 19 |
| broad momentum (Binance) | 1.49 | 0.97 | 32 → 20 |
| flow (Binance) | 1.31 | 0.72 | 32 → 26 |

**Reading.** At $200 the $10 minimum order is 5% of the account, so books that need 30 names lose a third to a half of their
edge (flow, broad momentum, the rule-picked blend). Books with few, larger positions are unaffected: funding capture, listing
shorts, trend, the hand-picked blend. Where $200 looks *better* that is noise (fewer trades), not an advantage. In money terms
$200 earns a fifth of what $1,000 does at the same percentage: at 12–27% a year that is $24–54 a year.

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
