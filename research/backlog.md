# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

**Priority order (rewritten 2026-11-10 after H4/T9/X1b; research Tue + Thu, ≤ 6 new walk-forward experiments per session):**
## Owner instruction 2026-11-10 ("run everything now"): DONE 2026-11-12 06:40 research (M1, X2, W1 live; forward baseline). Journal 2026-11-12.
**Next priorities (2026-11-12):** 1. T0a tracking (≈ 11-16, all books incl. main + pair) → 2. (X1d done: fspread deployable at gross 1.0) → 3. C1 cost calibration (from 11-24) → 4. W1 data analysis once ≥ 2 weeks (HL taker flow
vs next-day returns, same rule as flow@bn, ≈ 11-26) → 5. T2b (a)/(c) + longer hold (b showed decay continues to day 120) → 6. T5b.
- [x] M1 DONE 2026-11-12: HL main = blend_nested 1.0; main_bn = flow@bn/xsmom@bn/blend@bn 1/3 each. Was: **M1 main books trade the best estimate** (was planned for Thu 11-12; brought forward by the instruction above) (design.md 2026-11-10, owner mandate): apply the fixed rule
(equal-risk mix of the venue's candidates with WF OOS > 0.8 on that venue and `robust.worst` > 0) to set `incubation` + alloc for
`main` (HL) and `main_bn`; expected today: HL = blend_nested (it already is the rule-based mix; do not double-count blend), Binance =
flow@bn + xsmom@bn + blend@bn. Their `small:` twins follow automatically. State in STATUS.md that this is the paper best estimate,
not a funding recommendation. Then X2.
- [x] W1 DONE 2026-11-12: kripto-flow.service, data/hl/flow, side verified vs bbo, gaps.jsonl, watchdog heartbeat. Was: **W1 Hyperliquid trade-flow collector over the public websocket** (allowed since 2026-11-10): one connection, `trades` for the top
~60 coins, aggregated per coin per minute (taker buy / sell notional, trade count) into data/hl/flow/YYYY-MM-DD.parquet; verify
the taker-side field empirically against the book before trusting it; watchdog check for gaps. Non-backfillable, so build it this
week. Purpose: flow natively on HL (today only Binance flow exists; it transfers to HL prices before costs).
0. **C1 cost-model calibration** (assumptions.md row 1): live fills cost 5.4 bp on HL vs 9.6 bp modelled (2 days). From 2026-11-24
(≥ 14 days of fills, must include a volatile day): fit slippage vs order size / volume from the fills table (and the stored L2
snapshots), write scripts/cost_calibration.py, change `backtest.slippage_model` with a design.md entry in a session that promotes
nothing, then re-measure every "dead at taker costs" verdict and the decision-frequency study. Until then quote the ×0.56
sensitivity only as a labelled side number.
1. **X2 two-venue paper book for fspread_hold** (the cleanest candidate: market-neutral, small-account edge, +7–10%/yr funding at
mdd < 2%; live evidence starts only once it trades) → 2. T0a live-vs-backtest tracking (≈ 11-16) → 3. T2b a/b listing_short
(lead leg of both blends; funding coverage) → 4. X1c fspread_hold robustness (BN-funding-interval, basis blowups, more coins as HL
funding backfill grows) → 5. T5b → the rest. T9 (maker) is closed: turnover, not fee type, is the cost lever (findings).
Evidence that accrues with time (forward ledger, tracking, T6b data) outranks another backtest on the same history.

- [x] X2 DONE 2026-11-12 (kripto/venue_pair.py; 8 pairs opened). Was: **Two-venue paper book (`venue: "pair"`) for fspread_hold@pair.** Design (2026-11-10): new module kripto/venue_pair.py,
  called from paper.run_once after Binance inside try/except (a failure never touches HL/BN books). Book `shadow:fspread_hold@pair`,
  positions keyed `<COIN>@hl` / `<COIN>@bn`; `book_venue` → "pair" so the HL/BN funding/marks code skips it. Signal needs a fresh
  14-day funding history on BOTH venues for ~100 coins: HL from data/hl/funding (nightly; check freshness) + BN via one
  `premiumIndex` call (all symbols, weight 10) stored hourly as a small collector (lastFundingRate at each funding time), with
  data/bn/funding_all as the backfill. Fills: HL legs via paper.simulate_fill, BN legs via venue_bn's depth walk. Funding accrual:
  HL fundingHistory per held coin (≤ 10 coins, 3 s each), BN from the stored premiumIndex prints. Rebalance once a day.
  Tests: fake clients, known-answer funding accrual on a held pair, and HL/BN books unaffected. Report margin per venue (≈ 2×).
- [x] X1d DONE 2026-11-12 → deployable gross 1.0 (2.0 liquidated on 2025-10-10); findings. Was: **Per-venue account simulation for fspread_hold** (from X1c: one-account mdd −1.7% hides −37%/day per venue account at
  gross 2): simulate two accounts with daily collateral re-split, HL/BN maintenance margin and intraday highs (HL 1d high/low),
  gross ∈ {0.5, 1.0, 2.0} pre-registered; output P(liquidation) and return per gross. Descriptive; decides the deployable size.
- [ ] W2 **Visible metaorders on HL (library N10, Tóth et al.)**: from ≈ 11-26 (2 weeks of W1 `big` data): persistent same-side net
  taking by one address → next 4h/24h return, per coin, volume-scaled; descriptive IC first (kill: |IC| < 0.02 or below costs), then a
  pre-registered ≤ 6-config walk-forward only if it survives. Also plain HL taker-flow imbalance (flow@bn's rule) on HL prices.
- [ ] P2 **InSilico second pass** (owner 2026-11-12: the first pass tested one literal form per rule). Interactive, on the laptop (the
  chat archive is only there): `prompts/insilico_pass2.md`. Think-through per rule, ≥ 3 formulations, explore on 2021–23 / 10 coins,
  confirm on 2024–26 / unseen coins; profile rules R14–R17 (the author's main topic) were never tested. Server sessions may take the
  parts that need no archive (R23 timing tilt = E2, R28, signals as filters for the existing books).
- [ ] A1 **Dead-list audit** (design.md §4 2026-11-12): Sunday retro, two DEAD entries a week, oldest first: xsrev, lowvol,
  funding_contra, tsmom long-only, carry (HL), carry_trend, resrev, T9 maker execution, L1 hourly lead-lag, minute-bar event study.
  Relabel to OPEN (one form failed) where fewer than three formulations were tested or no reason is diagnosed; list untried forms here.
- [ ] E1 **lshock (liquidation fade) follow-ups** (findings: OPEN, tail-event; the only InSilico rule not dead). In this order:
  (a) LIVE evidence: a 1-minute event shadow book (Binance 30 coins; later HL from kripto/flow.py minute bars) run by the always-on
  watcher, frozen config z=6, m=5, e=1.0, long, $500 per trade, ≤ 2 open. Fills and venue behaviour on cascade days are the open question
  and only live paper can show them (≈ 130 trades/yr, 2–4 cascade days/yr: slow evidence, so start early). (b) ONE pre-registered test of
  "cascade days only" (≥ 5 of the 30 coins trigger within 30 min) on the NEXT 50 unseen Binance coins; it was seen in the data, so only
  unseen coins count. (c) Pessimistic fills: taker slippage 30–50 bp and no fills in the first minute of a cascade. No book before (a)+(c).
- [ ] E2 **Execution-time tilt** (calendar finding 11-11: BTC/ETH drift +5–9 bp in the hour CME is shut, 17–18 New York, both eras, t 2.3–3.6).
  Not a book (below costs). Descriptive check first: would moving the daily books' BUYS before 17:00 NY and SELLS after 18:00 NY have saved
  cost over the live fills so far and over 6 y of hourly bars? research/studies/. A cost saving is worth as much as a signal.
- [ ] TSZ-HL Trade-size buckets on Hyperliquid (kripto/flow.py `tsz`, per taker address, since 2026-11-12; non-backfillable). After ≥ 8
  weeks (≈ 2027-01-07): R1/R2 event study natively on HL, where one address = one order. Low prior after the Binance result; the data is
  also the input for W2 (large takers). Check at every review that `tsz` is non-empty.
- [ ] R28 Unit-price factor (insilico_rules.md R28): cross-sectional, long the lowest-unit-price coins, bnall 1d, ≤ 6 configs. Cheap, low prior.
- [ ] LQ1 Binance liquidation prints: public websocket `!forceOrder@arr` (read-only, HARD RULE 1 allows it) → data/bn/liq, same pattern as
  kripto/flow.py. Needed to tell a liquidation cascade from an ordinary dump (E1b, T7, insilico R12). Non-backfillable.
- [ ] R3/R7 Range ("rotation") bars with trade count and size-bucket delta: second aggTrades pass (scripts/aggtrades.py keeps 5-min bars
  only). Low prior now that R1 and R4 are dead on time bars; do only together with LQ1 or if TSZ-HL shows something.
- [ ] X1c fspread_hold robustness (descriptive, no new WF unless a new rule): per-pair basis excursions (worst daily |basis|),
  funding-interval mix on BN (1h/4h/8h coins), and a re-run when HL funding backfill reaches all coins (pair has 84 → more).
- [ ] blend@bn → nested choice? H4 on bnall picks carry+carry_trend+xsmom (1.16), not the hindsight trio (1.30). Needs Binance
  funding in the live BN panel (carry). Do with X2's BN funding collector.
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
- [ ] ~~L4~~ **Residual reversion with entry threshold (library N5, Pole)**: NEW angle vs dead xsrev: BTC-beta-defactored
  residuals, enter only past a z-threshold, exit on reversion, so turnover is a fraction of xsrev's. HL + bnall, ≤ 8 configs.
- [ ] T9b Alpha-decay curve per strategy (library N8, maxdama §7): signed return of each strategy's trades from decision to +1/4/12/24 h.
  Explains T9 and sizes the cost of a late run (one bar late costs tsmom a third). Descriptive, hourly data.
- [x] L1 → DEAD at taker costs: hourly effects are real (t ≈ 8) but 2–5 bp vs 25–40 bp costs (2026-11-10, findings). Was: **HL lags Binance? (library N4)**: cheap kill test: BN 1h alt return → HL same-coin next-1h return. Expect
  ≈ 0 (arbitraged in seconds). If |IC| is meaningful after costs, it becomes a strategy.
- [ ] L6 **Better vol forecasts for sizing (library N6)**: vol estimator ∈ {close-to-close, Parkinson, HAR-range} inside
  tsmom/xsmom vol targeting. Risk improvement, not alpha. One experiment per strategy.
- [ ] L3 **Square-root impact sanity check of the slippage model (library N3)**: do this with T0a once there are live fills.
- [ ] L5 Value-area rejection (library N7, Dalton/AMT): low prior, after the above.
- [ ] T2b **listing_short follow-ups** (pre-register ≤ 8 configs each). (b) DONE 2026-11-12 (event study: linear decay to d120 on both
  venues → new (d): hold 90/120 d pre-registered, judged on bnall where 800 events exist):
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
- [ ] T3 HL-vs-Binance funding spread as a crowding signal (HL retail flow is distinct; HL hourly vs BN 8h funding).
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions (positions data now collected, T6b).
- [ ] T8 Regime filter: trend/carry vs BTC vol regime or funding level (≤ 2 regime params; beware overfitting).

## Done
- [x] InSilico batch (2026-11-11/12, research/insilico_rules.md): weekend_revert DEAD, range_retest DEAD before costs, mousetrap DEAD before
  costs, tsize_capit DEAD (2021 only), lshock OPEN (replicated per trade on 20 unseen coins, 3 crash days = 72% of P&L) → E1.
- [x] H4 → blend_nested HL OOS 1.87, bnall 1.16 (DSR 0.63): blend is not hindsight; candidate + shadow (2026-11-10).
- [x] X1b → fspread_hold pair OOS 1.26, grid med 2.22, worst 1.43; candidate, needs X2 (2026-11-10).
- [x] X1 → DEAD at taker costs, funding leg real (2026-11-09, findings).
- [x] ~~T4b~~ (superseded by H4, done 2026-11-10) **Nested blend re-test (removes component-selection bias)**: the T4 blend (HL OOS 1.57) used component params I
- [x] T12 obsolete since the main book is $1,000 (band 0.01: the ~16-name blend is executable).
- [x] B1 Binance paper venue BUILT 2026-11-09 (interactive): shadow books xsmom_k@bn, flow@bn, tsmom@bn; main_bn (now $1,000). Follow-ups live in T0a (tracking) and the blend@bn item (Binance funding).
- [x] L4 Residual reversion with entry threshold → DEAD (2026-11-09, price-only SR −0.72; residuals continue)
- [x] T9 → DEAD as a general fix (2026-11-10): post-only cuts fees ~70% but alpha loss/adverse selection give it back on BN 6y; taker fallback is worse.
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
