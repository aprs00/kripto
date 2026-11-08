# Research backlog (highest priority first)

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

- [ ] T1 Baseline walk-forward of tier-1 strategies (tsmom, xsmom, xsrev, carry, lowvol, funding_contra) on HL+BN — establishes what survives costs
- [ ] T2 New-listing decay: short HL perps N days after listing, hold M days, vol-scaled — airdrop/unlock supply overhang; data: HL 1d candles incl. delisted
- [ ] T3 HL-vs-Binance funding spread as crowding signal — HL retail flow distinct; data: HL funding + Binance funding (hourly HL, 8h BN)
- [ ] T4 Combine survivors: risk-parity blend, check correlation & diversification benefit
- [ ] T5 Positioning: hourly snapshots of OI/premium (collected by trader into data/hl/ctx) — OI-change × price-change regimes (squeeze/flush setups); needs ≥ 4 weeks of snapshots
- [ ] T6 Public top-account positioning (HL leaderboard addresses via public /info clearinghouseState) — do profitable accounts lead? needs collector + weeks of data; rate-limit carefully
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions
- [ ] T8 Regime filter: does trend/carry performance depend on BTC vol regime or funding level? (beware overfitting; ≤ 2 regime params)
- [ ] T9 Execution: maker-style rebalancing (post-only at mid ± tick, fall back to taker) — fee 1.5bp vs 4.5bp; paper sim must model non-fills conservatively
