# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

**2026-11-27 research DONE:** ladder@bn → incubation as an overlay sleeve of main_bn (+ $200 twin); X1e → fspread_hold@pair incubation in the new two-account book main@pair
(alloc 0.5); main_scale written (main 0.87, main_bn 1.16; next 12-01); LV2c (nested choice still picks lowvol). Detail: journal 2026-11-27.
**Next priorities (2026-11-27):** 0. KS1 (insilico 11-27 KSW/KSA/PAC: main@pair needs a per-account transfer rule + per-account equity in venue_pair before it counts as fundable; kill switch scaled to vol) → 1. X1f (below) at ≥ 30 live days of main@pair / the pair shadow → 2. T5d (low prior; T5c failed 11-27) 2021–22 metrics explore once ≥ 95% (11-27: 72% / 76%)
→ 3. E1 + LQ1 (≈ 12-01) → 4. ladder sleeve check: first main_bn sleeve fills vs the shadow's (same minute, size = 2.9% × main_bn equity) → 5. fill-delay re-measure ≈ 12-09 → 6. T6b HL positioning (≈ 12-07)
→ 7. W2 re-check ≈ 12-23 → 8. E2b CME-break execution (fading) → 9. low prior: W3b, FC1(c), LV1 short leg, FF1 market-relative.
- [ ] KS1 (insilico KSW 2026-11-27; design change, research session; general rationale, not a book's result) **kill switch scaled to vol**: today −25 % fixed for every book = KSA (insilico 11-27, research/is3/ksa_abc.json): WITHOUT transfers one pair account halves in 2 y with ≥ 90 % probability (historical path: liquidated); rule "rebalance to 50/50 when one account < 70 % of the other" = ~14 transfers/yr, worst account −29 %; guard: flatten main@pair if an account is −40 % from its peak. Model the per-account equity in the paper book (venue_pair) before main@pair counts as fundable. PAC (11-27): live shadow pair accounts already +28 / −27 % after 2 weeks (≈ ±14 % at main@pair size; a 70 % transfer due by 11-20). Spec: venue_pair records per-venue account equity hourly (half the start capital each; legs price + funding − fees), the watchdog WARNs at < 70 %, STATUS shows both; research/studies/is3_pac.py reconstructs it meanwhile.
  1.0× the directional main books' vol (24 %): 2-y false-alarm 11–15 % on the backtest edge vs 72–84 % on a zero edge; at the steady mode's 30 % target the same −25 % is 0.83× vol (~35 % false).
  Proposal: kill = 1.25 × the book's vol target (4 % false / 50–65 % power on 2 y; research/is3/ksw_c.json); plus a per-venue-account drawdown guard for main@pair (book vol 0.8 % hides
  −27…−46 % 7-day swings of each account, X1C a). Record in design.md changelog; apply from the next session (HARD RULE 5).
- [x] HLI2 → CLOSED by insilico F0C 11-27: cash-on-idle = random day masks (54th pct on hlu_explore): exposure effect. HLI2 (insilico HLI 2026-11-27, research session, prior low-medium) **HL main book: listing_short's third in cash when it holds nothing** instead of re-scaling lowvol + tsmom
  to the full vol target. Backtest SR 1.39 vs 1.34, >= in every year (research/is3/hli_a.json); 2026 idle 21 % of days as HL's qualifying listings fell to ~1/month (hli_b.json). Needs a WF
  (pre-registered, 1 config) and an F0-style check that it is not just less exposure. Meanwhile quote the 2-leg HL expectation (SR ~1.06) next to the headline in STATUS.
- [ ] PRB2 (insilico PRB+PRL 2026-11-28, research session, prior MEDIUM: cost lever, HL-specific; PRX: no replication on bnall 2021-23 .73 vs .81; HTN: because HL trades cost 8-22 bp/unit vs BN 6 bp) **HL main book: tsmom + lowvol legs trade a third of the gap to target (lam .33), listing_short
  in full**: PRL pre-registered held-out HL 2025-26 net SR 2.10 vs 1.86 (whole-book lam .33 1.94), costs 7.0 -> 4.0 %/yr; band .01 >= full 3/4 years (2023 tie), 2x cost better every year;
  $200 (band .05) worse 3/4 -> $1,000 only. tsmom = over half the book's cost (turnover 35-64x). research/is3/prb_*.json, prl_*.json. Do: paper engine per-leg option `partial_lam` (live
  blend: leg target' = leg held + lam*(leg target - leg held), needs per-leg held state in paper.db), shadow variant at $1,000, judged on forward days vs shadow:blend_nested.
  Min order: 56 % of lam .33 trades are < $10 at $1,000: keep the leg target and trade when the cumulative gap clears $10 (CMB simulated it: 3/4 years > lam1, 2023 worse; the band form is not better live).
- [ ] HBL2 (insilico HBL 2026-11-28, research session, risk fix) **listing_short: coins without a 20-d beta hedged at 1.35, not 1.0**: pooled young-coin beta 1.37/1.46 (HL 2023-24, age 2-7/8-20 d),
  1.34/1.26 (bnall 2021-23), down-beta 1.5-1.6; pre-registered HL 2025-26: corr BTC closer to 0 (listing_short -.04 -> +.01) for -.06 SR (research/is3/hbl_*.json). Decide as a risk choice
  (design.md: beta-neutral claim), code in strategies.beta_to fill / hedge_beta, pytest + trader run.
- [ ] HLE2 (insilico HLE+HLX 2026-11-28, research session, prior medium-high) **listing_short: skip coins with >= 60 d of Binance perp history at listing** (HL: those n 42 mean +1 %, t .13 vs fresh/new
  +25-29 %, t 2.1-2.4; research/is3/hle_ab.json). Held-out DONE (HLX 11-28, frozen): bnall listings of coins on HL >= 60 d n 10, buy-hold median -5 % vs new +36 %: replicates.
  Next: ONE pre-registered WF of listing_short with the skip rule on HL (drops 42 of 165 events, 22 in 2023); needs the first-trade date on the other venue point-in-time (data.bn/hl files).
- [ ] LSB2 (insilico LSB 2026-11-27, research session, prior medium) **listing_short on Binance inside main_bn** (PRECHECK LSP 11-27 NEGATIVE: equal-weight book SR .18, 2025 −.40, 2026 −.33, 2023–24 profit = BTC hedge leg; w/o worst 10 days .66: needs a squeeze control before any WF; SQZ 11-27: 'far above post-listing low' has a 2x tail but blocking it = random masks) while HL's listing flow is dry (HL ~1/month in 2026, BN ~5.7).
  bnall events (≥ $1M 7-d volume, d2→d61 short-vs-BTC incl. funding): median +22…+41 % every year 2020–26, win 69–85 %, mean set by squeezes (2021 −79 %; 2025 +4, 2026 +9 %).
  Pre-register ONE config (listing_short defaults, band .005) on bnall; re-check the 11-09 finding that the bnall WF was BTC-leg P&L (corr BTC .63); stress the worst 10 events. research/is3/lsb_ab.json.
- [ ] HLL1 (2026-11-27) ladder rule on HL minute bars: `nice -n 19 .venv/bin/python -m research.studies.hl_ladder --confirm` at ≥ 60 days of flow data (≈ 2027-01-15); explore had 7 fills
  (findings). Kill if HL-only fills < ⅓ or confirm median ≤ 0. NOTE for every study on data/hl/flow (W2, TSZ-HL): coins drop out of the collected top-60 for days; split at gaps, never ffill across them.
- [x] HLU1 → DEAD 2026-11-27 (insilico: BN-only shorts are the momentum books' best; findings).
- [ ] T5d (2026-11-27, prior LOW after T5c) untried T5b forms: F3 losers' side as a SHORT-side filter (rising OI on a 3-day fall → bounce; explore 2023 IC +0.032), the 2021–22 explore
  for a regime check once `scripts.metrics_coverage` ≥ 95%, and HL positioning (T6b) as the HL analogue. F1/F2 failed explore. Any confirm must span ≥ 2 regimes (T5c flipped sign after 2024).
- [x] LD3 → OPEN 2026-11-27 insilico (findings). LD3 (2026-11-27, library N14, prior medium; insilico/research, descriptive first) **ladder fills in liquidity holes vs heavy-volume flushes**: split the E2 ladder fill set by the fill
  minute's Amihud ratio vs the coin's 30-day median; predict the high-illiquidity half bounces more. Explore ≤ 2023, confirm 2024+, per-day P&L + worst day, size-matched vs random skips.
- [ ] X1f (2026-11-27; (b)(c) DONE insilico X1V 11-27: live vol = backtest's own vol on those days (98th-pct window), marks/timing minor; live pairs differ -> queue X1U) fspread_hold live vol vs backtest.** Live price-P&L vol 3.2%/yr (gross ~1.2, 15 d) vs backtest 1.4% (gross 1.9, synchronised 00:00 closes); the 11-10 WF had vol 6.5% on
  dates where today's data gives ≈ 1.1% (no code change found; the HL funding/candle files were rebuilt by the FC1C backfill). Do: (a) `scripts.ledger_decomp shadow:fspread_hold@pair` and main@pair
  at ≥ 30 days; (b) replay the backtest on the live days and compare day by day (live_vs_backtest does not support pair books: extend it); (c) test whether HL markPx vs Binance markPrice
  definitions explain the noise (mark both legs from the same-minute trade prices). If live vol stays ≥ 3× backtest, recompute the DSR with live-like vol and say so in STATUS (the incubation
  → active check needs that band anyway). Also watch the yearly decay (2026 YTD 1.9% net at gross 1.9): retire per §4 if live 60-day Sharpe < 0.
**Older priorities (2026-11-26 research, superseded above):** 1. DONE 11-27: `scripts.main_scale --write` (AL2b, design.md 2026-11-26; first application,
monthly after that via `main_scale_due`) and check main_bn's first days on flow@bn + blend_nested@bn (switched 11-26 08:03) → 2. T5b positioning: backfill is newest-first per coin,
so 2022–23 currently holds only coins with SHORT top-60 spells (BTC starts 2024-07): explore only once 2021–23 is complete (≈ 11-29; check per-year coverage of BTC/ETH first)
→ 3. E1 + LQ1 (≈ 12-01) → 4. fill-delay re-measure ≈ 12-09 → 5. T6b HL positioning (≈ 12-07) → 6. W2 re-check ≈ 12-23 → 7. LD2 ladder cap 5 + size re-derivation (server, full universe, size-matched)
→ 8. E2b execution clock at the CME break (fading) → 9. low prior: W3b, FC1(c) pre-2024-07 HL funding, LV1 funding-filtered short leg, FF1 market-relative.
**2026-11-26 PC session (journal):** LD1, LV1, LO1, FC1(a)(b), E2 done descriptively, 0 walk-forwards spent; carry/carry_trend HL audited (DEAD holds). C1 monthly (≈ 12-25). Weekly: T0a in the retro. T2b(f) listing-day costs DONE 11-26 (robust; findings).
- [ ] E2b (from E2, 2026-11-26; prior low–medium, effect fading 7.2 → 2.1 → 1.1 bp) **daily BN books decide on the 16:00/20:00 UTC bar, buy at the CME break, defer sells ≥ 1 h**: first the
  phase/robustness check that moving flow@bn's anchor does not cost signal P&L; only then a shadow variant, judged on forward days. HL re-check at > 12 months of hourly data.
- [ ] A1 progress: 11-15 xsrev, lowvol; 11-22 tsmom long-only, funding_contra (both → OPEN, one form); 11-26 carry (HL), carry_trend (HL): DEAD holds (3 forms, diagnosed). Next: resrev, T9 maker execution.
- [x] **LV2c** → insilico BNH 11-27: HL blend 1.30 without lowvol vs 1.34; lowvol picked OOS 2025-01: keep (findings). **LV2c 2026-11-27: HL lowvol leg FRAGILE** (SR 0.70 on HL since 2023-03 with backfilled funding; 2025 2.36, every other year ≤ 0.5; w/o best 10 days 0.23; research/is3/lv2_hlc.json). The HL main book (blend_nested) holds it; the 2027-01-02 refit decides by rule, but a research session should check whether the nested selection would still pick it with the 2023-05+ funding (it was chosen on data with funding only from 2024-07).
- [ ] LV1 (a)(b) DONE 2026-11-26 (PC) → 4 forms fail net of funding (findings). Left, prior low: short leg without negative-funding names (needs HL/forward as confirm). Was: LV1 (2026-11-15 dead-list audit; lowvol relabelled OPEN) (c) ANSWERED 2026-11-17 by R1: high-vol shorts are not the losers (median +31–39 bp), no. (a)/(b) untried, prior low. Untried forms, prior low–medium: (a) bnall daily, survivorship-free (BN-82 drops the
  delisted high-vol losers that the short leg would have earned on); (b) idiosyncratic (BTC-residual) vol instead of total vol; (c) as a FILTER:
  drop the top-vol decile from the x-sec books' short side (same question as R1: are the high-vol shorts the squeeze losses?). ≤ 6 configs total.
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
- [ ] TSZ-HL Trade-size buckets on Hyperliquid (kripto/flow.py `tsz`, per taker address, since 2026-11-12; non-backfillable). After ≥ 8
  weeks (≈ 2027-01-07): R1/R2 event study natively on HL, where one address = one order. Low prior after the Binance result; the data is
  also the input for W2 (large takers). Check at every review that `tsz` is non-empty.
- [ ] D1 One-voiced buying at a 1-day high (+6 bp / 1 h held-out) as an entry-timing feature for `flow` / breakouts: low value, only with TSZ-HL.
- [ ] R3/R7 Range ("rotation") bars with trade count and size-bucket delta: second aggTrades pass (scripts/aggtrades.py keeps 5-min bars
  only). Low prior now that R1 and R4 are dead on time bars; do only together with LQ1 or if TSZ-HL shows something.
- [ ] X1H (insilico 2026-11-27, OPEN): re-run the FROZEN exit band x .05 (is3_x1h.py d) on 2026-12..2027-05 as forward data; adopt only via a research WF if it beats the live rule by >= 0.5 %/yr.
- [ ] X1c (a/b done insilico 11-27: X1C; c at 30 live days, 12-12) fspread_hold robustness (descriptive, no new WF unless a new rule): per-pair basis excursions (worst daily |basis|),
  funding-interval mix on BN (1h/4h/8h coins), and a re-run when HL funding backfill reaches all coins (pair has 84 → more).
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
- [x] T9b → DEAD 2026-11-27 insilico T9B (late runs cost ~nothing; findings). T9b Alpha-decay curve per strategy (library N8, maxdama §7): signed return of each strategy's trades from decision to +1/4/12/24 h.
  Explains T9 and sizes the cost of a late run (one bar late costs tsmom a third). Descriptive, hourly data.
- [ ] L6 (2026-11-27 insilico L6V → OPEN, research/is3/l6v_*.json) **ewm20 variances in vol_target**: track the vol target 9–23% better in 6/6 book × sample cells (blend@bn confirm −22%),
  SR mixed (xsmom confirm −0.21); HAR over-forecasts. A design-level risk change for a research session (design.md entry, all books at once, never in a promoting session); low priority.
- [ ] L3 **Square-root impact sanity check of the slippage model (library N3)**: do this with T0a once there are live fills. → queued as InSilico L3S 2026-11-27.
- [ ] L5 Value-area rejection (library N7, Dalton/AMT): low prior, after the above.
- [ ] T2b **listing_short follow-ups** (pre-register ≤ 8 configs each). (b) DONE 2026-11-12 (event study: linear decay to d120 on both
  venues → new (d): hold 90/120 d pre-registered, judged on bnall where 800 events exist):
  (a) DONE 2026-11-27 (insilico LS1): coverage 95%, SR 1.36 with funding, not fragile (findings);
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
- [x] T8 Regime filter → DEAD 2026-11-27 (insilico T8R: 6 states × 3 BN books, = random masks; findings).

## Done
Completed and superseded items (with their original text) are in `research/backlog_done.md` (moved 2026-11-26). Move an item there when it is done; keep this file to open work.
