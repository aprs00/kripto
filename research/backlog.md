# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

**Priority order (rewritten 2026-11-10 after H4/T9/X1b; research Tue + Thu, ≤ 6 new walk-forward experiments per session):**
## Owner instruction 2026-11-10 ("run everything now"): DONE 2026-11-12 06:40 research (M1, X2, W1 live; forward baseline). Journal 2026-11-12.
**Next priorities (2026-11-25 research):** 1. NEXT research session: re-derive the M1 lists from TF1 by the fixed rule (grid avg > 0.8, pick > 0, worst > 0; BN candidates
flow, xsmom, xsmom_k, tsmom, blend, blend_nested qualify on bnall; listing_short not) → 2. T5b positioning (≈ 11-29) → 3. E1 + LQ1 (≈ 12-01) → 4. T2b listing-day costs (XTEN: 160 bp
real vs 25 bp cap; see C1) → 5. fill-delay re-measure ≈ 12-09 (`research.studies.fill_delay`, after the 11-25 reorder) → 6. T6b HL positioning (≈ 12-07) → 7. W2 re-check ≈ 12-23
(pre-registered cells) → 8. low prior: W3b BTC+ETH-only Sunday fade, FC1, LV1, LO1. C1: re-run `scripts.cost_calibration` monthly (next ≈ 12-25). Weekly: T0a in the retro.
- [x] TF1 DONE 2026-11-25 (findings: all survive, no verdict changes; M1 re-derivation next session). Was: **Re-run the Binance walk-forwards on the clean panel** (no stock perps): the same 11-09 v2 grids for flow, xsmom, xsmom_k, tsmom, listing_short,
  blend, blend_nested on bnall, tagged as a data correction (no new hypotheses, grids unchanged). Report old and clean pick / grid average / worst; then re-derive the
  M1 lists by the fixed rule (grid average > 0.8, pick > 0, worst > 0) in the following session, not the same one. flow@bn (2026: 0.90 → 0.45) is the one at risk.
- [x] LU1 DONE 2026-11-22 (4 recorded bars): live top-30 = 29, 30, 30, 30 of the clean research top-30 → leave live as it is.
- [x] AL1 DONE 2026-11-25 → 1/N is enough (findings). FOLLOW-UP AL2 (next session, with the M1 re-derivation): main_bn's 1/N mix realises 14–18% vol vs the 25–30% steady target; pre-register a mix-level vol scaling (scale = 0.25 / trailing 60-d mix vol, cap max_gross) as a general rule for every main book, design.md entry, applied the session after. Was: (library N12, maxdama §6; 2026-11-25) **How to mix the M1 candidates in main_bn**: nested 60-d refits on bnall component returns: 1/N vs inverse-vol vs
  min-variance shrunk 50% to diagonal (daily, and 4h for more points); then empirical Kelly of the mix vs the vol target. Descriptive (no new signal), do it in the session
  that re-derives the M1 list (blend overlaps xsmom: the 1/3-each mix double-counts momentum). Prior: 1/N or inverse-vol wins; the value is knowing the overlap.
- [x] PL1 DONE 2026-11-25 → DEAD as entry filter (a/b/c + F1c fail; pumps are momentum's bull-year profit; findings). Untried: intraday stop (R1). Was: **Pump-and-crash tail on the LONG side** (11-22: IDOL, EVAA, AKE −42 to −48% overnight took 4.3% off xsmom@bn): R1 tested filters on shorts only. Think-through first;
  e.g. drop names whose 28-d score is made by ≤ 2 days, or with 7-d volume > 5× the 30-d median. Explore bnall ≤ 2023-06, confirm later, ≤ 3 forms. One night is not evidence.
- [ ] FC1 funding_contra untried forms (audit 11-22; prior low): (a) only extreme negative funding, long side; (b) conditional on price no longer rising; (c) HL-vs-BN funding
  gap as the crowding measure (= T3). ≤ 6 configs in all.  - [ ] LO1 tsmom long-only untried forms (prior low): excess over vol-matched BTC; BTC-only timing.
- [ ] IS3 **Superseded by the third-pass queue (research/insilico_queue.json, its own 12-h sessions: kripto-insilico.timer). Research sessions: do NOT work on it; W3's walk-forward stays here.** Was: what the second pass planned and did not run (audit 2026-11-22, journal). In order, think-through first, explore ≤ 2023 / confirm later, ≤ 6 WF in all:
  (1) **Range bars** (R3, R7; tg:103–107 "real edge", not even cited in the catalogue): build 0.4% move bars with trade count + size buckets from aggTrades (server can
  rebuild, public archive; raw is dropped, so a second pass; ≤ 2 workers, probe RAM first), BTC/ETH/SOL; R3 exhaustion, R7 ×10 velocity; judge against ≈ 13 bp. Prior low-medium:
  the 5-min version had the opposite sign. (2) lshock L6 pessimistic fills, L3 cascade-only on unseen coins, L4 wait for the end, L2 premium; then E1 (LQ1 ≈ 12-01).
  (3) **Filters for the live books** (never tested): P5 entries at prior POC / inside value, L5 no new shorts after a cascade day, T6 breadth inside `flow`. (4) R14 P4 gap fill; R21 with
  the real "collar" price. (5) low prior: FSVZO / Crayons guides (47 pages, no rule was ever written), R13 perp vs spot delta, R18, R26, R29, R30. Confluence: one fixed pair at most.
- [ ] A1 progress: 11-15 xsrev, lowvol; 11-22 tsmom long-only, funding_contra (both → OPEN, one form). Next: carry (HL), carry_trend.
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
- [ ] LV1 (2026-11-15 dead-list audit; lowvol relabelled OPEN) (c) ANSWERED 2026-11-17 by R1: high-vol shorts are not the losers (median +31–39 bp), no. (a)/(b) untried, prior low. Untried forms, prior low–medium: (a) bnall daily, survivorship-free (BN-82 drops the
  delisted high-vol losers that the short leg would have earned on); (b) idiosyncratic (BTC-residual) vol instead of total vol; (c) as a FILTER:
  drop the top-vol decile from the x-sec books' short side (same question as R1: are the high-vol shorts the squeeze losses?). ≤ 6 configs total.
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
- [ ] W2 (2026-11-25: plain taker-flow IC first look done, OPEN too early, re-check ≈ 12-23 on pre-registered cells; the per-address metaorder part is still untested) **Visible metaorders on HL (library N10, Tóth et al.)**: from ≈ 11-26 (2 weeks of W1 `big` data): persistent same-side net
  taking by one address → next 4h/24h return, per coin, volume-scaled; descriptive IC first (kill: |IC| < 0.02 or below costs), then a
  pre-registered ≤ 6-config walk-forward only if it survives. Also plain HL taker-flow imbalance (flow@bn's rule) on HL prices.
- [ ] FF1 (2026-11-19: (a) DONE → pick 0.78 / grid avg 0.61 on bn100, stays OPEN, no book; P&L = long leg of the 82 survivors. Remaining, prior LOW: market-relative move (coin minus universe) as one pre-registered form; (b) only if something passes) **friday_follow → candidate?** (findings 2026-11-15: WF bn_1h 1.06 cut-averaged, worst 0.78, corr BTC −0.03; the only second-pass
  survivor with a book). Before any lifecycle change: (a) hourly Binance klines for the survivorship-free top-100 (data.bn_all_symbols; ≈ 3 GB,
  nightly-job style) and the same pre-registered grid (`"cuts": [12, 15, 17, 20]`) on it; on the hand-picked 82 it may be survivor luck: at the
  UTC-day cut the full top-100 shows +46 bp per event (t 1.0–1.5) against +37 / +88 on the 82. (b) The paper engine decides on daily/4h bars:
  this book needs hourly decisions on Friday 16:00–21:00 UTC (check paper.compute_targets). (c) If (a) holds at OOS > 0.8 and worst > 0:
  candidate `friday_follow@bn` + shadow book; one trade a week, so live evidence is slow (≈ 50 events a year).
- [ ] A1 (11-15: xsrev audited, DEAD holds (4 forms, diagnosed); lowvol → OPEN, see LV1. Next: funding_contra, tsmom long-only) **Dead-list audit** (design.md §4 2026-11-12): Sunday retro, two DEAD entries a week, oldest first: xsrev, lowvol,
  funding_contra, tsmom long-only, carry (HL), carry_trend, resrev, T9 maker execution, L1 hourly lead-lag, minute-bar event study.
  Relabel to OPEN (one form failed) where fewer than three formulations were tested or no reason is diagnosed; list untried forms here.
- [ ] E1 **lshock (liquidation fade) follow-ups** (findings: OPEN, tail-event). 2026-11-15: use z=8, not 6 (73 unseen coins: +91 bp, every year
  positive; the open-interest split and coarser bars are dead ends; (b) is done and failed the day-level bar). In this order:
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
- [x] W3 DONE 2026-11-25 → OPEN weaker (WF pick 0.44 / avg 0.23, a 2024+ market-wide effect; findings). Untried: W3b BTC+ETH-only overlay, prior low. Was: (2026-11-19: REPLICATED on 616 unseen coins, +62 bp simple, t 2.3, both periods +) **NEXT: one pre-registered walk-forward** (Tue 11-24).
  Think-through first: (1) market-wide vs coin-specific: split each event into the universe's Sunday move and the coin's excess; if the market
  part carries it, the book is ONE bet per Sunday (≈ 50/yr: slow evidence) and BTC/ETH-only may be the cleaner form; (2) formulations: raw fade
  (the replicated one) / excess-over-universe fade (market-neutral) / BTC+ETH-only fade; (3) grid ≤ 6 configs (thr 1–2%, hold 12/24 h), tranche the
  18:00 clock time (17/18/19 NY) like friday_follow; dataset bn100 1h (fair universe; now fits in 2 GB, `--probe` first). Live book needs an hourly
  Binance feed in venue_bn (shared with FF1(b)); build it only if the WF passes. Was: W3 Sunday-move fade (findings 2026-11-15): fading the Sunday 12:00→18:00 New York move for 24 h made +20 bp (2020–23) and +105 bp
  (2024–26, t 2.6) across 82 coins; not pre-registered. One pre-registered confirmation on coins outside the 82 (needs FF1's hourly data).
- [ ] D1 One-voiced buying at a 1-day high (+6 bp / 1 h held-out) as an entry-timing feature for `flow` / breakouts: low value, only with TSZ-HL.
- [x] LQ1 DONE 2026-11-17: kripto/liq.py + kripto-liq.service (/market/ws path; the legacy /ws path is silent), data/bn/liq raw rows, watchdog. Was: Binance liquidation prints: public websocket `!forceOrder@arr` (read-only, HARD RULE 1 allows it) → data/bn/liq, same pattern as
  kripto/flow.py. Needed to tell a liquidation cascade from an ordinary dump (E1b, T7, insilico R12). Non-backfillable.
- [ ] R3/R7 Range ("rotation") bars with trade count and size-bucket delta: second aggTrades pass (scripts/aggtrades.py keeps 5-min bars
  only). Low prior now that R1 and R4 are dead on time bars; do only together with LQ1 or if TSZ-HL shows something.
- [ ] X1c fspread_hold robustness (descriptive, no new WF unless a new rule): per-pair basis excursions (worst daily |basis|),
  funding-interval mix on BN (1h/4h/8h coins), and a re-run when HL funding backfill reaches all coins (pair has 84 → more).
- [ ] blend@bn → nested choice? H4 on bnall picks carry+carry_trend+xsmom (1.16), not the hindsight trio (1.30). Needs Binance
  funding in the live BN panel (carry). Do with X2's BN funding collector.
- [x] T0a DONE 2026-11-17: scripts/live_vs_backtest.py; HL books track (corr 0.99–1.00), BN gaps = replay universe (fixed by paper.record_universe). Run weekly. Was: **Live-vs-backtest replay (tracking check)**: for each shadow book, re-run the backtest over exactly the live period
  and compare day by day: positions, turnover, costs/slippage (model vs live order book), funding, returns. Build
  scripts/live_vs_backtest.py once books have ≥ 7 days (≈ 2026-11-16). Large tracking error = bug or bad cost model.
- [ ] T5b (2026-11-19: DATA JOB BUILT: `scripts.download metrics` (also inside the nightly `all`, 15k files/night) → data/bn/metrics_full/<SYM>.parquet, cols oi, oiv, top_acct_ls, top_pos_ls, all_acct_ls, taker_ls, 5-min; target = every coin-day in the point-in-time top 60 since 2021 (290 coins, 128k files) ≈ 9 nights → analysis from ≈ 11-29. Explore 2021–23, confirm 2024+) (2026-11-17: data/bn/metrics holds OI only, 10 coins, 2021–23; the long/short ratios need one daily archive file per coin-day ≈ 100k+ files: build a capped nightly download job first, e.g. current top-60 from 2022, ≈ 2k files/night) **Positioning hypotheses NOW on Binance history** (added 2026-11-09, owner wants results fast; don't wait months
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
  (e) DONE 2026-11-19: hysteresis rejected by its pre-registered rule (HL SR 1.45 → 1.37; the dv exit is a squeeze filter on HL); re-run the same rule after C1. Was: (review 2026-11-18) **liquidity-threshold churn**: XTEN entered on the 11-15 bar at 7-d dv $1.07M (min_dv $1M, just over), filled
  at 60 bp slip, exited one bar later (dv $0.43M) at 22 bp: ≈ 80 bp round trip for a 1-day hold, ≈ 1% of the shadow book. Test entry at
  min_dv with stay-in at min_dv/2 (hysteresis) and/or a dv floor of 2× min_dv at entry; count how often HL/bnall listings cross the line.
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
- [ ] W2 **Book-event collector (non-backfillable)**: HL public websocket `l2Book` deltas for BTC/ETH/SOL + 2 thin names, per-minute aggregates of
  size pulled / added within 5 bp of mid on each side (InSilico wa 18.10.19: "real alpha is price reaction to pulls and lifts of limit orders"; S2b5).
  Every week not collected is lost; build like kripto/flow.py (heartbeat + data-arrival check, ≤ 300 MB). Test after ≥ 6 weeks.
- [ ] L1p **Single-liquidation spring-back (from 2027-02-17, ≥ 3 months of data/bn/liq)**: InSilico wa 18.10.35(3) "as a big (or relatively big for the contract) position
  is liquidated fully, we spring back to origination points; tracking individual liqs is ok". Event = one coin's liquidation prints in 1 min ≥ 99th pct of its own
  liq size; entry after the prints stop; target = price before the first print; placebo = same-size taker bursts without liq prints. L1 (closed OPEN) had no print data.
- [ ] T3 HL-vs-Binance funding spread as a crowding signal (HL retail flow is distinct; HL hourly vs BN 8h funding).
- [ ] T7 Liquidation-cluster proximity as risk filter for trend positions (positions data now collected, T6b).
- [ ] T8 Regime filter: trend/carry vs BTC vol regime or funding level (≤ 2 regime params; beware overfitting).

## Done
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
