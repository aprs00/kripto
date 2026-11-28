# Backlog: done and superseded items (archive; append, newest last)

Moved out of research/backlog.md on 2026-11-26 so the open list fits in one read. Results are in research/findings.md.

**Priority order (rewritten 2026-11-10 after H4/T9/X1b; research Tue + Thu, ≤ 6 new walk-forward experiments per session):**
## Owner instruction 2026-11-10 ("run everything now"): DONE 2026-11-12 06:40 research (M1, X2, W1 live; forward baseline). Journal 2026-11-12.
- [x] M1 re-derivation DONE 2026-11-26 → main_bn = flow@bn ½ + blend_nested@bn ½ (the "hindsight-free blend" clause had never been applied on BN); live BN panel carries funding.
- [x] AL2 DONE 2026-11-26 → form a (daily ex-ante) FAIL (costs), form b (monthly multiplier) PASS → design.md entry; apply next session (scripts/main_scale.py --write).
- [x] LD2 DONE 2026-11-26 insilico → OPEN (cap = size effect; skew +0.12 SR on confirm, below +0.2); findings. Was: (from LD1, 2026-11-26) **ladder@bn strict cap of 5 open positions** (beat a size-matched base on explore; truncates only the 6th+ fill of a flush batch) and, since a cap
  bounds the batch, re-derive the per-order size (2.9%, set from the 17-fill batch, E2d) by the same rule. Server only (full top-20 1-min coverage; the PC copy has ~80%); judge against a
  SIZE-MATCHED base, explore ≤ 2023 / confirm 2024+ (LD1's confirm already used once for cap 3: say so). Prior medium. Queued 2026-11-26 as InSilico item LD2 (sessions were idle until 12-05).
- [x] LD1 DONE 2026-11-26 (PC) → skew OPEN (explore only), cap 3 weak PASS (mostly a size effect); findings. Was: (library N13, Guéant §11; 2026-11-26) **ladder@bn inventory skew**: quote deeper when positions are already open (bid = 30σ·(1+λ·n_open)), because fills
  cluster in market-wide flushes; descriptive on the E2 event set, explore ≤ 2023 / confirm 2024+, judged on daily P&L and worst day. Prior low–medium. Belongs in an
  InSilico session's queue if one has room (ladder is their book), else here.
- [x] TF1 DONE 2026-11-25 (findings: all survive, no verdict changes; M1 re-derivation next session). Was: **Re-run the Binance walk-forwards on the clean panel** (no stock perps): the same 11-09 v2 grids for flow, xsmom, xsmom_k, tsmom, listing_short,
  blend, blend_nested on bnall, tagged as a data correction (no new hypotheses, grids unchanged). Report old and clean pick / grid average / worst; then re-derive the
  M1 lists by the fixed rule (grid average > 0.8, pick > 0, worst > 0) in the following session, not the same one. flow@bn (2026: 0.90 → 0.45) is the one at risk.
- [x] LU1 DONE 2026-11-22 (4 recorded bars): live top-30 = 29, 30, 30, 30 of the clean research top-30 → leave live as it is.
- [x] AL1 DONE 2026-11-25 → 1/N is enough (findings). FOLLOW-UP AL2 (next session, with the M1 re-derivation): main_bn's 1/N mix realises 14–18% vol vs the 25–30% steady target; pre-register a mix-level vol scaling (scale = 0.25 / trailing 60-d mix vol, cap max_gross) as a general rule for every main book, design.md entry, applied the session after. Was: (library N12, maxdama §6; 2026-11-25) **How to mix the M1 candidates in main_bn**: nested 60-d refits on bnall component returns: 1/N vs inverse-vol vs
  min-variance shrunk 50% to diagonal (daily, and 4h for more points); then empirical Kelly of the mix vs the vol target. Descriptive (no new signal), do it in the session
  that re-derives the M1 list (blend overlaps xsmom: the 1/3-each mix double-counts momentum). Prior: 1/N or inverse-vol wins; the value is knowing the overlap.
- [x] PL1 DONE 2026-11-25 → DEAD as entry filter (a/b/c + F1c fail; pumps are momentum's bull-year profit; findings). Untried: intraday stop (R1). Was: **Pump-and-crash tail on the LONG side** (11-22: IDOL, EVAA, AKE −42 to −48% overnight took 4.3% off xsmom@bn): R1 tested filters on shorts only. Think-through first;
  e.g. drop names whose 28-d score is made by ≤ 2 days, or with 7-d volume > 5× the 30-d median. Explore bnall ≤ 2023-06, confirm later, ≤ 3 forms. One night is not evidence.
- [x] FC1 (a)(b) DONE 2026-11-26 (PC) → DEAD as crowding reversal (4 forms); (c) HL−BN gap OPEN: re-explore on the server's HL funding before 2024-07 (if present), confirm 2025-07+ untouched. Was: FC1 funding_contra untried forms (audit 11-22; prior low): (a) only extreme negative funding, long side; (b) conditional on price no longer rising; (c) HL-vs-BN funding
  gap as the crowding measure (= T3). ≤ 6 configs in all.  - [x] LO1 DONE 2026-11-26 (PC, descriptive) → no excess over vol-matched BTC since 2024 (findings). Was: LO1 tsmom long-only untried forms (prior low): excess over vol-matched BTC; BTC-only timing.
- [ ] IS3 **Superseded by the third-pass queue (research/insilico_queue.json, its own 12-h sessions: kripto-insilico.timer). Research sessions: do NOT work on it; W3's walk-forward stays here.** Was: what the second pass planned and did not run (audit 2026-11-22, journal). In order, think-through first, explore ≤ 2023 / confirm later, ≤ 6 WF in all:
  (1) **Range bars** (R3, R7; tg:103–107 "real edge", not even cited in the catalogue): build 0.4% move bars with trade count + size buckets from aggTrades (server can
  rebuild, public archive; raw is dropped, so a second pass; ≤ 2 workers, probe RAM first), BTC/ETH/SOL; R3 exhaustion, R7 ×10 velocity; judge against ≈ 13 bp. Prior low-medium:
  the 5-min version had the opposite sign. (2) lshock L6 pessimistic fills, L3 cascade-only on unseen coins, L4 wait for the end, L2 premium; then E1 (LQ1 ≈ 12-01).
  (3) **Filters for the live books** (never tested): P5 entries at prior POC / inside value, L5 no new shorts after a cascade day, T6 breadth inside `flow`. (4) R14 P4 gap fill; R21 with
  the real "collar" price. (5) low prior: FSVZO / Crayons guides (47 pages, no rule was ever written), R13 perp vs spot delta, R18, R26, R29, R30. Confluence: one fixed pair at most.
**Superseded 2026-11-19 list:**  1. Tue 11-24: W3 walk-forward (pre-register formulations first, see W3) + C1 cost re-fit (≥ 14 days of fills
from 11-24) → 2. W2/W1 HL flow data (≈ 11-26) → 3. T5b positioning on Binance once the metrics backfill is complete (≈ 11-29) → 4. E1 cascade definition
with LQ1 (≥ 2 weeks, ≈ 12-01) → 5. T2b (a)/(c)/(d), and the T2b(e) re-run after C1 → 6. T6b HL positioning (≈ 12-07). Weekly: T0a in the retro.
**Older (2026-11-17 research):** 1. Thu 11-19: re-derive the M1 paper best-estimate lists under WF1 (grid average, pick > 0) by the fixed
rule, and FF1(a) walk-forward on bn100 (data download unit kripto-bn100-dl started 11-17; measure RAM of one evaluate first, `--workers 1`) →
2. C1 cost calibration from 11-24 with N11 (spread ∝ σ/√N) → 3. W2/W1 HL flow data (≈ 11-26) → 4. E1 cascade definition with LQ1 data (≥ 2 weeks)
→ 5. T2b (a)/(c)/(d) → 6. T5b (data job first). Weekly: `scripts.live_vs_backtest` (T0a) in the Sunday retro.
- [x] WF1 DONE 2026-11-17: design.md entry (gate = min(pick, grid avg); M1 list = grid avg with pick > 0; from 11-19). Was: (2026-11-15 retro, assumptions row 9) **Walk-forward selection rule.** research/studies/wf_selection.py: the equal-weight grid average beat
  the in-sample pick in 6/9 pairs (mean OOS SR 0.95 vs 0.78). `oos_grid_avg` is now in every result. Decide in a research session, with a
  design.md entry whose rationale is general: report both; the gate reads min(pick, grid avg) where the grid is one hypothesis (no mixed signs);
  consider trading the grid average (or top-3) in shadow books. Must not promote anything in the session that adopts it.
**Older priorities (2026-11-12):** 1. T0a tracking (≈ 11-16, all books incl. main + pair) → 2. (X1d done: fspread deployable at gross 1.0) → 3. C1 cost calibration (from 11-24) → 4. W1 data analysis once ≥ 2 weeks (HL taker flow
vs next-day returns, same rule as flow@bn, ≈ 11-26) → 5. T2b (a)/(c) + longer hold (b showed decay continues to day 120) → 6. T5b.
- [x] R1 DONE 2026-11-17 (findings): leg-sum tail real but the shorts are the alt-factor hedge; no-short filters fail; symmetric 5% per-name cap adopted (2/3 confirm). Untried: intraday stop via the watcher (needs hourly data + LQ1 cascade flag). Was: (added 2026-11-14 review) **single-name short-squeeze tail of the Binance cross-sectional books.** 11-13: AKE +370% in a day
(0.0026→0.0124, $1.1B 4h volume) cost shadow:xsmom@bn ≈ 9% of the book and dented xsmom_k@bn/blend@bn/main_bn. Measure on bnall:
share of xsmom/flow/blend short-leg P&L lost to the worst single-name days, then pre-register ≥ 3 formulations (liquidity/age floor for
shorts, per-name short cap below max_asset_weight 0.35, intraday stop via the live watcher) judged on OOS SR + mdd, not on removing AKE.
- [x] M1 DONE 2026-11-12: HL main = blend_nested 1.0; main_bn = flow@bn/xsmom@bn/blend@bn 1/3 each. Was: **M1 main books trade the best estimate** (was planned for Thu 11-12; brought forward by the instruction above) (design.md 2026-11-10, owner mandate): apply the fixed rule
(equal-risk mix of the venue's candidates with WF OOS > 0.8 on that venue and `robust.worst` > 0) to set `incubation` + alloc for
`main` (HL) and `main_bn`; expected today: HL = blend_nested (it already is the rule-based mix; do not double-count blend), Binance =
flow@bn + xsmom@bn + blend@bn. Their `small:` twins follow automatically. State in STATUS.md that this is the paper best estimate,
not a funding recommendation. Then X2.
- [x] W1 DONE 2026-11-12: kripto-flow.service, data/hl/flow, side verified vs bbo, gaps.jsonl, watchdog heartbeat. Was: **W1 Hyperliquid trade-flow collector over the public websocket** (allowed since 2026-11-10): one connection, `trades` for the top
~60 coins, aggregated per coin per minute (taker buy / sell notional, trade count) into data/hl/flow/YYYY-MM-DD.parquet; verify
the taker-side field empirically against the book before trusting it; watchdog check for gaps. Non-backfillable, so build it this
week. Purpose: flow natively on HL (today only Binance flow exists; it transfers to HL prices before costs).
0. [x] C1 DONE 2026-11-25 → model kept (scripts/cost_calibration.py; ×0.56 withdrawn; listing-day fills ≫ cap; monthly re-run). Was: **C1 cost-model calibration** (2026-11-19: after the re-fit, re-run research/studies/t2b_hyst.py confirm with the new thin-name costs: HL listing churn is 43% of events) (assumptions.md row 1; 2026-11-17: add library N11, spread ∝ σ/√N, as the competing model; T0a: live costs ≤ model except listing_short 0.20% vs 0.13% of equity): live fills cost 5.4 bp on HL vs 9.6 bp modelled (2 days). From 2026-11-24
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
- [x] W3 DONE 2026-11-25 → OPEN weaker (WF pick 0.44 / avg 0.23, a 2024+ market-wide effect; findings). Untried: W3b BTC+ETH-only overlay, prior low. Was: (2026-11-19: REPLICATED on 616 unseen coins, +62 bp simple, t 2.3, both periods +) **NEXT: one pre-registered walk-forward** (Tue 11-24).
  Think-through first: (1) market-wide vs coin-specific: split each event into the universe's Sunday move and the coin's excess; if the market
  part carries it, the book is ONE bet per Sunday (≈ 50/yr: slow evidence) and BTC/ETH-only may be the cleaner form; (2) formulations: raw fade
  (the replicated one) / excess-over-universe fade (market-neutral) / BTC+ETH-only fade; (3) grid ≤ 6 configs (thr 1–2%, hold 12/24 h), tranche the
  18:00 clock time (17/18/19 NY) like friday_follow; dataset bn100 1h (fair universe; now fits in 2 GB, `--probe` first). Live book needs an hourly
  Binance feed in venue_bn (shared with FF1(b)); build it only if the WF passes. Was: W3 Sunday-move fade (findings 2026-11-15): fading the Sunday 12:00→18:00 New York move for 24 h made +20 bp (2020–23) and +105 bp
  (2024–26, t 2.6) across 82 coins; not pre-registered. One pre-registered confirmation on coins outside the 82 (needs FF1's hourly data).
- [x] LQ1 DONE 2026-11-17: kripto/liq.py + kripto-liq.service (/market/ws path; the legacy /ws path is silent), data/bn/liq raw rows, watchdog. Was: Binance liquidation prints: public websocket `!forceOrder@arr` (read-only, HARD RULE 1 allows it) → data/bn/liq, same pattern as
  kripto/flow.py. Needed to tell a liquidation cascade from an ordinary dump (E1b, T7, insilico R12). Non-backfillable.
- [x] T0a DONE 2026-11-17: scripts/live_vs_backtest.py; HL books track (corr 0.99–1.00), BN gaps = replay universe (fixed by paper.record_universe). Run weekly. Was: **Live-vs-backtest replay (tracking check)**: for each shadow book, re-run the backtest over exactly the live period
  and compare day by day: positions, turnover, costs/slippage (model vs live order book), funding, returns. Build
  scripts/live_vs_backtest.py once books have ≥ 7 days (≈ 2026-11-16). Large tracking error = bug or bad cost model.
- [ ] ~~L4~~ **Residual reversion with entry threshold (library N5, Pole)**: NEW angle vs dead xsrev: BTC-beta-defactored
  residuals, enter only past a z-threshold, exit on reversion, so turnover is a fraction of xsrev's. HL + bnall, ≤ 8 configs.
- [x] L1 → DEAD at taker costs: hourly effects are real (t ≈ 8) but 2–5 bp vs 25–40 bp costs (2026-11-10, findings). Was: **HL lags Binance? (library N4)**: cheap kill test: BN 1h alt return → HL same-coin next-1h return. Expect
  ≈ 0 (arbitraged in seconds). If |IC| is meaningful after costs, it becomes a strategy.
- [x] P2 InSilico second pass (2026-11-15, research/insilico_pass2.md): ~30 formulations, 9 confirmation tests, 4 walk-forwards. Profile levels,
  trade-size capitulation (Binance), mousetrap, range retest, unit price, US-session momentum, spike-high short: DEAD with reasons.
  friday_follow OPEN → FF1; lshock OPEN → E1; R28 removed from the backlog (dead).
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

- [x] E2 DONE 2026-11-26 (PC, findings "E2 execution-time tilt"; follow-up E2b / InSilico E2B). Was: **Execution-time tilt** (calendar finding 11-11: BTC/ETH drift +5–9 bp in the hour CME is shut, 17–18 New York, both eras, t 2.3–3.6).
  Not a book (below costs). Descriptive check first: would moving the daily books' BUYS before 17:00 NY and SELLS after 18:00 NY have saved
  cost over the live fills so far and over 6 y of hourly bars? research/studies/. A cost saving is worth as much as a signal.
- [x] DONE 2026-11-26 (M1 re-derivation: blend@bn → blend_nested@bn). Was: blend@bn → nested choice? H4 on bnall picks carry+carry_trend+xsmom (1.16), not the hindsight trio (1.30). Needs Binance
  funding in the live BN panel (carry). Do with X2's BN funding collector.

- [x] 2026-11-27 backlog 0 (ladder@bn into main_bn) → overlay sleeve, incubation alloc 1.0 (journal 2026-11-27).
- [x] X1e fspread_hold unseen-history evidence (FC1C c, 2026-11-27): the frozen live config (lb14/enter 0.1) on the never-seen 2023-05-15..2024-06 pair window (HL funding backfilled) = SR 14.2, 26.6%/yr net at gross 2.0, mdd −0.6%. Its DSR fail was 1.66 y of OOS: re-run the pair WF on the longer panel (pair now starts with HL funding 2023-05) and walk the incubation gate clause by clause (two-account margin = gross 1.0, X1c). Research session, not insilico. → DONE 2026-11-27: WF OOS 5.66 / 2.85 y, DSR 1.00 → incubation, main@pair (journal 2026-11-27).
- [x] T5c (2026-11-27, PRE-REGISTERED, rule frozen before any confirm look) **OI-build filter on the Binance books' long side**: on each decision day, among universe names with a positive
  3-day return, drop LONG weights of names whose 3-day log OI change (Binance metrics, last 5-min row of the day) is in the top tercile; renormalise nothing (the book just holds less).
  Test with the F0 harness (apply transform) on flow@bn and xsmom@bn, bnall 1d, **confirm window 2024-01-01..2026-11 only** (explore 2023 done: findings T5b). Pass = SR up ≥ +0.1 AND the dropped
  longs' next-day mean < kept longs' in ≥ 2 of 3 confirm years, against random drops of the same count (≥ 90th pct). One shot; no knob changes. Also, untried T5b forms (prior low): F1 as a
  short-side filter, positioning on 4h bars, HL positioning (T6b) as the HL analogue. → FAIL 2026-11-27 (flow dSR −0.04, xsmom −0.22; sign flips after 2024; findings T5b).


## moved 2026-11-28
- [x] KS1 first half DONE 2026-11-28 (venue_pair accounts + transfer + guard, design.md 2026-11-28). Remaining = KS1b:
- [x] HLI2 → CLOSED by insilico F0C 11-27: cash-on-idle = random day masks (54th pct on hlu_explore): exposure effect. HLI2 (insilico HLI 2026-11-27, research session, prior low-medium) **HL main book: listing_short's third in cash when it holds nothing** instead of re-scaling lowvol + tsmom
  to the full vol target. Backtest SR 1.39 vs 1.34, >= in every year (research/is3/hli_a.json); 2026 idle 21 % of days as HL's qualifying listings fell to ~1/month (hli_b.json). Needs a WF
  (pre-registered, 1 config) and an F0-style check that it is not just less exposure. Meanwhile quote the 2-leg HL expectation (SR ~1.06) next to the headline in STATUS.
- [x] PRB2 → ADOPTED 2026-11-28 (WF 1.82 vs 1.45 same data; forward judge PRB2-F). Was: PRB2 (insilico PRB+PRL 2026-11-28, research session, prior MEDIUM: cost lever, HL-specific; PRX: no replication on bnall 2021-23 .73 vs .81; HTN: because HL trades cost 8-22 bp/unit vs BN 6 bp) **HL main book: tsmom + lowvol legs trade a third of the gap to target (lam .33), listing_short
  in full**: PRL pre-registered held-out HL 2025-26 net SR 2.10 vs 1.86 (whole-book lam .33 1.94), costs 7.0 -> 4.0 %/yr; band .01 >= full 3/4 years (2023 tie), 2x cost better every year;
  $200 (band .05) worse 3/4 -> $1,000 only. tsmom = over half the book's cost (turnover 35-64x). research/is3/prb_*.json, prl_*.json. Do: paper engine per-leg option `partial_lam` (live
  blend: leg target' = leg held + lam*(leg target - leg held), needs per-leg held state in paper.db), shadow variant at $1,000, judged on forward days vs shadow:blend_nested.
  Min order: 56 % of lam .33 trades are < $10 at $1,000: keep the leg target and trade when the cumulative gap clears $10 (CMB simulated it: 3/4 years > lam1, 2023 worse; the band form is not better live).
- [x] HBL2 → CLOSED 2026-11-28, no change: listing_short corr BTC is already −.04 (the beta-neutral claim holds), the fix costs .06 SR. Was: HBL2 (insilico HBL 2026-11-28, research session, risk fix) **listing_short: coins without a 20-d beta hedged at 1.35, not 1.0**: pooled young-coin beta 1.37/1.46 (HL 2023-24, age 2-7/8-20 d),
  1.34/1.26 (bnall 2021-23), down-beta 1.5-1.6; pre-registered HL 2025-26: corr BTC closer to 0 (listing_short -.04 -> +.01) for -.06 SR (research/is3/hbl_*.json). Decide as a risk choice
  (design.md: beta-neutral claim), code in strategies.beta_to fill / hedge_beta, pytest + trader run.
- [x] HLE2 → NOT a filter (insilico HLB 2026-11-28: skip rule lowers HL listing_short 1.37 -> 1.21, blend worse 3/4 years; event-level new-float contrast replicated on bnall (HLX) but the book needs the established coins too).
- [x] HLU1 → DEAD 2026-11-27 (insilico: BN-only shorts are the momentum books' best; findings).
- [x] LD3 → OPEN 2026-11-27 insilico (findings). LD3 (2026-11-27, library N14, prior medium; insilico/research, descriptive first) **ladder fills in liquidity holes vs heavy-volume flushes**: split the E2 ladder fill set by the fill
  minute's Amihud ratio vs the coin's 30-day median; predict the high-illiquidity half bounces more. Explore ≤ 2023, confirm 2024+, per-day P&L + worst day, size-matched vs random skips.
- [x] **LV2c** → insilico BNH 11-27: HL blend 1.30 without lowvol vs 1.34; lowvol picked OOS 2025-01: keep (findings). **LV2c 2026-11-27: HL lowvol leg FRAGILE** (SR 0.70 on HL since 2023-03 with backfilled funding; 2025 2.36, every other year ≤ 0.5; w/o best 10 days 0.23; research/is3/lv2_hlc.json). The HL main book (blend_nested) holds it; the 2027-01-02 refit decides by rule, but a research session should check whether the nested selection would still pick it with the 2023-05+ funding (it was chosen on data with funding only from 2024-07). **LVS 11-28:** lowvol on HL = two opposite market bets netting ~0 beta; price spread +5..+6 %/yr eaten by long-side funding; whole return = 2025 high-vol short side (+22 % net; ex-2025 -3 %/yr). One year deep; refit by rule (research/is3/lvs_a.json).
- [x] T9b → DEAD 2026-11-27 insilico T9B (late runs cost ~nothing; findings). T9b Alpha-decay curve per strategy (library N8, maxdama §7): signed return of each strategy's trades from decision to +1/4/12/24 h.
  Explains T9 and sizes the cost of a late run (one bar late costs tsmom a third). Descriptive, hourly data.
- [x] T8 Regime filter → DEAD 2026-11-27 (insilico T8R: 6 states × 3 BN books, = random masks; findings).
- [x] LSB2 → NO-GO 2026-11-28 insilico LSX (stops = 2021 insurance vs placebo; capped books SR ≤ .42, 2025–26 flat; findings). LSB2 (insilico LSB 2026-11-27, research session, prior medium) **listing_short on Binance inside main_bn** (PRECHECK LSP 11-27 NEGATIVE: equal-weight book SR .18, 2025 −.40, 2026 −.33, 2023–24 profit = BTC hedge leg; w/o worst 10 days .66: needs a squeeze control before any WF; SQZ 11-27: 'far above post-listing low' has a 2x tail but blocking it = random masks) while HL's listing flow is dry (HL ~1/month in 2026, BN ~5.7).
  bnall events (≥ $1M 7-d volume, d2→d61 short-vs-BTC incl. funding): median +22…+41 % every year 2020–26, win 69–85 %, mean set by squeezes (2021 −79 %; 2025 +4, 2026 +9 %).
  Pre-register ONE config (listing_short defaults, band .005) on bnall; re-check the 11-09 finding that the bnall WF was BTC-leg P&L (corr BTC .63); stress the worst 10 events. research/is3/lsb_ab.json.
- [x] E2b → DEAD at its size 2026-11-28 insilico E2C (break deferral 2024-only, rank 19-20/23; anchor free; → FPD). E2b (from E2, 2026-11-26; prior low–medium, effect fading 7.2 → 2.1 → 1.1 bp) **daily BN books decide on the 16:00/20:00 UTC bar, buy at the CME break, defer sells ≥ 1 h**: first the
  phase/robustness check that moving flow@bn's anchor does not cost signal P&L; only then a shadow variant, judged on forward days. HL re-check at > 12 months of hourly data.
- [x] T5d → DEAD 2026-11-28 insilico T5D (F3 short-side filter: sign alternates by year, inside a shuffle null; F3 dead after 3 forms; findings). T5d (2026-11-27, prior LOW after T5c) untried T5b forms: F3 losers' side as a SHORT-side filter (rising OI on a 3-day fall → bounce; explore 2023 IC +0.032), the 2021–22 explore
  for a regime check once `scripts.metrics_coverage` ≥ 95%, and HL positioning (T6b) as the HL analogue. F1/F2 failed explore. Any confirm must span ≥ 2 regimes (T5c flipped sign after 2024).
