HEALTH: OK — 08:25 review: trader ran every hour, watchers and all three data recorders (HL positions, HL trade flow, Binance liquidations) are fine, nightly data OK.

_Updated 2026-11-18 08:35 UTC (review). Detail: journal/2026-11-18.md. "Yesterday" below = the 11-17 research session._

## Review 08:25 (short)
* Everything ran: trader 25 runs in 25 h (last 08:10), live watcher every 20 s, HL collector errors=0, HL trade-flow recorder side check 228 ok / 0 bad,
  Binance liquidations 42,588 recorded since 11-17, no reconnects. Nightly data 02:51 OK. Disk 70%, RAM 4.7 GB free. No warnings in the trader log.
* Costs in the last day: 229 fills, average 2 bp slippage, in line with the model.
* **Listing shorts paid for a coin sitting on the liquidity line.** The book shorted the new coin XTEN on 11-16 when its average daily volume was just
  over the $1M minimum, paying 60 bp to get in, and closed it the next day when volume fell to $0.43M (22 bp to get out). About 80 bp round trip
  for a one-day hold, or ≈ 1% of the book. The rule did what it says, but the rule is wasteful. Added to the backlog (T2b-e): require more volume to
  enter than to stay in. Thursday's research decides whether it is tested.
* xsmom@bn is −15.2% (AKE squeeze; kill switch −25%). No lifecycle gate met.

## Today in plain words
1. **Do the paper books do what the backtests say? Yes.** I replayed every test book's backtest over exactly its live days and compared day by day.
   Hyperliquid books match almost perfectly (daily correlation 0.99–1.00, e.g. trend +8.32% live vs +8.25% replayed; same positions, same trading).
   Live trading costs are at or below the model everywhere except the new-listing shorts (new coins are thinner than the model assumes). The Binance
   gaps came from my replay, not the engine: it used today's coin list, which includes coins that only became big after pumping. The engine now
   records the coin list it actually used every bar. **No bug found in the trader.**
2. **The short-squeeze losses on Binance (AKE +370% on 11-13).** Over 2020–23 the shorts in those books lose money on their own, and a few squeezes
   do the damage. But removing the shorts makes the books far worse (Sharpe 1.23 → 0.33, drawdown −23% → −41%), because the shorts hedge the
   rest of the altcoin market. Filters that skip "dangerous" shorts didn't help either. What did help a little, on data it had never seen: no single
   coin above 5% of the book (either side). Adopted for the three Binance momentum/flow books. **It limits risk; it adds no edge.**
3. **New rule for reading backtests** (written today, applies from Thursday): the real-money gate uses the lower of "best setting" and "average of
   all settings", because picking the best setting mostly adds luck. It makes the real-money bar harder, never easier.
4. **New data recorder: Binance liquidations** (who got force-closed, live; nobody serves this history). Needed to tell a liquidation cascade from
   a normal sell-off. A catch: Binance's old address still accepts connections but sends nothing; the recorder uses the new one, and the watchdog
   now complains if no liquidation arrives for 2 hours.
5. **Friday-follow, survivorship check:** downloading hourly data for all 698 Binance coins that were ever in the top 100 (incl. dead ones). The test is
   written down in advance and runs Thursday.

## Books (08:25 UTC; ten days of paper P&L is noise, ±4 Sharpe)
| book | $1,000 (shadow $2,000) | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $1,001 (+0.1%) | $194 (−2.9%): 1 position fits |
| main_bn (flow + momentum + blend) | $944 (−5.6%) | $200 (−0.0%) |
| funding pair ($2,000) | $2,020 (+1.0%; funding +$22.7) | $202 (+1.2%) |
| tsmom / tsmom@bn | +7.8% / +7.4% | +4.2% / +3.3% |
| blend / blend_nested | +0.8% / +1.0% | −1.5% / −3.1% |
| listing_short | −1.0% (flat now) | −1.0% |
| xsmom@bn / xsmom_k@bn / flow@bn | −15.2% / −12.3% / −3.1% | −11.1% / −3.2% / −2.8% |
| xsmom_k (HL) | −2.9% | −3.6% |

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
Too early (≈ 8 forward days). First verdicts around 12-09.

## Next
Thu 11-19 research: re-pick the paper main-book mixes under the new reading rule; friday_follow on the fair 698-coin universe. From 11-24: re-fit the
cost model on two weeks of live fills, now with a volatility term (book: spreads widen with volatility). ≈ 11-26: first look at Hyperliquid order-flow
data. blend_nested refit due 2027-01-02.
