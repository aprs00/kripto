HEALTH: OK — 08:25 review: trader hourly, both venues, watcher, both collectors (errors 0) and the nightly data job all fine; disk 65%.

_Updated 2026-11-12 08:30 UTC (daily review; content below from the 07:20 research session, books refreshed)._

## Interactive session 11-11/12: one trader's public rules, tested (nothing passed)
You gave me a chat archive of a discretionary order-flow trader (BitMEX/Bybit, 2020–22). I turned it into 32 testable rules
(research/insilico_rules.md), fixed five tests in writing before looking at any result, and ran them on Binance data with real costs.
Books and candidates are unchanged: **none of this is traded**.

| rule | result (out-of-sample Sharpe, after costs) | verdict |
|---|---|---|
| Buy after a day when every trade-size group sold | 0.18 (just holding the coins: 0.96). Worked in 2021, +0.24 since 2023 | dead |
| Fade the weekend move back to Friday's price | −0.46, 0 of 6 settings positive, loses before costs | dead |
| Bid the old range high after a breakout (maker) | −34; 57% winners but −1.9 bp per trade before fees | dead |
| Mousetrap: failed break, small sold / large bought | −2.9; loses before costs, the size condition adds nothing | dead |
| Liquidation fade on 1-minute bars | 0.64; +78 bp per trade on 30 coins incl. 20 never used for fitting | open, not a candidate |

The liquidation fade is the only one left standing, and it is fragile: three market-wide crash days produced 72% of its profit, and
those are the minutes when real fills are worst. Next step is a live 1-minute paper book for it (backlog E1), not a backtest.
At $200 the intraday tests are identical in % (one $100 trade at a time is above every minimum); none is worth trading at either size.
New data that cannot be backfilled: Hyperliquid trade sizes per taker are recorded from today (kripto/flow.py).

## What changed today (the "run everything now" list from 11-10 is done)
1. **The main books now trade.** Until today `main` and `main_bn` sat flat because nothing had passed the statistical gate.
   Since 06:45 each trades my best current estimate, chosen by the fixed rule written on 11-10:
   * **Hyperliquid main ($1,000):** the rule-picked blend (`blend_nested`: listing shorts + trend + low volatility).
   * **Binance main ($1,000):** one third each of order flow, broad momentum and the blend.

   This is a **paper best estimate, not a recommendation to fund**. The full gate (and ≥ 60 days of tracking) still decides that.
2. **The funding trade trades on paper.** A new book holds each coin short on Hyperliquid and long on Binance (or the reverse)
   to collect the funding difference. It opened 8 pairs this morning, all short Hyperliquid.
3. **Hyperliquid order flow is now recorded.** One public live stream records who bought and who sold in the top 60 coins, every
   minute. This data can't be downloaded later, so recording starts now. I checked the buy/sell label against the order book
   (163 of 163 agree). The watchdog raises an alert if the stream goes silent for 5 minutes.
   It also records, by address, every trader who buys or sells more than $20k of a coin in a minute. Hyperliquid is one of the
   few exchanges that publishes this, and research says big orders are split over hours, so an order in progress may be visible
   (first test once there are 2 weeks of data, about 11-26).

## Important finding: the funding trade is smaller than it looked
The backtest showed +8.4%/yr with a worst drawdown of −1.7%. That assumed both legs sit in **one** account. With real money they
sit in two (one per exchange), and each account carries only one side of the trade. I simulated two separate accounts over
2024–2026 at their worst intraday prices:
* **At the backtest size, one account would have been wiped out on 10 Oct 2025** (the market-wide liquidation cascade:
  Binance long legs fell 45–81% within the day).
* **At half that size nothing is liquidated**, even with money moved between exchanges only weekly. One day still showed
  −70% inside one account. The other account gained the same.

So the deployable version earns **about 4–5% a year before costs, roughly $40 a year on $1,000**. The paper book keeps the larger
size so the signal stays measurable. Not modelled: an exchange force-closing the winning leg in a crash (auto-deleveraging).

## New-listing study (why the listing-shorts leg works)
New perps lose against BTC steadily for about 4 months, on both exchanges and in every year since 2020.
* Median loss against BTC after 60 days: −49% on Hyperliquid (129 listings), −34% on Binance (794 listings).
* 76–84% of listings are down after 60 days.
* The decline is steady, not concentrated in the first days, so the 60-day holding period is not a lucky pick.
* The risk sits in a few short squeezes: the worst listing cost a short 162% in funding.

## Books (2–4 days old: all of this is noise, live Sharpe error bars are about ±4)
| book | $1,000 / $2,000 size | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $998.87 (−0.1%, started today) | $199.99: only 1 position fits |
| main_bn (flow + momentum + blend) | $998.85 (−0.1%, started today) | $200.00: **nothing fits** (20 names, each under the $5 minimum) |
| funding pair book (shadow, $2,000) | $1,998.46 (−0.1%, opened today; funding +$0.07 so far) | $199.84 |
| shadow tsmom / tsmom@bn | +2.2% / +1.7% | |
| shadow blend_nested / blend / blend@bn | +0.7% / −0.8% / −0.2% | |
| shadow flow@bn / xsmom@bn / xsmom_k / xsmom_k@bn | −2.0% / −2.8% / −1.6% / −2.1% | |
| shadow listing_short | flat: the only listing in the last 60 days (XTEN, 10-27) trades < $1M/day, below the filter (checked 11-12) | |

**$200 vs $1,000:** at $200 the main books can barely hold the mix, so a $200 account would need its own concentrated choice
(listing shorts, trend or the funding pair, which keep their edge at $200). I'll decide that at Sunday's review, with a week of
the $200 books in hand.

## Candidates (walk-forward out-of-sample Sharpe after costs; worst = lowest stress test). None passes the real-money gate.
| strategy | Hyperliquid | Binance (all perps, 6 y) | worst | missing |
|---|---|---|---|---|
| blend, components chosen by rule (HL main) | 1.87 | 1.16 | 1.29 / 0.98 | multiple-testing check (0.63 < 0.9) |
| funding pair | 1.26 (1.7 y) | n/a | 1.43 | multiple-testing check; deployable only at half size (above) |
| blend (hand-picked) | 1.61 | 1.30 | 1.15 / 0.99 | multiple-testing check (0.81) |
| flow (Binance) | n/a | 1.42 | 0.75 | multiple-testing check (0.88) |
| broad momentum | −0.09 | 1.34 | 1.03 | negative on HL |
| listing shorts | 0.89 | 0.86 | 1.33 / 0.85 | multiple-testing check |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; the funding pair about
4–5% a year at a deployable size. No real money should go in before the paper books have tracked their backtests for 2–3 months.
That decision is yours.

## What only time can produce
Live-vs-backtest tracking check from about 11-16 (needs a week of books). Cost-model re-fit from 11-24 (needs two weeks of fills).
First reading of the order-flow data from about 11-26. Forward-ledger verdicts from about 12-09 (needs 30 days; today's
baseline holds 51 frozen configs).

## Next
Sunday 11-15 retro: the weekly review, including the $200 choice. Tue 11-17 research: tracking check (T0a), then listing-short
follow-ups (funding coverage, a 90/120-day hold). blend_nested component refit is due 2027-01-02 (the watchdog will remind me).
