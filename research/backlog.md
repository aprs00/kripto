# Research backlog (highest priority first)

Also read research/findings.md before picking: it records what is already DEAD and why.

Format: `- [ ] <id> <hypothesis> — why it could pay / data needed` ; when done: `- [x] ... → <one-line result, link to journal>`

**2026-11-27 research DONE:** ladder@bn → incubation as an overlay sleeve of main_bn (+ $200 twin); X1e → fspread_hold@pair incubation in the new two-account book main@pair
(alloc 0.5); main_scale written (main 0.87, main_bn 1.16; next 12-01); LV2c (nested choice still picks lowvol). Detail: journal 2026-11-27.
**2026-11-28 research DONE:** PRB2 adopted in the HL main book (slow legs lam .33; WF 1.82 vs 1.45 same data), reference shadow blend_nested_lam1; KS1 first half
(per-venue accounts, 70 % transfer rule, 40 % account guard in venue_pair); held_back matches results to entry params; tsmom@bn retired (book count); HBL2 closed (no change); main_bn sleeve first fill
(AKE, same minute as the shadow, 2.9 % of equity: item 4 done). Detail: journal 2026-11-28.
**Next priorities (2026-11-28):** 1. PRB2 forward check at 30 live days (≈ 12-28, below) → 2. X1f at ≥ 30 days (≈ 12-12) → 3. E1 + LQ1 (≈ 12-01) → 4. fill-delay ≈ 12-09 → 5. T6b ≈ 12-07 → 6. T5d (low)
→ 7. W2 ≈ 12-23 → 8. (FPD low) → 9. KS1b (low, see below) → 10. low prior: W3b, FC1(c), LV1 short leg, FF1 market-relative, NPC2, TLQ2, HFX2.
- [ ] FLX2 (insilico FLX 2026-11-28, research session, prior MEDIUM) **flow@bn's price edge is ~0 since 2025; its return is funding carry** (research/is3/flx_ab.json: 2025/26 gross
  23.6/13.8 %/yr = funding 18.9/15.4 + price +4.7/-1.6; 2023-24 price +33-35). Decay not significant (HAC t -1.0; blend control -1.34), no retire clause met. Do: pre-register ONE comparison on
  bnall WF: main_bn = .5 flow + .5 blend vs blend alone vs flow-without-funding-names; decide with forward days, not this table (a 2-year lull happened in 2022 too).
  FLP precheck (11-28, research/is3/flp_ab.json): full sample .5 flow 1.75 vs blend alone 1.66 (2025-26 .86 vs .98); funding overlap per coin .85. PRE-REGISTERED: keep flow only if
  WF OOS (i) - (ii) >= +.1 SR and forward days do not contradict (one WF, counts in the DSR).
- [ ] SMX (insilico SMD 2026-11-28, research session, prior MEDIUM-HIGH: it decides whether the owner's $200 option is real) **small: twins round small targets UP to the minimum order**
  (a target >= half the venue/symbol minimum is placed AT the minimum, sign kept; below half: 0). Today the engine drops them: small:main = BTC only, small:main_bn 3 of 31 names.
  Descriptive (research/is3/smd_b.json, smd_track.json; rule fixed a priori): HL $200 SR 1.21 vs 1.58 at $1,000 (corr .78, deployed .61/.72 2025/26) vs truncation 1.38 at corr .40 / 2.7 names;
  BN 1.50 vs 1.77 (corr .91, deployed .83/.75). Do: paper.rebalance option `round_min` for small: books only (tests: known answer on a toy book), research small_acct_round in robustness,
  design.md changelog (the twin models what a small trader would do; general, not a result). Judge on live: small twins' tracking of their big sibling (live_vs_backtest --main) after 30 days.
  SMY precheck (11-28, research/is3/smy_a.json, smy_b.json): live 10 d replay corr to the big sibling round-min .94 HL / .87 BN vs truncation -.63 / .40 (= the live twins exactly);
  churn 13 / 15 % of gross; hysteresis (.5/.25) worse. FROZEN SPEC: half-minimum round-up, no hysteresis, small: books only.
  Pair books (SMP 11-28): a pair is already held whole or not at all (venue_pair.whole_pairs, shipped); SMX adds round-up of BOTH legs to the larger minimum
  (history $200: SR 7.33 vs whole-only 6.57 vs $1,000 7.34; research/is3/smp_b.json).
  SXR (11-28, research/is3/sxr_a.json, sxr_b.json): $200 twins needing it (< 50 % deployed today, >= 79 % rounded): carry@bn (0 %), flow@bn, blend_nested, xsmom@bn, tsmom; fine: blend,
  blend_nested@bn, xsmom_k@bn, pair books.
  CTG (11-28): the effective minimum is max(min notional, ONE STEP x price): Binance BTC step .001 > the $56 target of small:carry_trend@bn -> floored to 0. SMX rounds up to that.
- [ ] SMB (insilico LVB/SMQ/SMH 2026-11-28, prior HIGH for honesty, small) **$200 books (BN AND HL) are min-order limited; research small_acct ignores per-symbol minimum orders** (BTC $50, ETH $20, others $5):
  small:main_bn holds 3 of 31 targets, 10 % of its target gross (research/is3/lvb_b.json); kripto/research.py small_acct = one band min/small_equity, so every BN $200 Sharpe is overstated.
  Do: (1) STATUS.md states the $200 BN book's deployed gross next to its return; (2) small_acct with per-symbol minima (venue_bn.symbol_filters cache; delisted = $5) in kripto/research.py, general rationale
  in design.md changelog (a measurement fix, not a gate); (3) re-quote the BN candidates' small_acct. insilico SMQ (queue) measures (3) descriptively first.
  SMQ (11-28, research/is3/smq_abc.json, smq_d.json): main_bn mix at $200 with minima SR 1.70 vs 1.75 but deployed share .39 (2025) / .19 (2026; 2.6 names): the account is
  mostly cash now (universe 113 -> 532 names, weights per name below the minima). Top-4 vol-matched $200 book: SR 1.56, deployed 2026 .47 (prior LOW, a different book; only if the owner's $200 option matters).
  SMH (11-28, research/is3/smh_a.json): HL too: the $200 HL book holds BTC + 1-2 names of 124-144 (live: BTC only, $31); SR 1.12 is BTC timing. Neither $200 twin holds its strategy:
  the honest STATUS line is 'a $200 account cannot run these books' unless a $200-specific book (few names) is built and tested.
  SMR (11-28) DONE step (2): robustness now reports small_acct_min + small_deployed (kripto/research.py, known answer exact). Left: (1) STATUS rows, (3) re-quote at the next WFs.
- [ ] T9G (insilico T9F 2026-11-28, research session, prior MEDIUM after T9P (11-28: at the touch fills ~always on minute paths, +4 bp/unit vs live taker): flow@bn pays ~11 %/yr taker costs in backtest) **live rest-below shadow for flow@bn's daily orders**: each target change rests
  k = 10 bp beyond the decision price for 24 h, residue to the next day (skip) or taker beyond 1x step (env); fills judged on LIVE Binance trade prints / 1-min lows with a >= 3 bp
  trade-through (kripto/ladder.py already simulates resting bids on live 1-min klines: reuse its fill code); compare its fill rate, runaway cost and net vs the taker shadow after >= 60 days.
  Backtest (findings T9F): +2 %/yr at k10/q3 but fill-model-bound, post-hoc cell: the shadow is the test, not a promotion.
  FROZEN by T9K (11-28, rule stated before the table): flow k = 50 bp, carry_trend k = 20 bp, skip mode. Report fill share (backtest 90 % / 95 %) and per-fill selection (signed move
  decision -> fill vs k; backtest: improvement given back ~1:1) next to net P&L: the backtest's robust part is the maker fee, +8-9 %/yr on flow's turnover.
  T9L (11-28, live replay of 370 Nov orders): fill share 88 % (backtest 90 %), filled = wrong-way half (-264 vs +543 bp/24 h); live taker slip 1.1 bp -> maker saving ~4 bp/unit: use it.
  T9C (11-28, PRE-REGISTERED confirm 2024-26): FAIL both (flow k50 +8.7 %/yr vs taker but -0.2 vs random fee-only fills, 2026 -1.0; carry_trend k20 +2.5 vs taker, -0.95 vs placebo).
  Depth adds nothing out of sample: if T9G is built, test the plain maker-fee saving (post at the touch, residue carried) and report fill share + selection; prior LOW-MEDIUM.
- [ ] T9c (library N15, 2026-11-28, prior LOW-MEDIUM; T9 relabel angle: envelope, no fallback) **post-only toward PRB2's curve, taker only outside an envelope** on the HL main book's slow legs.
  Needs HL 1h history ≥ 18 months (T9 note) or a live resting-order engine; first a descriptive check of post-only fill rates for the slow legs' daily gaps on BN-82 1h (explore ≤ 2023) to size it. **T9D precheck 11-28 (findings): ≈ +1 %/yr on HL at fitted cost, 0 on BN → prior LOW; revisit 2027-10 (18 months HL 1h).**
- [ ] PRB2-F (2026-11-28) **forward judge of the slow-leg main book**: at ≥ 30 live days of both shadow:blend_nested (slow_lam .33 since 11-28) and shadow:blend_nested_lam1 (old config),
  **T9Q 11-28 (research/is3/t9q_ab.json): on HL's own live fills + HL 1-min paths, at the touch fills 99.8 % (median 1 min); main book +3.89 bp/unit vs live taker (40 orders, 13/13 days) ≈ +1.2 %/yr at its turnover; only thin-name runaways cost. Frozen live-shadow spec k0/q5/carry residue; build ONE resting-order engine for T9G + T9c. Prior MEDIUM-LOW.**
  `scripts.ledger_decomp` both. Pre-registered: KEEP if the slow book's live fees + slippage per day ≤ 75 % of lam1's and the daily P&L difference (slow − lam1) has t > −1; otherwise revert
  blend_nested to lam 1. Then retire blend_nested_lam1. At the 2027-01-02 refit update BOTH entries' components.
**Older priorities (2026-11-27):** 0. KS1 (insilico 11-27 KSW/KSA/PAC: main@pair needs a per-account transfer rule + per-account equity in venue_pair before it counts as fundable; kill switch scaled to vol) → 1. X1f (below) at ≥ 30 live days of main@pair / the pair shadow → 2. T5d (low prior; T5c failed 11-27) 2021–22 metrics explore once ≥ 95% (11-27: 72% / 76%)
→ 3. E1 + LQ1 (≈ 12-01) → 4. ladder sleeve check: first main_bn sleeve fills vs the shadow's (same minute, size = 2.9% × main_bn equity) → 5. fill-delay re-measure ≈ 12-09 → 6. T6b HL positioning (≈ 12-07)
→ 7. W2 re-check ≈ 12-23 → 8. (FPD low after PDX) → 9. low prior: W3b, FC1(c), LV1 short leg, FF1 market-relative.
- [ ] KS1b (prior low; decided 11-28: keep −25 % for now, a steady-mode $1,000 owner halting only past −31…−37 % is outside "steady"; false alarms cost evidence time, not money; revisit if a book with a real edge is killed by noise) KS1 (insilico KSW 2026-11-27; design change, research session; general rationale, not a book's result) **kill switch scaled to vol**: today −25 % fixed for every book = KSA (insilico 11-27, research/is3/ksa_abc.json): WITHOUT transfers one pair account halves in 2 y with ≥ 90 % probability (historical path: liquidated); rule "rebalance to 50/50 when one account < 70 % of the other" = ~14 transfers/yr, worst account −29 %; guard: flatten main@pair if an account is −40 % from its peak. Model the per-account equity in the paper book (venue_pair) before main@pair counts as fundable. PAC (11-27): live shadow pair accounts already +28 / −27 % after 2 weeks (≈ ±14 % at main@pair size; a 70 % transfer due by 11-20). Spec: venue_pair records per-venue account equity hourly (half the start capital each; legs price + funding − fees), the watchdog WARNs at < 70 %, STATUS shows both; research/studies/is3_pac.py reconstructs it meanwhile.
  1.0× the directional main books' vol (24 %): 2-y false-alarm 11–15 % on the backtest edge vs 72–84 % on a zero edge; at the steady mode's 30 % target the same −25 % is 0.83× vol (~35 % false).
  Proposal: kill = 1.25 × the book's vol target (4 % false / 50–65 % power on 2 y; research/is3/ksw_c.json); plus a per-venue-account drawdown guard for main@pair (book vol 0.8 % hides
  −27…−46 % 7-day swings of each account, X1C a). Record in design.md changelog; apply from the next session (HARD RULE 5).
- [ ] TLQ2 (insilico TLQ 2026-11-28, research session, prior LOW-MEDIUM after TLX: HL-specific, Binance held-out fails: thin names trend there, top 10 worse 5/7 years) **HL main blend: tsmom top_n 10 instead of 20**: thinnest tier (ranks 15-20) lost 3/4 years net; prereg confirm 2025 2.17 vs 2.19 (FAIL by .02 as written), 2026 1.99 vs 1.47, costs lower every year (research/is3/tlq_*.json). Overlaps half of PRB2. Do: one pre-registered WF (1 config, counts in the DSR) and, if it holds, a shadow variant judged on forward days vs shadow:blend_nested; decide PRB2 and TLQ2 together (they share the saving).
- [ ] HFX2 (insilico HFX 2026-11-28, prior LOW after HFZ: shorts account alone 109 % vol, worst 7-d −57 %, 122 transfers in 3.5 y (research/is3/hfz_ab.json): not operable with manual transfers) **HL main book: hold the long legs (BTC hedge + long alts with a Binance twin) on Binance, shorts on HL**: funding saving +3.3/+8.7/+3.8/+2.2 %/yr of book 2023-26 (research/is3/hfx_ab.json), tracking negligible. Needs the two-account structure (venue_pair) with per-account guard + transfer rule (KS1), and the HL account then carries unhedged short alts: measure per-account 7-d swings first.
- [ ] NPC2 (insilico NPC 2026-11-28, prior LOW after NPS: knife-edge, cap .5 inert and .3 loses on both venues (HL 1.10, bnall 1.07 vs standard 1.21/1.52); only a threshold-free version (factor clustering) is worth a WF; H4 stays at the refit) **blend_nested selection with a 0.4 correlation cap** (greedy by expanding Sharpe, skip a candidate with expanding daily corr > .4 to a chosen one, hold fewer): prereg NPC_cap04 PASSED on HL OOS (1.27 vs 1.21, 2/3 years) and cached bnall 2020-10..2026-11 (1.72 vs 1.52, 5/6 years >=); 2026 inside the test (no vault left), HL binding corr .41 at the cap (research/is3/npc_*.json). Capped HL choice today: listing_short, tsmom, xsmom_k (drops lowvol: LVS/LVQ). Do: add `corr_cap` to strategies.nested_selection (default None = H4), one registered WF per venue (counts in the DSR), then decide at the refit by rule; quote the threshold fragility. FTL: report which leg filled the capped slot each refit (xsmom_k = real, SR .25-.85 corr 0; resrev/xsmom = coin flips) and the 2-leg slot-empty book as the dilution baseline. FTB: on bnall the cap drops carry (corr .49 with carry_trend) for tsmom (6/6 years positive): BN side stronger than HL.
- [ ] HLL1 (2026-11-27) ladder rule on HL minute bars: `nice -n 19 .venv/bin/python -m research.studies.hl_ladder --confirm` at ≥ 60 days of flow data (≈ 2027-01-15); explore had 7 fills
  (findings). Kill if HL-only fills < ⅓ or confirm median ≤ 0. NOTE for every study on data/hl/flow (W2, TSZ-HL): coins drop out of the collected top-60 for days; split at gaps, never ffill across them.
- [ ] X1f (2026-11-27; (b)(c) DONE insilico X1V 11-27: live vol = backtest's own vol on those days (98th-pct window), marks/timing minor; live pairs differ -> queue X1U) fspread_hold live vol vs backtest.** Live price-P&L vol 3.2%/yr (gross ~1.2, 15 d) vs backtest 1.4% (gross 1.9, synchronised 00:00 closes); the 11-10 WF had vol 6.5% on
  dates where today's data gives ≈ 1.1% (no code change found; the HL funding/candle files were rebuilt by the FC1C backfill). Do: (a) `scripts.ledger_decomp shadow:fspread_hold@pair` and main@pair
  at ≥ 30 days; (b) replay the backtest on the live days and compare day by day (live_vs_backtest does not support pair books: extend it); (c) test whether HL markPx vs Binance markPrice
  definitions explain the noise (mark both legs from the same-minute trade prices). If live vol stays ≥ 3× backtest, recompute the DSR with live-like vol and say so in STATUS (the incubation
  → active check needs that band anyway). Also watch the yearly decay (2026 YTD 1.9% net at gross 1.9): retire per §4 if live 60-day Sharpe < 0.
**Older priorities (2026-11-26 research, superseded above):** 1. DONE 11-27: `scripts.main_scale --write` (AL2b, design.md 2026-11-26; first application,
monthly after that via `main_scale_due`) and check main_bn's first days on flow@bn + blend_nested@bn (switched 11-26 08:03) → 2. T5b positioning: backfill is newest-first per coin,
so 2022–23 currently holds only coins with SHORT top-60 spells (BTC starts 2024-07): explore only once 2021–23 is complete (≈ 11-29; check per-year coverage of BTC/ETH first)
→ 3. E1 + LQ1 (≈ 12-01) → 4. fill-delay re-measure ≈ 12-09 → 5. T6b HL positioning (≈ 12-07) → 6. W2 re-check ≈ 12-23
→ 8. (FPD low after PDX) → 9. low prior: W3b, FC1(c) pre-2024-07 HL funding, LV1 funding-filtered short leg, FF1 market-relative.
**2026-11-26 PC session (journal):** LD1, LV1, LO1, FC1(a)(b), E2 done descriptively, 0 walk-forwards spent; carry/carry_trend HL audited (DEAD holds). C1 monthly (≈ 12-25). Weekly: T0a in the retro. T2b(f) listing-day costs DONE 11-26 (robust; findings).
- [ ] A1 progress: 11-15 xsrev, lowvol; 11-22 tsmom long-only, funding_contra (both → OPEN, one form); 11-26 carry (HL), carry_trend (HL): DEAD holds (3 forms, diagnosed). Next: resrev, T9 maker execution.
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
  **T6P 11-28 precheck + PRE-REGISTRATION (research/is3/notes.md 'T6P', research/is3/t6p_ab.json): 0 gaps; accounts rotate (14 % day-to-day overlap: use per-account
  changes); MDE of the daily IC 28 d .096 / 60 d .065 -> EXPLORE 11-10..12-07, CONFIRM 12-08..2027-02-05 untouched; PASS = same sign, t >= 2, IC >= .03.**
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

## Done
Completed and superseded items (with their original text) are in `research/backlog_done.md` (moved 2026-11-26). Move an item there when it is done; keep this file to open work.
