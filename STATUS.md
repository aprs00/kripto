HEALTH: OK — all services, timers, data and collectors healthy at the 11-25 08:25 review; 11-24 sessions lost to the usage limit are now retried automatically.

_Updated 2026-11-25 ~08:35 UTC (review; research content from the 06:40 session). Detail: journal/2026-11-25.md._

## Today in plain words
1. **The Binance results hold on clean data.** I re-ran the main Binance tests after removing the stock/commodity contracts (data error found 11-22). Over six years
   nothing changed materially. Flow even looks a bit sturdier (worst stress test 0.75 → 1.20). The 2026-only damage is real but small next to six years.
2. **Trading costs: the model stays.** 17 days and 1,727 paper fills. Price impact is below what the backtests charge (Hyperliquid 4.0 vs 6.2 bp, Binance 1.1 vs 1.9).
   But Hyperliquid fills happened about 11 minutes after the price the backtest uses, and that delay cost more than the impact saved. Almost all of it was **one coin on its listing
   day (XTEN): about 1.6% per trade, against the model's maximum of 0.25%**. For normal coins, real cost ≈ model. So I withdraw the earlier claim that real costs are only 56% of the model.
   Fix applied: the bot now trades **3 minutes** after the hour starts instead of ~8 (data downloads moved after the trades).
3. **Sunday-afternoon fade: weaker than hoped, no book.** Out-of-sample Sharpe 0.44 (needed 0.8), loses money in a $200 account. It worked in 2020 and 2024–26, not in 2021–23,
   and it is mostly one market-wide bet per Sunday.
4. **First look at our own Hyperliquid order-flow data (13 days).** Neither total buying pressure nor big single traders' persistent buying predicts the next hours. One cell
   (4-hour flow → next day) looks interesting but rests on 12 days; re-check fixed for about 12-23.
5. **Cutting pumped coins from momentum's long side does not work** (3 new filters + 1 earlier): the pumps are where momentum earns its bull-year money; the overnight crashes are the price of that. The 5%-per-coin cap stays the protection.
6. **The Binance main book takes less risk than its target.** Mixing three books 1/3 each gives about 18% yearly volatility instead of 25–30%, so it would earn less than the expectation below. Fix to be decided next session (a general rule for all main books, not tuned to results).

## Books (11-25 06:40 UTC; 16 days of paper P&L is noise)
| book | $1,000 (shadow $2,000) | $200 twin |
|---|---|---|
| main (HL, blend_nested) | $1,017 (+1.7%) | $191 (−4.4%): 1 position fits |
| main_bn (flow + momentum + blend) | $922 (−7.8%) | $201 (+0.3%) |
| funding pair ($2,000) | $2,010 (+0.5%; funding +$20.1) | $201 (+0.4%) |
| tsmom / tsmom@bn | +12.7% / +13.0% | +8.2% / +6.7% |
| blend / blend_nested | +7.3% / +2.5% | +2.9% / −4.6% |
| blend@bn | −5.8% | −0.2% |
| listing_short | −1.0% (flat) | −1.0% |
| xsmom@bn / xsmom_k@bn / flow@bn | −18.7% / −15.2% / −6.6% | −11.0% / −5.2% / −2.2% |
| xsmom_k (HL) | −0.3% | −0.1% |
| ladder@bn (resting bids, since 11-23) | +0.4% | +0.4% |

## Candidates (walk-forward out-of-sample Sharpe after costs: pick / grid average; worst = lowest stress test; $200 = same config in the small account). None passes the real-money gate.
| strategy | Hyperliquid | Binance 6 y (clean, 11-25) | worst (BN) | $200 (BN) | missing |
|---|---|---|---|---|---|
| blend, components chosen by rule (HL main) | 1.87 | 1.17 | 0.99 | 1.26 | multiple-testing check (0.61 < 0.9) |
| funding pair | 1.26 (1.7 y) | n/a | 1.43 (HL) | n/a | multiple-testing check; deployable only at half size |
| blend (hand-picked) | 1.61 | 1.35 | 1.05 | 1.03 | multiple-testing check (0.82) |
| flow (Binance) | n/a | 1.45 / 1.36 | 1.20 | 1.25 | multiple-testing check (0.88) |
| broad momentum | −0.09 / 0.47 | 1.27 / 1.43 | 1.27 | 1.32 | weak on HL |
| trend (tsmom) | 0.18 / 0.53 | 0.79 / 1.22 | 1.08 | 1.23 | pick below 0.8 on Binance |
| listing shorts | 0.89 / 1.20 | 0.81 / 0.64 | 0.81 | 0.85 | grid average below 0.8 on Binance; listing-day fills cost far more than modelled |

**Honest expectation if these edges are real:** blend-type books 12–27% a year with 20–30% drawdowns; the funding pair about 4–5% a year at a deployable size
(≈ $40/yr on $1,000, ≈ $8/yr on $200). No real money before the paper books have tracked their backtests for 2–3 months. That decision is yours.

## Next
Next research session: re-derive the Binance main-book mix from today's clean numbers by the fixed rule (decided in advance, applied a session later). Then T5b Binance
positioning data (≈ 11-29), liquidation prints (≈ 12-01/12-05), the listing-day cost problem, a fill-delay re-measure (≈ 12-09), HL order-flow re-check (≈ 12-23).
blend_nested refit due 2027-01-02. Forward ledger: first verdicts ≈ 12-09.
