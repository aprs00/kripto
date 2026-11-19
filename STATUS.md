HEALTH: OK — trader, live watcher, all three data recorders and nightly data fine; research session 11-19 changed backtest internals (results unchanged, tested).

_Updated 2026-11-19 ~07:30 UTC (research). Detail: journal/2026-11-19.md._

## Today in plain words
1. **Friday-follow did not survive the fair test.** On the 82 hand-picked coins it looked good (Sharpe 1.06). On all 698 Binance coins that were
   ever in the top 100 (dead ones included) it falls to 0.78 for the chosen setting and 0.61 averaged over settings. That is below the 0.8 bar I wrote
   down before the test, so **no paper book**. Why: most of its profit came from being long coins that later survived and made my hand-picked list.
   On the other coins it earned almost nothing since 2024. The idea stays open, but my expectation for it is low.
2. **The Sunday fade held up on coins it had never seen.** On 11-15 I noticed that big Sunday-afternoon moves (New York 12:00→18:00) tend to reverse
   over the next day. Today, on 616 coins outside the original list, with the pass/fail rule written down first: +0.62% per trade on average,
   positive in every year, statistically solid. It is **not a strategy yet**: next Tuesday it gets a proper walk-forward test. My main worry: it
   may be one market-wide bet per Sunday (about 50 a year), which would make live evidence slow.
3. **Fixing churn in the new-listing shorts did not pass.** After XTEN cost ~80 bp for a one-day hold, I tested a "harder to get in than to stay in"
   volume rule. It cuts costs, but on Hyperliquid it also lowered the Sharpe (1.45 → 1.37) and deepened the drawdown. The current exit doubles as a
   protection against squeezes in thin, dying coins. Rule unchanged. I'll re-check it after the cost model is re-fitted (from 11-24).
4. **Main-book mixes re-checked under the stricter 11-17 reading rule: no change.** Hyperliquid main = the self-choosing blend; Binance main = flow +
   momentum + blend, a third each.
5. **Plumbing:** the big 698-coin hourly test needed 3.8 GB of memory and was killed twice (limit 2 GB). I rewrote the backtest's memory handling,
   not the test. Results are identical to the old code (checked on six strategies), and it now fits in 2 GB. Also started a nightly download of
   Binance positioning history (top traders' long/short ratios, open interest), about 9 nights to fill 2021–2026, for a test around 11-29.

## Books (07:25 UTC; ten days of paper P&L is noise, ±4 Sharpe)
| book | $1,000 (shadow $2,000) | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $990 (−1.0%) | $194 (−3.2%): 1 position fits |
| main_bn (flow + momentum + blend) | $946 (−5.4%) | $200 (+0.0%) |
| funding pair ($2,000) | $2,013 (+0.7%; funding +$20.5) | $202 (+0.9%) |
| tsmom / tsmom@bn | +8.1% / +7.9% | +4.6% / +3.7% |
| blend / blend_nested | +2.9% / −0.1% | +0.2% / −3.4% |
| listing_short | −1.0% (flat now) | −1.0% |
| xsmom@bn / xsmom_k@bn / flow@bn | −14.9% / −11.9% / −3.3% | −10.8% / −2.8% / −2.7% |
| xsmom_k (HL) | −1.6% | −2.6% |

## Candidates (walk-forward out-of-sample Sharpe after costs; worst = lowest stress test). None passes the real-money gate.
| strategy | Hyperliquid | Binance (all perps, 6 y) | worst | missing |
|---|---|---|---|---|
| blend, components chosen by rule (HL main) | 1.87 | 1.16 | 1.29 / 0.98 | multiple-testing check (0.63 < 0.9) |
| funding pair | 1.26 (1.7 y) | n/a | 1.43 | multiple-testing check; deployable only at half size |
| blend (hand-picked; the $200 reference) | 1.61 | 1.30 | 1.15 / 0.99 | multiple-testing check (0.81) |
| flow (Binance) | n/a | 1.42 (settings averaged: 1.25) | 0.75 | multiple-testing check (0.88) |
| broad momentum | −0.09 (averaged: 0.47) | 1.34 (averaged: 1.43) | 1.03 | weak on HL |
| listing shorts | 0.89 (averaged: 1.20) | 0.86 (averaged: 0.68) | 1.33 / 0.85 | multiple-testing check |
| friday_follow (Binance hourly, fair universe) | n/a | 0.78 (averaged: 0.61) | 0.43 | below 0.8: no book |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; the funding pair about 4–5% a year
at a deployable size (≈ $40/yr on $1,000, ≈ $8/yr on $200). No real money should go in before the paper books have tracked their backtests
for 2–3 months. That decision is yours.

## Forward ledger
Too early (≈ 10 forward days). First verdicts around 12-09.

## Next
Tue 11-24 research: Sunday-fade walk-forward (formulations thought through first); cost-model re-fit on two weeks of live fills, with a volatility
term. ≈ 11-26: first look at Hyperliquid order-flow data. ≈ 11-29: Binance positioning history complete → first test. blend_nested refit due 2027-01-02.
