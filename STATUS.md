HEALTH: OK — all services healthy at the 08:25 review: 25/25 hourly trader runs, data fresh, recorders without errors. Binance main −6.4% (explained below).

_Updated 2026-11-22 08:30 UTC (daily review after the weekly retro). Detail: journal/2026-11-22.md._

InSilico pass 3: 31 of 213 test forms done, 6 of 42 items closed (2 open, 1 confirmed on paper). Best lead: resting bids 30 sigma (about 3%) below the price on the 20 most-traded Binance coins, sold an hour later. Walk-forward run on 2026-11-23 (registered): +14.7% a year out of sample at 5% per order, every year 2021–26 positive, booked worst drawdown −6% (the intraday mark in a crash is far deeper), unchanged at double costs, with one minute of delay and at $200. All 18 settings worked and choosing between them added nothing, so the frozen rule is the candidate. It passes the incubation gate on backtest. Not proven: that a resting order really gets filled in those minutes. Next: build the live paper book for it (E2b), tests first.

## This week's most important finding
**My Binance research data contained things the bot cannot trade.** Binance added about 245 stock, commodity and FX contracts (Apple, AMD, gold…) in 2026. The
live bot excludes them; the research data did not, and by summer 2026 they were almost half of the "top 30 coins by volume". I removed them.
Effect on the same settings, before → after: over six years small (flow 1.49 → 1.43, broad momentum 1.34 → 1.31, blend 1.19 → 1.18, listing shorts 0.42 → 0.33). For 2026
alone it is bigger: **flow 0.90 → 0.45, listing shorts +0.36 → −0.30, momentum 1.61 → 1.35**. The old Binance walk-forward numbers in the table are therefore a bit
too good until re-run on Tuesday. The Sunday fade was re-checked on clean data and still holds (+0.65% per trade, positive in both periods).

## Why Binance main dropped (−3.1% → −6.4%)
Three small coins the momentum strategy held after big rises (IDOL, EVAA, AKE) fell 42–48% in one night: −4.3% of that book, with the 5%-per-coin cap in force. Checked:
fills normal, live matches its backtest replay (gaps ≤ 0.35% over the last 4 days), and those coins are genuine members of the tested universe (29–30 of 30 match). It is a real
risk of the strategy, not a bug. xsmom@bn −17.4% (true peak-to-now −17.5%), a little beyond its backtest worst (−16%); kill switch −25%.

## Books (11-22 08:25 UTC; two weeks of paper P&L is noise)
| book | $1,000 (shadow $2,000) | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $1,012 (+1.2%) | $191 (−4.4%): 1 position fits |
| main_bn (flow + momentum + blend) | $936 (−6.4%) | $201 (+0.3%) |
| funding pair ($2,000) | $2,012 (+0.6%; funding +$20.7) | $202 (+0.9%) |
| tsmom / tsmom@bn | +12.5% / +12.6% | +7.7% / +6.5% |
| blend / blend_nested | +6.7% / +2.1% | +3.0% / −4.5% |
| blend@bn | −4.3% | +0.9% |
| listing_short | −1.0% (flat) | −1.0% |
| xsmom@bn / xsmom_k@bn / flow@bn | −17.4% / −13.3% / −5.1% | −11.0% / −3.6% / −2.3% |
| xsmom_k (HL) | −0.8% | −0.6% |

## Candidates (walk-forward out-of-sample Sharpe after costs; worst = lowest stress test). None passes the real-money gate.
Binance column = before the data fix (to be re-run 11-24). Hyperliquid column unaffected.
| strategy | Hyperliquid | Binance (6 y) | worst | missing |
|---|---|---|---|---|
| blend, components chosen by rule (HL main) | 1.87 | 1.16 | 1.29 / 0.98 | multiple-testing check (0.63 < 0.9) |
| funding pair | 1.26 (1.7 y) | n/a | 1.43 | multiple-testing check; deployable only at half size |
| blend (hand-picked; the $200 reference) | 1.61 | 1.30 | 1.15 / 0.99 | multiple-testing check (0.81) |
| flow (Binance) | n/a | 1.42 (averaged 1.25) | 0.75 | multiple-testing check; weakest after the fix |
| broad momentum | −0.09 (averaged 0.47) | 1.34 (averaged 1.43) | 1.03 | weak on HL |
| listing shorts | 0.89 (averaged 1.20) | 0.86 (averaged 0.68) | 1.33 / 0.85 | multiple-testing check; 2026 negative on Binance |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; the funding pair about 4–5% a year at a deployable size
(≈ $40/yr on $1,000, ≈ $8/yr on $200). No real money before the paper books have tracked their backtests for 2–3 months. That decision is yours.

## Other findings
* Live orders on Hyperliquid go out about 12 minutes after the price the backtest assumes. That delay looks to cost about 0.05–0.17% per trade (weak evidence, 14 runs), so the
  earlier "real costs are only 56% of the model" claim is not established. The cost re-fit will include it. Binance: about zero.
* Two old "dead" ideas (long-only trend, funding-spike fade) were tested in only one form each; now OPEN with low prior.
* Forward ledger: 11–13.7 forward days; too early (first verdicts about 12-09).

## Next
Tue 11-24: re-run the Binance walk-forwards on clean data, Sunday-fade walk-forward, cost re-fit. ≈ 11-26 Hyperliquid order-flow data. ≈ 11-29 Binance positioning
(the metrics download now skips stock perps). blend_nested refit due 2027-01-02.
