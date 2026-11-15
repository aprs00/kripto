HEALTH: OK — 11-15 retro: trader hourly on both venues, live watcher, both collectors (errors 0), data fresh; disk 67%. Fixed today: the forward ledger could not see Binance (data stopped at 10-31).

_Updated 2026-11-15 ~07:45 UTC (Sunday retrospective)._

## This week in one paragraph
I built the machinery: two exchanges, a two-exchange funding book, live recording of Hyperliquid order flow, an intraday order engine,
$200 twins of every book, and a ledger that scores frozen choices on days after they were made. I also found three foundation errors:
the cost model is about 1.8× too expensive, the funding trade assumed one account, and results depended on the start weekday.
**Edge evidence did not move.** Every candidate passes the out-of-sample and stress tests on Hyperliquid and fails only the
multiple-testing check (it needs 0.9; best so far 0.88). What can move that now is time: live tracking, the forward ledger and the new
Hyperliquid data. Running more backtests on the same history can't.

## Books after 6 days (all noise: a live Sharpe after a week has an error bar of about ±4)
| book | $1,000 / $2,000 size | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $1,001 (+0.1%) | $195 (−2.4%): only 1 position fits |
| main_bn (flow + momentum + blend) | $956 (−4.4%) | $201 (+0.3%): 2 positions fit |
| funding pair book ($2,000) | $2,008 (+0.4%; funding +$12.1, fees $2.6) | $201.8 (+0.9%) |
| tsmom / tsmom@bn | +8.8% / +8.8% (different coins, both short the majors) | +5.5% / +4.6% |
| blend / blend_nested / blend@bn | +2.9% / +1.0% / −5.5% | +0.7% / −2.5% / +1.6% |
| flow@bn / xsmom@bn / xsmom_k / xsmom_k@bn | −1.9% / −14.3% / −2.3% / −12.1% | −2.7% / −11.3% / −3.1% / −3.2% |
| listing_short | flat (no recent listing passes the volume filter) | flat |

The Binance momentum books' losses are mostly one event: the AKE short squeeze on 11-13 (+370% in a day, verified as real). Worst book
drawdown −14%; the kill switch is at −25%. Live costs per fill stay at 0.2–2 bp, in line with the 11-10 cost check.

## $200 decision (made today)
At $200 the main books can't hold their mix: most weights fall below the $10/$5 minimum order. **If you fund $200, the book to watch
is `small:blend`** (HL: trend + concentrated momentum + listing shorts). It holds 10 positions at $200. Its full-history Sharpe at the $200 size
is 1.81, the highest among the HL candidates that fit in one account. The funding pair book also works at $200 but needs two exchange accounts
of $100 each and earns about $8 a year at a safe size. `small:main` stays on as the record of why the mix doesn't fit.

## What the retro found
1. **The forward ledger was blind on Binance.** The Binance universe was built from monthly archives only, so it ended on 31 Oct and every
   Binance row showed "0 forward days". It would have stayed that way until December, and "too early" hid it. Fixed: the download now tops up
   to yesterday from the public API, and the ledger warns about any stale source. Binance rows now have 5 forward days, like Hyperliquid.
2. **Picking the "best" parameter set mostly adds noise.** On the same out-of-sample periods, averaging all pre-registered settings beat
   picking the best past performer in 6 of 9 strategy/exchange pairs (mean Sharpe 0.95 vs 0.78). Every result now also reports the average,
   and Tuesday's session will write that into the rules. It doesn't promote anything; it changes how I read old verdicts. For example, trend on
   Hyperliquid is 0.53 averaged against 0.18 picked.
3. Old "dead" list audit: short-term reversal really is dead (four different versions failed, reason known). Low-volatility was tested in only
   one form, so it is back to open, with three untried versions queued.

## Candidates (walk-forward out-of-sample Sharpe after costs; worst = lowest stress test). None passes the real-money gate.
| strategy | Hyperliquid | Binance (all perps, 6 y) | worst | missing |
|---|---|---|---|---|
| blend, components chosen by rule (HL main) | 1.87 | 1.16 | 1.29 / 0.98 | multiple-testing check (0.63 < 0.9) |
| funding pair | 1.26 (1.7 y) | n/a | 1.43 | multiple-testing check; deployable only at half size |
| blend (hand-picked; the $200 reference) | 1.61 | 1.30 | 1.15 / 0.99 | multiple-testing check (0.81) |
| flow (Binance) | n/a | 1.42 (settings averaged: 1.25) | 0.75 | multiple-testing check (0.88) |
| broad momentum | −0.09 (averaged: 0.47) | 1.34 (averaged: 1.43) | 1.03 | weak on HL |
| listing shorts | 0.89 (averaged: 1.20) | 0.86 (averaged: 0.68) | 1.33 / 0.85 | multiple-testing check |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; the funding pair about 4–5% a year
at a deployable size (≈ $40/yr on $1,000, ≈ $8/yr on $200). No real money should go in before the paper books have tracked their backtests
for 2–3 months. That decision is yours.

## Forward ledger
Too early: 4–6 forward days on both exchanges (Binance rows are scored again since today's fix, back to their 11-09 registration). First verdicts around 12-09.

## Next
Tue 11-17 research: live-vs-backtest tracking replay (T0a), then the parameter-averaging rule (WF1), then the short-squeeze study for the
Binance momentum books (R1, together with the low-volatility filter). Cost-model re-fit from 11-24. First reading of Hyperliquid order-flow
data around 11-26. blend_nested refit is due 2027-01-02 (the watchdog will remind me).
