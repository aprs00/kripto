HEALTH: OK — trader, ladder, collectors and websockets running; ladder@bn and the funding pair now trade in main books; no strategy is held back without a written clause.

_Updated 2026-11-27 ~07:25 UTC (research session). Detail: journal/2026-11-27.md._

## Held back (written gate clauses applied by `scripts.held_back`; a strategy that fails nothing must trade)
| strategy | pick | grid avg | DSR | worst | grid med | other venue | status / alloc | fails (written clauses) |
|---|---|---|---|---|---|---|---|---|
| fspread_hold@pair | 5.66 | 5.66 | 1.00 | 5.08 | 7.17 | – | incubation 0.5 | none (trading) |
| ladder@bn | 1.94 | 2.19 | 0.98 | 2.00 | 1.88 | – | incubation 1.0 | none (trading) |
| blend_nested | 1.87 | 1.87 | 0.61 | 1.29 | 1.57 | 1.17 | incubation 1.0 | DSR>0.9 |
| blend | 1.61 | 1.61 | 0.82 | 1.15 | 1.56 | 1.35 | candidate 0.0 | DSR>0.9 |
| flow@bn | 1.45 | 1.36 | 0.88 | 1.20 | 1.00 | – | incubation 0.5 | DSR>0.9 |
| carry_trend@bn | 1.44 | 1.46 | 0.87 | 1.29 | 1.34 | – | candidate 0.0 | DSR>0.9 |
| carry@bn | 1.30 | 1.31 | 0.77 | 1.34 | 1.29 | – | candidate 0.0 | DSR>0.9 |
| blend_nested@bn | 1.17 | 1.17 | 0.61 | 0.99 | 1.60 | 1.87 | incubation 0.5 | DSR>0.9 |
| xsmom_k@bn | 0.99 | 1.26 | 0.50 | 0.83 | 1.03 | 0.73 | candidate 0.0 | DSR>0.9 |
| xsmom@bn | 1.27 | 1.43 | 0.76 | 1.27 | 1.24 | -0.09 | candidate 0.0 | DSR>0.9, other venue>0 |
| listing_short | 0.89 | – | 0.33 | 1.33 | 1.34 | 0.81 | candidate 0.0 | grid avg>0.8 (missing), DSR>0.9 |
| tsmom@bn | 0.79 | 1.22 | 0.31 | 1.08 | 0.95 | 0.08 | candidate 0.0 | pick>0.8, DSR>0.9 |
| tsmom | 0.08 | – | 0.31 | 0.49 | 0.62 | 0.79 | candidate 0.0 | pick>0.8, grid avg>0.8 (missing), DSR>0.9 |

Two strategies pass every clause, and both now trade in a main book: **ladder@bn** (resting bids, inside main_bn since 06:56) and **fspread_hold@pair** (HL-vs-Binance funding
capture, in the new two-account book main@pair since 07:06). Everything else fails the multiple-testing check (DSR ≤ 0.9).

## Scoreboard
**Scoreboard, last 7 days** (scripts.scoreboard): walk-forward experiments 12, single backtests 339, new studies 94, commits 245. Lifecycle changes: xsmom_k: candidate 0.0 -> retired 0.0; flow@bn: incubation 0.3333 -> incubation 0.5; xsmom@bn: incubation 0.3333 -> candidate 0.0; blend@bn: incubation 0.3333 -> retired 0.0; fspread_hold@pair: candidate 0.0 -> incubation 0.5; ladder@bn: new (incubation); blend_nested@bn: new (incubation); carry@bn: new (candidate); carry_trend@bn: new (candidate). InSilico items closed: 43 (OPEN 23, DEAD 14, UNTESTABLE 5, CONFIRMED 1).
Paper vs backtest per main book: too early (main 18 days, main_bn 18 days on a mix switched 11-26, main@pair 0 days); the weekly `scripts.live_vs_backtest` runs in Sunday's retro.
**My mistakes this week:** ladder@bn held back 4 days (11-23 → 11-27) by a rule I invented; the funding pair had no main book to go into, so a pass could never have traded (fixed today);
first HL-ladder study run gave 52 fake fills (forward-filled over data gaps; caught and fixed in-session); InSilico idle 40 h (11-25/26) reported as healthy; the M1 "hindsight-free blend"
clause applied on HL only for two weeks; a research day lost to the usage limit (11-24); 233 stock/commodity perps in the Binance research universe until 11-22.

## Today in plain words
1. **The resting-bid ladder now trades inside the Binance main book.** Each order is 2.9% of the whole main_bn account ($27 on $926; ≈ $5.8 in the $200 twin, where BTC/ETH are too small to buy).
   It is flat about 97% of the time, so it shares the account's margin with the daily books instead of taking a slice of capital. Worst case (2025-10-10-type crash at this size): about −10%
   on top of the daily books. Its own books: 2 fills since 11-23, +0.4%.
2. **The funding pair passes the real-money test on a longer history, but its edge is shrinking.** Re-running the same 6 settings on 2.85 years (Hyperliquid funding now goes back to 2023-05):
   out-of-sample Sharpe 5.7, multiple-testing check 1.00, worst stress 5.1. But the yearly net return fell from 21% (2023) to 19%, 6% and 1.9% (2026 so far): the gap between Hyperliquid
   and Binance funding is closing. Also, its live paper book moves 3× more day to day than the backtest says, so the real Sharpe is probably nearer 1.5–2. It now trades in **main@pair**:
   one Hyperliquid and one Binance account, $1,000 in total, at half the paper book's size (what survives a crash in two separate accounts). **Expect about 1–4% a year (≈ $10–40 on $1,000)**:
   low risk, little money.
3. **The main books now run at your chosen risk level.** Monthly multiplier switched on: Hyperliquid ×0.87, Binance ×1.16 (next check 12-01).
4. Checked: the Hyperliquid main book's rule still picks lowvol even with the longer funding history, so nothing changes there before the 2027-01-02 refit.
5. First look at the ladder on Hyperliquid's own minute data: only 7 fills in 15 days, and no sign yet that Hyperliquid's thinner order books drop further than Binance's. Re-check mid-January.

## Books (11-27 07:20 UTC; 18 days of paper P&L is noise)
| book | $1,000 (shadow $2,000) | $200 twin |
|---|---|---|
| main (HL, blend_nested ×0.87) | $999 (−0.1%) | $193 (−3.7%): 1 position fits |
| main_bn (flow + blend_nested@bn ×1.16, + ladder sleeve) | $926 (−7.4%) | $199 (−0.5%) |
| **main@pair (new: funding pair, alloc 0.5)** | $1,000 (opened 07:06, 12 legs, gross 0.6) | $200 (9 legs) |
| funding pair shadow ($2,000) | $2,013 (+0.7%; funding +$19, fees $4.9) | $201 (+0.7%) |
| ladder@bn shadow | +0.4% (2 fills) | +0.4% |
| tsmom / tsmom@bn | +9.7% / +10.1% | +6.4% / +4.5% |
| blend / blend_nested (HL) / blend_nested@bn | +5.2% / +0.8% / +0.5% | +0.6% / −3.9% / +1.5% |
| carry@bn / carry_trend@bn (since 11-26) | +1.1% / 0.0% | 0.0% / 0.0% |
| flow@bn / xsmom@bn / xsmom_k@bn | −7.3% / −16.7% / −15.3% | −1.5% / −11.5% / −5.8% |
| listing_short | −1.0% (flat) | −1.0% |

## Candidates (walk-forward out-of-sample Sharpe after costs: pick / grid average; worst = lowest stress test; $200 = same config in the small account)
| strategy | Hyperliquid | Binance 6 y (clean) | worst | $200 | status |
|---|---|---|---|---|---|
| ladder (resting bids) | n/a | 1.94 / 2.19 | 2.00 | 2.16 | **passes all; trading in main_bn** |
| funding pair (two venues, 2.85 y) | 5.66 / 5.66 | (pair) | 5.08 | 7.09 | **passes all; trading in main@pair**; edge decaying, live vol 3× backtest |
| blend, components chosen by rule | 1.87 | 1.17 | 0.99 | — | in both main books; multiple-testing check 0.61 |
| flow (Binance) | n/a | 1.45 / 1.36 | 1.20 | 1.25 | in main_bn; check 0.88 |
| funding carry / trend-filtered carry | dead on HL | 1.30 / 1.44 | 1.34 / 1.29 | 1.06 / 0.78 | candidates; check 0.77 / 0.87 |
| broad momentum / trend / listing shorts | weak | 1.27 / 0.79 / 0.81 | | | candidates |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; ladder ≈ 8%/yr on its own at this size (backtest); the funding pair ≈ 1–4%/yr
at a deployable size. None of the main books has tracked its backtest long enough yet (the gate wants 60+ days). No real money before that. That decision is yours.

## Next
Next research session: T5b Binance positioning once 2021–22 coverage ≥ 95% (today 72% / 76%); first main_bn ladder fills vs its shadow; E1 + LQ1 liquidation prints (≈ 12-01);
main_scale re-check 12-01. X1f (funding pair live vol vs backtest) at 30 live days (≈ 12-12). Fill-delay re-measure ≈ 12-09; HL order-flow re-check ≈ 12-23; HL ladder ≈ 2027-01-15.
Nested-blend refits (HL and Binance) 2027-01-02. Forward ledger: first verdicts ≈ 12-09.
InSilico pass 3: 228/246 forms done, 43/49 items closed; the remaining 6 wait for data still being collected (first due 12-05).
