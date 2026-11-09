# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

- [ ] T0 **RE-RUN EVERYTHING (do first, 2026-11-09 research session)**: all 2026-11-08 backtests are invalid (rebalance-grid unit bug,
  see findings.md warning). Re-run the same pre-registered grids (tsmom, xsmom, carry, xsrev, lowvol, funding_contra; hl+bn,
  plus the concentrated tsmom/carry variants) with the fixed code, then re-decide every verdict and lifecycle status (carry
  retirement included). Don't change grids: same configs, so it's a re-measurement, not a fishing trip.
- [ ] T0a **Live-vs-backtest replay (tracking check)**: for each shadow book, re-run the backtest over exactly the live period
  and compare day by day: positions, turnover, costs/slippage (model vs live order book), funding, returns. This is what
  live paper can actually verify (weeks), whereas edge needs months. Build as scripts/live_vs_backtest.py and run it in
  every research session once books have ≥ 7 days. Large tracking error = bug or bad cost model ⇒ fix before trusting anything.
- [ ] T0b Scheduled re-checks: ~2027-05 re-run HL walk-forward for HL-only DEAD ideas (carry) with 6 more months of data.
- [x] T1 Baseline walk-forward of tier-1 strategies on HL+BN → tsmom/xsmom/carry candidates (shadow), xsrev/lowvol/funding_contra dead; HL carry pending funding data (journal/2026-11-08.md)
- [x] T1b HL carry walk-forward → FAILS on HL (OOS SR −0.58; price leg −0.66 overwhelms +6.5%/yr funding); retired (41/60 top coins had funding history)
- [ ] T1d Trend-conditioned carry: earn funding only where it agrees with trend sign (short high-funding names only in downtrends, etc.) — rationale: HL high funding = squeeze momentum; pre-register ≤ 8 configs
- [ ] T1c HL cost reduction: liquidity-filtered universe, signal smoothing, fewer/larger positions for $200 (min order $10)
- [ ] T2 New-listing decay: short HL perps N days after listing, hold M days, vol-scaled — airdrop/unlock supply overhang; data: HL 1d candles incl. delisted
- [ ] T3 HL-vs-Binance funding spread as crowding signal — HL retail flow distinct; data: HL funding + Binance funding (hourly HL, 8h BN)
- [ ] T4 Combine survivors: risk-parity blend, check correlation & diversification benefit
- [ ] T5 Positioning: hourly snapshots of OI/premium (collected by trader into data/hl/ctx) — OI-change × price-change regimes (squeeze/flush setups); needs ≥ 4 weeks of snapshots
- [ ] T6 Public top-account positioning (HL leaderboard addresses via public /info clearinghouseState) — do profitable accounts lead? needs collector + weeks of data; rate-limit carefully
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions
- [ ] T8 Regime filter: does trend/carry performance depend on BTC vol regime or funding level? (beware overfitting; ≤ 2 regime params)
- [ ] T9 Execution: maker-style rebalancing (post-only at mid ± tick, fall back to taker) — fee 1.5bp vs 4.5bp; paper sim must model non-fills conservatively
