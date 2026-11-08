# Findings ledger

One entry per hypothesis ever tested. Read this before choosing research. Keep each entry ≤ 5 lines.
Verdicts: **ALIVE** (candidate/incubation/active) · **DEAD** (rejected; revisit only with a new angle stated) ·
**OPEN** (inconclusive or blocked on data).
Numbers are walk-forward out-of-sample, net of fees + slippage + funding unless noted. SR = annualised Sharpe.

## Cross-cutting lessons (apply to everything)
* **Costs are the binding constraint on Hyperliquid.** The HL top-20 by volume includes thin memes; slippage +
  fees took ~8%/yr off trend. Any HL strategy must be judged at HL cost levels, not Binance's.
* **$200 + $10 min order ⇒ any position < 5% of equity can't be opened.** Diversified (20–30 name) books can't
  be executed in the main book. Backtests use band 0.05 to mirror this.
* **Binance results do NOT transfer automatically to HL** (see carry). Every idea must pass on HL data.
* BN dataset has mild survivorship bias (hand-picked list of 82 coins); HL dataset includes delisted perps.
* **Statistical power is low; know the error bars.** SE(annual Sharpe) ≈ √((1 + SR²/2) / years). HL walk-forward OOS ≈
  1.6 years ⇒ ±0.8; BN ≈ 6 years ⇒ ±0.4; 3 weeks live ⇒ ±4. So: a single HL number is weak evidence either way; demand
  consistency (per-year signs, grid breadth, BN agreement, an economic mechanism) before concluding. Live paper P&L
  proves nothing about edge for many months. Its job is checking that live behaves like the backtest
  (fills, costs, bugs).
* **DEAD on HL ≠ dead forever.** HL history grows every day. Re-test DEAD ideas that died on HL alone (not on BN
  too) once HL OOS history has grown by ≥ 6 months, as a pre-registered re-check (see backlog T0b).

## Hypotheses

### tsmom: multi-horizon time-series trend, L/S, vol-targeted (2026-11-08) → ALIVE (candidate)
BN 2020–26: OOS SR 1.26, positive every year, corr BTC 0.01, 2×cost SR 1.03. HL: OOS SR 0.55, grid median 0.69
(12/12 >0); price-only SR 1.22 but costs 8.3%/yr. Concentrated (top 8/12): HL OOS 0.51, grid median 0.89 (16/16 >0).
Fails HL gate (needs OOS > 0.8). Signal real; cost/size problem. Shadow book live from 2026-11-09.

### tsmom long-only (2026-11-08) → DEAD
2022 −33%, 2025 −11%: it is BTC beta, not an edge.

### xsmom: cross-sectional momentum, beta-hedged (2026-11-08) → ALIVE (candidate)
BN OOS SR 0.63 (grid median 0.52), HL 0.71 (0.63). Weak but consistent. Shadow book live.

### carry: short high funding / long low funding, dollar+beta neutral (2026-11-08) → DEAD on HL (≈1 SE; re-check ~2027-05)
BN OOS SR 1.35 (funding +15%/yr, price leg SR +1.0, every year >0). **HL OOS SR −0.58**, grid median −0.68 (3/12 >0):
funding +6.5%/yr but price leg SR −0.66, every year negative. On HL, high-funding names are momentum squeezes
that keep rising. Concentrated variant on BN also collapses (0.45): carry needs breadth. Follow-up idea: T1d.

### xsrev: short-term cross-sectional reversal (2026-11-08) → DEAD
BN OOS SR −1.57, grid median −1.79 (0/6 >0). Turnover makes fees dominate.

### lowvol: betting against volatility, beta-hedged (2026-11-08) → DEAD
BN OOS SR −0.02, grid median −0.30 (1/6 >0).

### funding_contra: fade funding spikes vs own history (2026-11-08) → DEAD
BN OOS SR −0.38, grid median 0.09. Not robust.
