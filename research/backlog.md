# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

**Priority order after the owner's re-aim (2026-11-09: $1,000 real capital waiting on evidence, steady risk, small-account
edges first; research is Tue + Thu, ≤ 6 new walk-forward experiments per session):**
1. **T9 maker execution** (three HL signals are now positive before costs and dead after them: the lever is cost, not signal;
library: gueant-2016 part on limit-order placement, maxdama §7) → 2. H4 (is the blend real once its components are chosen
out-of-sample? one experiment) → 3. T0a (does live track the backtest? ≈ 11-16) → 4. T2b a (funding on listing shorts; the nightly
job now backfills 8 more coins a night) → 5. X1b (funding capture with hold-until-flip, only after T9) → 6. T5b → the rest.
Evidence that accrues with time (forward ledger, tracking, T6b data) outranks another backtest on the same history.

- [ ] H4 **Blend with component SELECTION nested, at weight level** (review 11-09: return-level nested 0.62–1.24 vs 1.36 hindsight).
  Pre-register ONE rule before looking (suggest: top-3 by expanding in-sample Sharpe among ALL registered HL-testable strategies,
  re-chosen every 60 days, equal risk). This replaces T4b. If HL OOS stays > 0.8 and `worst` > 0, the blend's only failing
  clause is DSR, and the forward ledger + T0a become its evidence stream. Run on hl 1d + bnall.
- [ ] X1b **Funding capture, second angle (only after T9)**: X1 showed the funding difference is real (+6–13%/yr at gross ≤ 2) and
  that spread-following weights churn it away (70–410× turnover). Pre-register ONE rule: enter when the 14-day spread > 20%/yr,
  hold until it changes sign, top-20 liquid pairs, passive fills where T9 allows. Then a two-venue paper book if it passes.
- [x] X1 → DEAD at taker costs, funding leg real (2026-11-09, findings). Was: **Cross-venue funding capture (small-account edge, new)**: same coin long on the venue with lower funding, short on the
  other, when the spread is wide and persistent. Price risk hedged; pays the funding difference minus two sets of costs.
  Needs: HL + Binance funding history joined per coin (both on disk), a two-venue book in the paper engine (today a book
  lives on one venue), and a persistence test of the spread first (cheap kill test: is the 7-day mean spread > round-trip
  costs often enough?). Do the kill test before building anything.
- [ ] ~~T4b~~ (superseded by H4) **Nested blend re-test (removes component-selection bias)**: the T4 blend (HL OOS 1.57) used component params I
  picked after seeing their results. Re-test with each component's params chosen by its OWN walk-forward on past data only,
  same equal-risk rule. Pre-register 1 config, HL 1d + bnall. Also report (descriptive, not a new grid) bnall blend without
  listing_short (band/survivorship artifact there), and the blend on 4h HL (2024-06+). If HL stays > 0.8, the bnall DSR
  clause is the only failure, and the blend's live shadow book + T0a tracking becomes the main evidence stream.
- [x] T12 obsolete since the main book is $1,000 (band 0.01: the ~16-name blend is executable). Was: **$200 executability of the blend**: it holds ~16 names (many ≈ 5%). Design a capped version (≤ 10 names, each
  ≥ 6%) and measure the Sharpe cost vs the full blend at band 0.05. Needed before any main-book allocation.
- [x] B1 Binance paper venue BUILT 2026-11-09 (interactive): shadow books xsmom_k@bn, flow@bn, tsmom@bn; main_bn $200. Follow-ups:
  (1) after 7 days, add these books to the T0a tracking check; (2) blend@bn; (3) Binance funding in the live panel if a
  funding strategy moves to bn. Original spec: Spec: `kripto/bn.py` public fapi client
  (≤ 1 req/s, retries, no keys); live panel = 4h/1d klines (keep taker buy quote volume) + funding (premiumIndex/fundingRate)
  for the point-in-time liquid universe; fills simulated by walking the live `/fapi/v1/depth` book + 5 bp taker fee; 8h
  funding accrual; min notional/step size from exchangeInfo. Books get a `venue` field (config/strategies.json `venue`:
  "hl"|"bn"; default hl); `main_bn` $200 book next to `main`. Tests: known-answer fill/funding/min-notional tests and an
  offline mocked trader run. Then shadow books on Binance for the strongest Binance-evidenced candidates:
  xsmom_k (bnall 1.37), flow lb14 (bnall 1.13), blend. Watch the hourly run time (HL already ~7.5 min) and keep total < ~20 min.
- [ ] T0a **Live-vs-backtest replay (tracking check)**: for each shadow book, re-run the backtest over exactly the live period
  and compare day by day: positions, turnover, costs/slippage (model vs live order book), funding, returns. Build
  scripts/live_vs_backtest.py once books have ≥ 7 days (≈ 2026-11-16). Large tracking error = bug or bad cost model.
- [ ] T5b **Positioning hypotheses NOW on Binance history** (added 2026-11-09, owner wants results fast; don't wait months
  for HL collection). data.binance.vision publishes per-symbol daily `metrics` files (5-min open interest, top-trader
  long/short account + position ratios, taker buy/sell volume ratio) going back years, for the whole bnall universe.
  Test the T5/T6 ideas there first (OI change × price change regimes; crowded top-trader positioning as a contrarian or
  confirming signal), pre-registered ≤ 8 configs each. HL collection (T6a) then confirms that the effect carries over to HL.
- [ ] L2b **flow follow-ups** ((a) DONE 2026-11-09: sign transfers to HL prices, dead at HL taker costs; (b) live Binance feed exists: flow@bn; (c) open). Was: (a) cross-venue test: Binance taker-flow
  signal → trade the same coins on HL prices (HL 1d/4h panel joined with bnall taker_buy on common coins), the only
  way to get HL evidence for the gate; (b) a live signal source: Binance public futures klines (fapi `/klines` includes
  taker buy quote volume, public market data, polite rate) OR HL recentTrades aggregation (collector already sees trades);
  only then a shadow book; (c) blend candidate: flow + xsmom_k (corr 0.43) + tsmom + listing_short, pre-registered.
  Also: inspect_strategy printed its WARN line although corr BTC 0.11 and BTC leg −1% < other legs 23%, so check the WARN condition.
- [ ] L2 **Taker-flow signals (library N1/N2)**: first extend the Binance kline loaders to keep taker buy volume (cols 9–10,
  currently dropped by `.iloc[:, :8]`/`cols`). Re-download is incremental-unfriendly → plan it within the nightly window.
  Then one pre-registered batch on bnall: (a) k-day net-taker-flow rank → next-k return, both signs, beta-hedged;
  (b) flow-without-price-progress (absorption) reversal. ≤ 8 configs each. Mechanism: metaorder splitting (Tóth et al.).
- [x] L4 Residual reversion with entry threshold → DEAD (2026-11-09, price-only SR −0.72; residuals continue)
- [ ] ~~L4~~ **Residual reversion with entry threshold (library N5, Pole)**: NEW angle vs dead xsrev: BTC-beta-defactored
  residuals, enter only past a z-threshold, exit on reversion, so turnover is a fraction of xsrev's. HL + bnall, ≤ 8 configs.
- [ ] L1 **HL lags Binance? (library N4)**: cheap kill test: BN 1h alt return → HL same-coin next-1h return. Expect
  ≈ 0 (arbitraged in seconds). If |IC| is meaningful after costs, it becomes a strategy.
- [ ] L6 **Better vol forecasts for sizing (library N6)**: vol estimator ∈ {close-to-close, Parkinson, HAR-range} inside
  tsmom/xsmom vol targeting. Risk improvement, not alpha. One experiment per strategy.
- [ ] L3 **Square-root impact sanity check of the slippage model (library N3)**: do this with T0a once there are live fills.
- [ ] L5 Value-area rejection (library N7, Dalton/AMT): low prior, after the above.
- [ ] T2b **listing_short follow-ups** (pre-register ≤ 8 configs each):
  (a) HL funding coverage: backfill funding for every coin ever shorted (currently 28% of short exposure) and re-measure;
  (b) per-listing event study (cumulative abnormal return vs BTC by days since listing, HL + bnall) to see the decay shape,
  not just a portfolio Sharpe; (c) sizing: vol_target under-estimates new-coin vol (pre-listing returns = 0) → use a
  per-name vol floor. Capacity at $200: ~6 concurrent shorts at gross 0.5 ≈ $16 each, which is executable.
- [ ] T13 **New low-correlation sleeves for the blend** (from T4: diversification is the lever). Judge any new idea partly by
  its correlation to the blend. Ideas: T3 HL-vs-BN funding spread; T2b event-driven shorts (token unlocks need external data);
  intraday seasonality of HL funding settlement. Each must still pass alone on its own merits (no blend-weight search).
- [ ] T10 **Re-run survivor-sensitive BN verdicts on bnall** (daily): carry, lowvol, xsrev still only on BN-82. bnall needs a
  monthly refresh: add `data.bn_download_all_daily()` to scripts/download.py (incremental, ~20 min first run).
- [ ] T6b Positioning-data analysis (collector live since 2026-11-09 17:40; needs ≥ 4 weeks ≈ 2026-12-07): top-account net
  positioning vs next-day returns; L2 imbalance vs next-hour returns; OI-change × price-change regimes (old T5/T6).
  Watch the `collector:` line of `paper status` at every review (a gap = data lost forever).
- [ ] T0b Scheduled re-checks of HL-only DEAD ideas (carry, carry_trend) once HL has ≥ 6 more months (~2027-05). Low priority:
  this is a re-check of dead ideas, not the main path. New ideas get evidence now from bnall/BN history.
- [ ] T9 Execution: maker-style rebalancing (post-only at mid ± tick, fall back to taker): fee 1.5bp vs 4.5bp. xsmom_k pays
  ~10%/yr and tsmom ~4–5%/yr in HL costs. Paper sim must model non-fills conservatively.
- [ ] T3 HL-vs-Binance funding spread as a crowding signal (HL retail flow is distinct; HL hourly vs BN 8h funding).
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions (positions data now collected, T6b).
- [ ] T8 Regime filter: trend/carry vs BTC vol regime or funding level (≤ 2 regime params; beware overfitting).

## Done
- [x] H1 Harness: staggered tranches instead of one start day (`strategies.scheduled`, research + live) → DONE 2026-11-09;
  candidates re-measured (batches 2026-11-09-h1-recheck-*, findings v2).
- [x] H2 Robustness block stored with every walk-forward (`research.robustness`, gate reads `robust.worst`) → DONE 2026-11-09.
- [x] H3 Forward ledger (`scripts/forward_score.py` → research/forward.json; Sunday retro runs it) → DONE 2026-11-09.
- [x] T4 Blend of candidates (1 pre-registered rule) → HL OOS 1.57, bnall 1.02, DSR 0.62: fails only the DSR clause; candidate + shadow (2026-11-09 pm)
- [x] T11 xsmom_k (top/bottom-k, $200-executable) → HL 0.55, bnall 1.37; candidate + shadow (2026-11-09 pm)
- [x] T6a Non-backfillable HL collector (kripto/collect.py: top-account positions via recentTrades→clearinghouseState, L2 top-10; ≤ ~56 calls/h) live 2026-11-09 17:40
- [x] T0 Re-run all 2026-11-08 grids with fixed code → same verdicts; numbers close to the invalid ones (journal/2026-11-09.md)
- [x] T1 Baseline tier-1 walk-forward → tsmom/xsmom candidates; xsrev/lowvol/funding_contra dead (re-confirmed 11-09)
- [x] T1b HL carry → DEAD on HL (−0.89 re-run)
- [x] T1c tsmom cost reduction: signal smoothing DEAD (lag > cost savings); $20M liquidity floor marginal (2026-11-09)
- [x] T1d carry_trend → DEAD on HL (0/6 >0) (2026-11-09)
- [x] T2 listing_short → HL OOS 0.75, 9/9 grid >0; candidate + shadow book; BN-82 −0.18 (survivor-biased) (2026-11-09)
