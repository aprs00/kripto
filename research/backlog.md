# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

- [ ] T0a **Live-vs-backtest replay (tracking check)**: for each shadow book, re-run the backtest over exactly the live period
  and compare day by day: positions, turnover, costs/slippage (model vs live order book), funding, returns. Build
  scripts/live_vs_backtest.py once books have ≥ 7 days (≈ 2026-11-16). Large tracking error = bug or bad cost model.
- [ ] T6a **Start collecting non-backfillable HL data now** (time-critical; every day not collected is lost forever, and
  Tier 2 in design.md is our most distinctive edge source). Already collected: hourly asset ctx (OI/funding/premium).
  Missing: (1) public account positioning: discover active addresses from `/info` `recentTrades` (`users` field) and
  snapshot `clearinghouseState` for a rotating set of the largest ~50 accounts per hour; (2) L2 depth snapshots that
  the trader already fetches for fills (store top-N levels per coin, nearly free). Budget: stay well inside the
  shared 3 s rate limit (trader already uses ~7.5 min/h, so ≤ ~60 extra calls/h). /info only (HARD RULE 1).
  Build it as a small module with tests and append to the hourly run. T5/T6/T7 depend on it.
- [ ] T5b **Positioning hypotheses NOW on Binance history** (added 2026-11-09, owner wants results fast; don't wait months
  for HL collection). data.binance.vision publishes per-symbol daily `metrics` files (5-min open interest, top-trader
  long/short account + position ratios, taker buy/sell volume ratio) going back years, for the whole bnall universe.
  Test the T5/T6 ideas there first (OI change × price change regimes; crowded top-trader positioning as a contrarian or
  confirming signal), pre-registered ≤ 8 configs each. HL collection (T6a) then confirms that the effect carries over to HL.
- [ ] T4 **Blend of the candidates (tsmom + xsmom-small + listing_short)**, moved up 2026-11-09. Each one alone fails the
  HL gate, but their correlation should be low (trend vs x-section vs short-alt), so a risk-parity blend is the most
  plausible path to the first incubation. Pre-register ONE blend rule (e.g. equal risk, monthly) and run it as a
  single walk-forward experiment on HL + bnall; don't search over blend weights.
- [ ] T2b **listing_short follow-ups** (only after bnall verdict; pre-register ≤ 8 configs each):
  (a) HL funding coverage: backfill funding for every coin ever shorted (currently 28% of short exposure) and re-measure;
  (b) per-listing event study (cumulative abnormal return vs BTC by days since listing, HL + bnall) to see the decay shape,
  not just a portfolio Sharpe; (c) sizing: vol_target under-estimates new-coin vol (pre-listing returns = 0) → use a
  per-name vol floor. Capacity at $200: ~6 concurrent shorts at gross 0.5 ≈ $16 each, which is executable.
- [ ] T10 **Re-run survivor-sensitive BN verdicts on bnall** (daily): tsmom/xsmom/listing_short done 2026-11-09; carry,
  lowvol, xsrev still only on BN-82. bnall needs a monthly refresh: add `data.bn_download_all_daily()` to scripts/download.py
  (incremental, ~20 min first run, a few min after; the monthly archive only updates once a month).
- [ ] T11 **Small-account construction for xsmom** (bnall 1.27 but needs breadth; band 0.05 halves it): test top/bottom-k only
  (k = 3–5 each side, ≥ 5% weights) on HL + bnall; pre-register ≤ 8 configs. The $200 main book can only hold ~10 positions.
- [ ] T0b Scheduled re-checks of HL-only DEAD ideas (carry, carry_trend) once HL has ≥ 6 more months (~2027-05). Low priority:
  this is a re-check of dead ideas, not the main path. New ideas get evidence now from bnall/BN history.
- [ ] T9 Execution: maker-style rebalancing (post-only at mid ± tick, fall back to taker): fee 1.5bp vs 4.5bp. tsmom pays
  ~4–5%/yr in costs on HL, about half its gross edge. Paper sim must model non-fills conservatively.
- [ ] T3 HL-vs-Binance funding spread as a crowding signal (HL retail flow is distinct; HL hourly vs BN 8h funding).
- [ ] T5 Positioning: hourly OI/premium snapshots (data/hl/ctx, collecting since 2026-11-08): OI-change × price-change regimes; needs ≥ 4 weeks.
- [ ] T6 Public top-account positioning (HL leaderboard addresses via public /info clearinghouseState); needs collector + weeks.
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions.
- [ ] T8 Regime filter: trend/carry vs BTC vol regime or funding level (≤ 2 regime params; beware overfitting).

## Done
- [x] T0 Re-run all 2026-11-08 grids with fixed code → same verdicts; numbers close to the invalid ones (journal/2026-11-09.md)
- [x] T1 Baseline tier-1 walk-forward → tsmom/xsmom candidates; xsrev/lowvol/funding_contra dead (re-confirmed 11-09)
- [x] T1b HL carry → DEAD on HL (−0.89 re-run)
- [x] T1c tsmom cost reduction: signal smoothing DEAD (lag > cost savings); $20M liquidity floor marginal (2026-11-09)
- [x] T1d carry_trend → DEAD on HL (0/6 >0) (2026-11-09)
- [x] T2 listing_short → HL OOS 0.75, 9/9 grid >0; candidate + shadow book; BN-82 −0.18 (survivor-biased) (2026-11-09)
