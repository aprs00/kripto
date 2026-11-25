# Findings ledger

One entry per hypothesis ever tested. Read this before choosing research. Keep each entry ≤ 5 lines.
Verdicts: **ALIVE** (candidate/incubation/active) · **OPEN** (inconclusive, blocked on data, or **one form failed**: a single
formulation was tested and failed; the untried forms are in the backlog) · **DEAD** (at least three materially different formulations
failed AND the reason is diagnosed; revisit only with a new angle stated). Standard since 2026-11-12 (design.md §4): entries above
that date used DEAD after as little as one formulation and are re-audited two per week in the Sunday retro (`audited <date>` when done).
Numbers are walk-forward out-of-sample, net of fees + slippage + funding unless noted. SR = annualised Sharpe.

## Cross-cutting lessons (apply to everything)
* **Verify the plumbing, not just the result.** A unit bug silently voided a whole day of research (2026-11-09). Any
  helper touching timestamps/alignment needs a unit test on synthetic data with a known answer.
* **Passive execution is not a free cost cut for daily signals (T9, 2026-11-10).** Post-only maker orders cut fees ~70%, but the
  orders that don't fill are the ones that run away (alpha loss), and fills come as the price moves against you. On 6 years of
  BN-82 that took back as much return as the fees saved. Lowering turnover is the cost lever, not swapping taker for maker: X1b's hysteresis cut fspread
  turnover from 70–410× to 10–50× and turned a dead idea into the cleanest candidate so far.
* **Costs are the binding constraint on Hyperliquid.** The HL top-20 by volume includes thin memes; slippage +
  fees took ~8%/yr off trend. Any HL strategy must be judged at HL cost levels, not Binance's. By 2026-11-09 three signals
  are real before costs and dead after them on HL (xsmom_k: 2× costs 0.31; flow-on-HL: +19% gross, 17% costs; funding
  capture: +6–13% funding, 6–36% costs). The next unit of effort belongs to execution (T9), not to another signal.
  Always report gross, costs and turnover separately: "dead" and "dead at taker costs" are different verdicts.
* **The HL cost model looks ≈ 1.8× too pessimistic for our order sizes (2026-11-10, 2 calm days, 234 fills, median $49).** Live
  slippage 0.9 bp on both venues vs 5.1 bp modelled on HL (thinnest bucket: 1.5 live vs 9.9 modelled). At live-calibrated costs
  (×0.56): flow-on-HL 0.23 → 0.54, xsmom HL 0.00 → 0.31, fspread −0.25 → 0.89, tsmom 1.03 → 1.15, blend 1.56 → 1.73. Not a gate
  number until C1 re-fits the model on ≥ 14 days incl. a volatile one. Every HL "dead at taker costs" verdict is provisional.
* **Deciding more often earns more before costs and less after them (2026-11-10, BN-82 5.7 y + HL 2.2 y).** tsmom: daily → 4h →
  1h decisions: before costs +25% → +31% → +31%/yr, turnover 79× → 169× → 281×, net SR 0.92 → 0.78 → 0.58; xsmom 0.45 → 0.22 →
  −0.20. Finer bars with daily decisions: tsmom +0.06–0.16, xsmom ±0.05. Re-test after C1: cheaper costs shift the optimum.
* **Account size decides what is executable.** At $200 a $10 min order is 5% of equity and 20–30 name books could not be
  traded (band 0.05). Since 2026-11-10 the main book is $1,000 (the owner's deployable capital): band 0.01, broad books fit.
  Binance's $5 min order allows twice the breadth again. Always quote which band a number used. $200 vs $1,000 for the chosen
  configs (2026-11-10, full-sample SR): many-name books need the bigger account (flow 1.31 → 0.72, xsmom bnall 1.49 → 0.97,
  blend_nested HL 1.41 → 0.99); concentrated ones don't (listing_short 1.56 → 1.47, tsmom 0.87 → 0.93, blend HL 1.56 → 1.81,
  fspread_hold 1.89 → 2.21; rises are band-as-turnover-filter noise, not a gain). Live `small:` twins are the real test.
* **Binance results do NOT transfer automatically to HL** (see carry). Every idea must pass on HL data.
* BN 4h dataset is survivor-biased (hand-picked 82 coins). **`bnall`** (2026-11-09) = every Binance USDT perp ever listed
  incl. delisted (923), daily bars: use it as the second venue for anything where survivorship matters (listings, shorts, breadth).
* **Band/hedge artifacts.** The 5% no-trade band (the $200 executability rule) silently drops small positions. A broad
  hedged book then becomes "long the hedge": listing_short on bnall showed OOS 1.08 with corr BTC 0.63, mostly BTC-leg P&L.
  Always check corr to BTC + leg decomposition + band 0.005 (inspect_strategy prints these since 2026-11-09). Judge the
  *signal* at a small band; judge *executability at $200* separately.
* HL 1d candles before a coin's HL listing are zero-volume oracle prices; the loader masks them since 2026-11-09.
* **Don't derive epoch ms/ns via `asi8`/`astype(int64)`** (pandas 3 = µs). Bit me twice on 2026-11-09 (live bug + a test).
* **Statistical power is low; know the error bars.** SE(annual Sharpe) ≈ √((1 + SR²/2) / years). HL walk-forward OOS ≈
  1.6 years ⇒ ±0.8; BN ≈ 6 years ⇒ ±0.4; 3 weeks live ⇒ ±4. So: a single HL number is weak evidence either way; demand
  consistency (per-year signs, grid breadth, BN agreement, an economic mechanism) before concluding. Live paper P&L
  proves nothing about edge for many months. Its job is checking that live behaves like the backtest
  (fills, costs, bugs).
* **DSR counts experiments, not registry lines** (since 2026-11-09). A WF OOS record is deflated by the number of
  walk-forward experiments ever run (40 at the change) and judged on the longest survivorship-free venue (bnall ≈ 6 y,
  needs OOS SR ≈ 1.4). HL can't show significance in 1.6 y; on HL the gate asks for OOS > 0.8 net of HL costs. Cost
  stresses and re-checks no longer raise the bar, so run them freely; new *experiments* do raise it.
* **Diversify before polishing.** Three ~0.6–1.0 SR candidates with corr ≈ 0.1 blend to ~1.6 on HL (T4). Combining
  low-correlated weak signals beats tuning any one of them; judge new ideas also by their correlation to the blend.
* **Rebalance-phase luck (2026-11-09 review).** Schedules are anchored at the epoch, so a config with `every_days` > 1 is
  tested on one phase only. By phase: bnall xsmom_k lb14 k5 weekly 1.46/0.56/0.26/0.41/0.47/0.96/0.54 (mean 0.66), HL xsmom_k
  3d 0.65/0.04/0.38. Broad xsmom is stable (0.60–0.79). Concentrated + infrequent = phase lottery: judge the PHASE AVERAGE
  (staggered tranches) and report the spread. FIXED in harness v2: `strategies.scheduled` trades the tranche average in
  research and live, and `robust.phases` shows every single start day.
* **Headline numbers are start-date and delay sensitive.** HL blend: 1.82 all history, 1.30 since 2024-09, 0.81 on 4h from
  2024-07; 1-day execution delay 1.82 → 1.34 (tsmom 1.06 → 0.71). Quote `robust.worst` next to any OOS Sharpe.
* **A per-trade t-stat lies when trades cluster (2026-11-12, lshock).** 730 trades gave t 3.3 per trade but t 1.6 on daily sums: three
  crash days were 72% of the P&L. For any event strategy quote the day-clustered t, the share of the top 3 days and the result without them.
* **A conservative fill model decides passive strategies (2026-11-11, range_retest).** A resting bid that needs a 1 bp trade-through is
  filled exactly when price keeps going: 57.5% winners and still −1.9 bp per trade before fees. "Bounces most of the time" ≠ profitable.
* **Picking the in-sample best config mostly adds noise (2026-11-15, research/studies/wf_selection.py).** On the same folds the equal-weight
  grid average beat the walk-forward pick in 6/9 strategy×venue pairs (mean OOS SR 0.95 vs 0.78; tsmom HL 0.53 vs 0.18, xsmom HL 0.47 vs −0.02).
  So a low pick-best OOS with a healthy grid median (tsmom, xsmom HL) is weak evidence against the IDEA, and a pick that beats its grid average
  (flow bnall 1.43 vs 1.25) is partly luck. Every result now carries `oos_grid_avg`: quote it next to the OOS Sharpe (backlog WF1).
* **Event studies in log returns flatter shorts (2026-11-15, spike_high_short).** Coins at a volume-spike high lagged the market by 170–374 bp
  over 10 days in LOG terms (t −3 to −7, both samples) and the short book still lost (WF −0.44): in SIMPLE returns the mean was −80 / −4 bp
  (median −4 to −5%; 3–5% of shorts lose > 50%), and shorts of pumped coins PAID funding (−34%/yr). For any short or skewed event report
  simple-return mean AND median, the tail, and the funding sign before building anything.
* **A "level" claim needs placebo levels (2026-11-15, profile rules).** Yesterday's POC bounced +8 bp over 2 h; a fake POC taken from 8 days
  earlier bounced +7. Every level a move reaches looks reactive. Same for failed breaks of yesterday's low (+11 real vs +8 placebo).
* **Check a translated rule's base rate on the venue first (2026-11-15).** "Every size bucket net negative" fires on 3–6% of days on Bybit
  inverse and on 17–30% on Binance USDT-M (hedging venue: structural sell bias). The first pass tested a different event without noticing.
* **Tranche an arbitrary clock time (2026-11-15, friday_follow).** Shifting the decision by a few hours moved it between +28 and +103 bp per
  event. As with start days: trade the average over the reasonable choices and judge that (Sharpe 1.21 → 1.06, worst 1.02 → 0.78).
* **DEAD on HL ≠ dead forever.** HL history grows every day. Re-test DEAD ideas that died on HL alone (not on BN
  too) once HL OOS history has grown by ≥ 6 months, as a pre-registered re-check (see backlog T0b).

## Hypotheses

> 2026-11-09: everything before this date was re-run with the fixed rebalance code (T0, same grids). Registry lines 1–179
> (git ≤ c1e3c1f) are invalid but stay in the registry (append-only); they only make DSR more conservative.
> The re-run numbers were close to the invalid ones (so the bug's backtest effect was smaller than feared).

> **2026-11-09 late: harness v2.** Schedules slower than daily now trade as staggered tranches (average over every start day),
> the band is 0.01 (the main book is $1,000), and every walk-forward stores a robustness block (`worst` = min of base, 2× costs,
> one bar late, first 6/12 months dropped). Lines marked **v2** are the same pre-registered grids re-measured that way
> (batches 2026-11-09-h1-recheck-*). Unmarked numbers used band 0.05 and ONE start day: treat them as upper bounds.

### tsmom: multi-horizon time-series trend, L/S, vol-targeted (2026-11-08, re-run 11-09) → ALIVE (weak; blend leg + shadow)
**v2: HL 1d OOS 0.08 (grid med 0.58, 12/12 >0; mdd −47%), bnall 0.65 (med 0.96; chosen cfg worst 0.97).** The walk-forward keeps
picking badly among the 12 (long-only variants), so the grid median is the fairer number: ~0.6 HL, ~1.0 Binance.
Old: HL 4h 0.43–0.55, BN-82 1.31 (survivor-biased), bnall 0.97. One day late costs a third (1.06 → 0.71). Fails the gate alone.

### tsmom long-only (2026-11-08) → OPEN (one form, diagnosed as beta; audited 2026-11-22, was DEAD)
2022 −33%, 2025 −11%: it is BTC beta, not an edge. Audit 2026-11-22: one form (a restriction of tsmom); its grid SR is 0.65–1.0 on bnall, like the L/S book,
so "beta" was asserted, never measured against holding BTC at equal vol. Untried, prior low: LO1 (excess over vol-matched BTC; BTC-only timing; as blend leg).

### tsmom signal smoothing (EMA 3/7d) and $20M liquidity floor (T1c, 2026-11-09) → DEAD (smoothing) / weak (floor)
Smoothing halves turnover (63→28/yr) but Sharpe falls more (HL 1.11→0.34, BN 1.00→0.99 at best; lag kills the signal).
$20M/day floor: +0.1–0.5 SR on HL in 3/4 pairs, ≈0 on BN. WF OOS HL 0.57, BN 1.08. Not worth a separate book.

### xsmom: cross-sectional momentum, beta-hedged (2026-11-08, re-run 11-09) → DEAD on HL, ALIVE on Binance (shadow xsmom@bn)
**v2: bnall 1d OOS 1.34 / 6.1y (DSR 0.85, med 1.15, 12/12 >0, worst 1.03, corr BTC 0.04); HL 1d OOS −0.09 (med 0.06).**
It needs ~30 names: impossible at $200 (band 0.05 halved it), executable at $1,000. Start days agree (0.60–0.79 for lb28/3d), so
this is not schedule luck. Fails the gate: DSR < 0.9 and negative on HL. Why HL differs is open (thinner alts, costs ×2–3).

### carry: short high funding / long low funding, dollar+beta neutral (2026-11-08, re-run 11-09) → DEAD on HL (re-check ~2027-05)
HL OOS −0.89, grid med −0.34 (2/12 >0); BN 1.06 (med 0.72). On HL high-funding names are squeezes that keep rising.
Concentrated: HL −1.05, BN 0.50. Carry needs breadth and doesn't transfer to HL.

### carry_trend: carry only where trend agrees (T1d, 2026-11-09) → DEAD on HL
HL OOS −0.88, grid med −0.52 (0/6 >0); BN 0.65 (med 0.88, 6/6). Conditioning on trend doesn't rescue HL carry.
Funding +2–3%/yr on HL can't pay ~5–8%/yr costs.

### listing_short: short new perps 1–14d after listing for 30–90d, BTC-beta hedged (T2, 2026-11-09) → ALIVE (candidate, shadow)
**v2: HL 1d OOS 0.89 / 2.95y (med 1.34, 9/9 >0; cfg (1,60) worst 1.33), bnall 0.86 / 6.1y (med 0.42, 9/9; corr BTC 0.00).** At band
0.01 the old bnall band artifact (corr BTC 0.63) is gone and the short leg shows. Holds one and two days late (1.47 → 1.27 → 1.01).
Open hole: funding is known for only 28% of HL short exposure, and new-listing shorts can pay heavy funding (T2b a). DSR 0.42.
**T2b(b) event study (2026-11-12, descriptive, research/studies/t2b_listing_event.py):** log abnormal return vs BTC from the day-1
close, median: HL (129 events) −17% d14, −49% d60, −82% d120; bnall (794) −12% / −34% / −51%; 76–84% of events negative at d60,
every cohort year negative on both venues (weakest bnall 2021 −7% mean). The decay is ~linear to day 120, not front-loaded, so the
60-day hold is not a tuned peak (longer holds untested). Funding to a short over 60 d: median +1.3–1.8%, mean −1–2%, worst −162%:
small on average, fat-tailed (squeezes). Mechanism holds; the risk is a few squeezes, not the average.
### blend: equal-risk tsmom(top12) + xsmom_k + listing_short, 1 pre-registered rule (T4, 2026-11-09) → ALIVE (candidate, shadow; best so far)
**v2: HL 1d OOS 1.61 / 2.95y (worst 1.15 = 2× costs; one day late 1.32), bnall 1.30 / 6.1y (DSR 0.81, worst 0.99, corr BTC 0.07).**
Fails only DSR > 0.9. Caveats that v2 does NOT remove: components were chosen with hindsight (nested selection at return level:
0.62–1.24 vs 1.36, rule-dependent → H4), and HL since 2024-09 is 1.3, not 1.8 (2023–mid-2024 carries it). Honest HL range ≈ 0.6–1.2
until H4 says otherwise. Shadow books on both venues (blend, blend@bn).
### xsmom_k: top/bottom-k x-sec momentum, k = 3–5, beta-hedged (T11, 2026-11-09) → ALIVE on Binance (weak on HL)
**v2 (tranched): bnall 1d OOS 1.12 / 6.1y (DSR 0.67, med 1.01, 8/8, worst 0.94); HL 1d OOS 0.73 but grid med 0.20, 2× costs 0.31.**
The pre-v2 "bnall 1.37, DSR 0.87" was one lucky weekday (start days 0.26–1.46, mean 0.66 for lb14 k5 weekly). On HL the single
start days still span 0.22–0.90. With $1,000 the broad xsmom is executable and stronger, so xsmom_k has lost its reason to exist
except as the blend's momentum leg.
### xsrev: short-term cross-sectional reversal (2026-11-08, re-run 11-09) → DEAD (audited 2026-11-15: holds)
HL OOS −2.66, BN −1.81; 0/6 >0 on both. Turnover makes fees dominate. Audit: four materially different forms failed (rank reversal 1–7 d;
thresholded BTC-residual reversion = resrev; hourly x-sec reversal = L1; minute extreme-move fades) and the reason is diagnosed: daily residual
moves CONTINUE (price-only SR −0.72), intraday reversal is real (t ≈ 8) but 2–5 bp vs ≥ 12 bp round trip. Untried, low prior: bnall (T10).

### lowvol: betting against volatility, beta-hedged (2026-11-08, re-run 11-09) → OPEN (one form failed; audited 2026-11-15, was DEAD)
HL −0.24 (1/6 >0); BN OOS 0.44 but grid med −0.01 (3/6 >0). Not robust. Note 2026-11-10: under harness v2 (tranches, band 0.01) the
DEFAULT config is HL full-sample 0.90 (bnall 0.22) and H4's selection rule picks it as an HL blend leg; no new WF run, verdict unchanged.
Audit 2026-11-15: ONE form (total-vol rank, beta-hedged, HL + survivor-biased BN-82 4h) and no diagnosis of why it failed; H4 keeps
picking it on HL. Untried forms → backlog LV1 (bnall, idiosyncratic vol, high-vol exclusion as a filter for the x-sec books' shorts = R1).

### funding_contra: fade funding spikes vs own history (2026-11-08, re-run 11-09) → OPEN (one form failed; audited 2026-11-22, was DEAD)
HL −0.81 (0/8 >0); BN −0.42 (med 0.15). Not robust. Audit 2026-11-22: ONE form (z-scored funding jump, cross-sectional, daily); no diagnosis beyond turnover.
BN grid is mixed, HL clearly negative (squeezes keep rising, as with carry). Untried → backlog FC1 (extreme negatives only, conditional on price, HL-vs-BN funding gap).

### resrev: BTC-defactored residual reversion with entry threshold (library N5/Pole, 2026-11-09, interactive) → DEAD
New angle vs xsrev (threshold, residuals, low turnover). Still 0/9 >0 on HL 1d (OOS −0.59), bnall 1d (−0.85), BN 4h (−1.13);
HL 4h −0.18 (1/9). Price-only SR −0.72 (BN 4h lb7 thr1.5), negative 5/7 years: extreme residual moves CONTINUE over days
(that is xsmom's effect), so it isn't the costs. Reversion in crypto residuals, if it exists, is intraday/HFT, out of reach.

### flow: cross-sectional taker-flow imbalance (library N1/N2, 2026-11-09, interactive) → ALIVE (candidate, shadow flow@bn)
**v2: bnall 1d OOS 1.42 / 6.1y (DSR 0.88, the closest to 0.9 so far); chosen lb3: base 1.31, one day late 1.07, 2× costs 0.75 (= worst).**
Continuation 6/6 >0, reversal 6/6 <0 (so "grid median > 0" fails mechanically: half the grid is the opposite hypothesis).
Cost-sensitive (lb3 turns over fast): the live shadow book's fills are the real test. corr xsmom 0.43, resid variant 0.77.
**Not testable on HL** (no taker split in HL candles) → L2b cross-venue test.

### flow on HL prices: Binance taker flow → trade the same coins on HL (L2b a, dataset hlx, 2026-11-09) → DEAD at taker costs (signal transfers)
HL 1d WF OOS 0.03 / 2.97y, grid med −1.54, 2/12 >0. The SIGN carries over: continuation lb14 earns ≈ +19%/yr before costs, reversal
loses in all 6 configs (−1.5 to −2.2). But HL costs are 17–50%/yr at this turnover (118–366×): net SR 0.23 at best, −0.40 at 2× costs.
So flow is real on both venues and only tradable where costs are low (Binance). Revisit on HL only with cheaper execution (T9).

### fspread: HL-vs-Binance funding capture, same coin long on one venue and short on the other (X1, dataset pair, 2026-11-09) → DEAD at taker costs (funding leg real)
pair 1d WF OOS −1.42 / 1.67y, 0/9 >0. The funding difference IS there: +6% to +13%/yr of equity at gross ≤ 2, price risk cancels
(vol ≈ 2–4%). But weights that follow the spread turn over 70–410×/yr and cost 6–36%/yr: more than the funding in every config.
Best (lb14, thr 20%): funding +6.3%, costs −6.0%. New angle if revisited (not tested): enter on a wide spread and HOLD until it
flips (hysteresis), liquid pairs only, passive execution. Needs T9 first. Only 84 coins have HL funding history (2024-07+).

### blend_nested: blend with component SELECTION out-of-sample (H4, 2026-11-10) → ALIVE (candidate, shadow blend_nested)
Every 60 days, top-3 by expanding net Sharpe among 10 pool strategies at default params, equal risk. **HL 1d OOS 1.87 / 2.16y
(worst 1.29 = 1 day late; 2× costs 1.34; corr BTC −0.03), bnall 1.16 / 5.4y (DSR 0.63, worst 0.98).** The pre-registered test passed
(HL > 0.8, worst > 0), so the blend's HL number is NOT mainly hindsight. The rule picks listing_short+tsmom+lowvol on HL and carry+carry_trend+xsmom
on bnall. Fails DSR only. Caveat: listing_short leads; its HL funding is known for 35% of short exposure overall (92% in 2026).
### T9 passive (maker) execution for the daily books (2026-11-10, exec_study r1+r2, config-level) → DEAD as a general fix
Model: limit at the decision close, filled on a 5 bp trade-through within 4 h (hourly OHLC). (r1) taker fallback: BN-82 costs UP ~20%
(unfilled orders chase ~150 bp of drift). (r2) post-only, skip unfilled: costs −65–80% on both venues, but BN-82 6y Sharpe falls
(tsmom 0.88→0.83, xsmom 0.65→0.58, xsmom_k 0.51→0.46; 20 bp trade-through 0.44/−0.01). By year, post-only gained only in 2025–26,
which is why HL's 7-month window looks good (tsmom 1.76→1.93, flow-on-HL 1.59→1.72). Fails the pre-registered rule. Revisit only
for non-directional books (fspread) or once HL 1h history (kept nightly; HL serves only 5000 bars) covers ≥ 18 months.
### fspread_hold: funding capture with hysteresis (X1b, 2026-11-10) → ALIVE (candidate; needs a two-venue book, X2)
New angle vs X1: fixed 10% legs, open at |14d mean HL−BN spread| > enter, HOLD until it flips. **pair 1d WF OOS 1.26 / 1.66y (cagr 8.4%,
mdd −1.7%), grid med 2.22, 6/6 >0, worst 1.43 (2× costs), corr BTC −0.03.** Turnover 10–50× (X1: 70–410×): funding +3–10%/yr vs costs
1–4%/yr. 40–52 pairs, top coin ≈ 20% of P&L, every year +; short the HL leg 95% of pair-days (HL longs pay). ~⅓ of P&L is premium
convergence (price legs), not funding. Fails DSR (0.006: 1.66 y, fat tails). Not modelled: margin split across two venues (≈2× per venue). Daily basis risk small (worst pair-day −0.41%, max basis 95 bp).
**X1c margin (2026-11-12, descriptive, research/studies/x1c_pair_margin.py): the −1.7% mdd assumes ONE margin account; real money
sits in two.** At gross 2.0 each venue account is 2× one-directional (HL ≈ all short alts): worst account P&L without transfers
HL −37% (1 d) / −68% (3 d) / −86% (7 d), BN −50% / −68% / −73%; worst single held HL leg +384% in 7 d (TNSR). Basis itself is calm
(worst daily change 351 bp, p99 29 bp). Verdict for deployment: total gross ≤ 1.0 (≈1× per venue) + daily collateral re-split, ≈ 4%/yr.
Paper book stays at 2.0 (signal measurement). Live since 2026-11-12 (8 pairs, all short HL / long BN).
**X1d two-account sim (2026-11-12, pre-registered rule, descriptive, research/studies/x1d_pair_accounts.py):** both legs at their
adverse intraday extreme, maintenance 5/10%. Gross 2.0 is liquidated 1–2× (2025-10-10 cascade: BN long legs −45…−81% intraday,
account −133%); gross 1.0 and 0.5: 0 liquidations, min buffer 5.6× / 14× (weekly re-split, 10% mm), but a −67…−72% intraday account
day. **Deployable size = gross 1.0 ≈ +4.8%/yr before costs (~$40/yr on $1,000).** Not modelled: ADL closing the winning leg mid-crash.

### L1 hourly horizon: Binance → HL lead-lag and 1h reversal (library N4; descriptive kill test, no backtest, 2026-11-10) → DEAD at taker costs
45 coins on both venues, 4,821 hours (2026-04-14 → 10-31), HL names > $5M/day. Rank IC with HL's next-hour return: Binance return
this hour −0.038 (t −8.7), HL's own −0.039 (t −8.8), "HL lagged Binance this hour" +0.031 (t +7.9), HL last 4h −0.043. Top-minus-bottom
fifth, next hour: −3 / −3 / +5.4 / −2 bp. Statistically real, economically 5–10× smaller than the ~25–40 bp a taker long-short
switch costs; part is bid-ask bounce and stale last-trade closes. Harvesting it means near-free passive fills = market making
(T9: adverse selection; paper cannot validate queue position). Slow horizons stay the right place for this system.

### Minute-bar ideas from the library: flow, absorption, sweeps, BTC leader-lag, breadth, activity spikes, extreme-move fades (event study, 2026-11-10) → DEAD at taker costs
20 liquid Binance perps, 1-min bars, 2026-05 → 10 (263,520 min), rules fixed before download, two halves must agree with |t| > 3 and
clear 15 bp (round trip ≈ 12 bp). Nothing does. Largest signed forward returns: fade a 4-sigma 5-min move +6.7 bp @15 min in half 1,
−0.5 in half 2; volume-spike reversal −9.3 / +0.4; close beyond the 4h high reverses −1 to −6 bp (t −8) in half 1, ≈ 0 in half 2;
flow continuation and BTC → alts ≤ 2 bp. Only one sign is stable: breakouts of the 4h range give a little back within minutes (< 2 bp).
Not tested: order-book imbalance (needs the L2 stream, W1) and thin coins (bigger moves, bigger costs). research/minute_study.json.

> **InSilico rules (2026-11-11/12).** One discretionary trader's public posts (BitMEX/Bybit era) mined into 32 falsifiable rules:
> research/insilico_rules.md (definitions, sources, data map). Five were pre-registered (batch 2026-11-11-insilico.json) and tested on
> Binance with Binance VIP0 costs (taker 5 bp + slippage, maker 2 bp); intraday ones in the order engine kripto/events.py.

### weekend_revert: fade the weekend move back to Friday's CME close (InSilico R21, bn 1h BTC+ETH, 2026-11-11) → DEAD (see second pass: three fade formulations)
WF OOS −0.46 / 6.2y, grid med −0.43, 0/6 >0, worst −0.42. Negative BEFORE costs in both eras (to 2022 −0.31, 2023+ −0.41); only 2021,
the year the author wrote it, was positive (+20–56%). Price touches Friday's level by Monday's close in just 42% of ≥1% gaps. Since 2023
BTC weekend moves CONTINUE into Monday (fade −88 bp/trade, t −3.4, n=128; ETH −10, n.s.): seen after the fact on one coin, not a strategy.

### range_retest: bid the old range high after a breakout, target one average candle (InSilico R19, bnm 1m, 10 coins, 2026-11-11) → DEAD (three forms: trade-through fills below; the touch itself is followed by ±1 bp; at profile levels real = placebo, second pass)
WF OOS −34, 0/8 >0. 91,782 trades: 57.5% winners, gross −1.9 bp, cost 5.9 bp, net −7.8 bp per trade, the same in both eras and all coins.
84% of breakouts do come back to the level, but the candle after the touch closes ±1 bp from it and reaches +1 ATR only 23–26% of the
time. With trade-through fills the bid is hit when price is going through. A touch-fill version would be unverifiable on paper.

### lshock: liquidation fade on 1-minute bars (InSilico R5, bnm 1m, 2026-11-11/12) → OPEN (tail-event effect; not a candidate)
WF OOS 0.64 / 5.2y (grid med −0.005, 4/8 >0, worst 0.56): FAILS the pre-registered rule. The literal rule (6σ dump on ≥5× volume, then a
full engulfing up-bar on less volume) made +70 bp net/trade on the 10 test coins (n=302) and, frozen, **+84 bp on 20 unseen coins** (n=428,
t 2.35, both eras +: pre-registered replication passed). Short side ≈ 0, maker entry no better, costs irrelevant (11 of 90 bp gross).
BUT 3 crash days = 72% of P&L; day-clustered t 1.6; days with one trade lose (−4 bp), cascade days (≥5 coins) make +155–413 bp.
It is a bet on catching 2–4 market-wide liquidation days a year, exactly when real fills and venue uptime are worst (2025-10-10).

### Calendar claims (InSilico R22–R24, descriptive, BTC+ETH 1h 2020–26, 2026-11-11) → nothing tradable at taker costs
Friday after the US close (R22): +7–19 bp/4h, t ≤ 1.5, no different from Mon–Thu. CME break hour 17–18 New York (R23): no extra
volatility, but a drift of +5–9 bp/h, t 2.3–3.6 in BOTH eras on both coins; below a taker round trip (≈ 13 bp). Use: timing of buys
the books make anyway (backlog E2), not a book. September / Santa / lunar claims: ≤ 6 observations each, untestable.

### tsize_capit: daily trade-size capitulation, all size buckets net negative → long (InSilico R1, bnts 1d BTC/ETH/SOL, 2026-11-12) → DEAD on Binance (see second pass)
WF OOS 0.18 / 6.2y (grid med 0.58, 12/12 >0, worst 0.47), but the grid is long-only crypto: holding the three coins is 0.96. Chosen config
(12 bins, hold 1d): to 2022 +1.25, **2023+ +0.24**; 2021 alone made +138%. Forward returns after all-negative days never beat all days with
t > 2 in both eras; with the author's 7 buckets "all negative" is 17–30% of days on Binance and BTC did WORSE after them (−84 bp/3d to 2022).
The claimed asymmetry is real the other way: all-POSITIVE days are followed by gains (BTC +68 bp/3d excess; shorting them −0.94) = flow
continuation, already traded as `flow`. Binance USDT-M ≠ BitMEX (author: "exchange sensitive"); HL version waits for `tsz` data (TSZ-HL).

### mousetrap: failed break of the range low, small trades sold / large bought (InSilico R4, bnts 5m BTC/ETH/SOL, 2026-11-12) → DEAD (see second pass: three formulations)
WF OOS −2.92 / 5.2y, 0/12 >0. Chosen (8h low, 2× volume): 916 trades, 22% winners, gross −3.5 bp, cost 13 bp, net −16.5 bp (t −4.4), same
in both eras. Without the size condition (control): 12,240 trades, gross −1.2 bp: the small/large split adds nothing. Shorts mirror: −2.4 bp.
Agrees with the 11-10 minute study (sweeps of the 4h range: ≈ 0). Not tested: range bars and resting-order absorption (need ticks / L2).

> **InSilico second pass (2026-11-15, research/insilico_pass2.md).** Think-through per family, ≥ 3 formulations each, explored on
> 2021–23 / 10 coins (studies research/studies/is2_*.py), confirmed on 2024–26 and on unseen coins (batch 2026-11-15-insilico-pass2.json).
> The entries below supersede the first-pass verdicts above where they overlap.

### Profile / auction levels: prior POC, value area, single prints, 80% rule (InSilico R15–R17, 2026-11-15) → DEAD as mechanical level rules; R14 relabelled OPEN 2026-11-22
**Correction 11-22:** the header said R14–R17, but R14's own test (P4 gap fill) and P5 (levels as a filter for the slow books) were planned and have no code; R17 = 1 of his 10 laws. → IS3
Three formulations, each failing on the exploration sample AND three held-out samples (10 coins 2024–26, 20 unseen coins 2021–26):
(1) single-print bands fill 48–49% vs 51–52% for placebo bands; (2) first touch of yesterday's POC / VAH / VAL reacts like a fake level;
(3) 80% rule: far edge reached 26–30% vs 37% for a random walk with the same geometry (t −8 to −11). **Correction 11-24 (IS3 P2d):** that test counted unresolved trades as misses against unconditional odds; resolved-only, the daily form is 37.2% vs 38.9% (−1.7 pp, p .20), sessions 47.6 vs 49.5%: a random walk, not worse. Verdict (no edge) unchanged. Reason: any level a move reaches
reacts the same. Real but useless: +4–5 bp more bounce in the 30 min after a real band is filled (was +10 bp in 2021–23, +2 since 2024).

### Trade-size buckets as capitulation / exhaustion (InSilico R1–R2, 2026-11-15) → DEAD on Binance; OPEN (weak) on the author's venue type; R3 relabelled OPEN 2026-11-22
**Correction 11-22:** R3 is a RANGE-BAR rule. T4 was planned on 0.4% move bars and run on 5-minute time bars; T6 (breadth as a feature inside `flow`) was run only as an event table. → IS3
Binance, five formulations beyond the first-pass sign rule, all with the OPPOSITE sign: abnormal one-voiced selling on big down days (next
3 d −235 bp vs +26), total-delta extreme, the same in an uptrend, large-sell/small-buy, intraday "top signal" at a 1-day high (price rose).
Reason: one-voiced flow continues (what `flow` trades). Bybit inverse BTCUSD, his literal rule: fires on 4.5% of days (Binance 17–30%);
next 3 d +130 bp vs +54 (excess +77 bp, t 1.6, n=92, 2019-10..2025-08), positive in his era and after it, never significant. Watch: HL `tsz`.

### One-voiced buying at a 1-day high continues (opposite of R3; BTC/ETH/SOL 5-min, 2026-11-15) → real, below costs (a feature, not a book)
Held-out 2024–26: +6.4 bp over 1 h vs −0.9 for other bars at the high (t 4.7), +15 vs +3 bp over 24 h; exploration +9 / +29 bp (1 h / 4 h).
Use, if any: confirmation for entries the slow books already make. Not worth a book at 13 bp per round trip.

### Mousetrap at real levels (InSilico R4, second and third formulation, 2026-11-15) → DEAD
Failed break of yesterday's low → long: +10.8 bp / 1 h, +34 bp / 24 h (2021–23), but placebo levels give +7.8 / +23: not the level. Heavy
volume and the small-sold/large-bought split (n=93) add nothing; failed breaks of the high: nothing. With the first pass (rolling n-bar
low, with and without the size split) that is three formulations; reason: reclaiming ANY broken low is followed by the generic dip bounce.

### lshock, second pass (InSilico R5, 2026-11-15) → OPEN (tail-event; unchanged verdict, better understood)
**Correction 11-22:** of L1–L6 only L1 (+ a z dose-response) has code. L2 premium, L3 cascade-only, L4 wait-for-end, L5 risk filter, L6 pessimistic fills were NOT run; E1's live book was never started. → IS3
Dose-response on 2021–23 is monotonic (z=4 +6 bp, 5 +28, 6 +70, 8 +150, 10 +194 net per trade; short side negative; half engulf ≈ 0): what
forced selling predicts. But held-out, z=8: original coins 2024–26 +219 bp of which −3 bp without the three best days; 20 unseen coins +188 bp,
+30 without them, days with 1–2 triggers −6 bp. Open-interest split fails (5-min OI too coarse, missing in the wildest minutes). The pattern
exists only on 1-minute bars (5-min: 21 trades, negative). **Pre-registered test on 53 unseen coins, z=8: +44.8 bp net (n=387), both periods
and 1–2-trigger days positive, but t on daily sums 1.57 → NOT confirmed.** All 73 never-selected coins, z=8: +91 bp (n=571, 181 days), every year
positive, 64% of trade-days profitable, t 1.9 on daily sums / 2.4 with one vote per day; three days = 73% of P&L, the rest +27 bp. → E1 (live book, z=8).

### spike_high_short: short a new 20-day high made on a volume spike (InSilico R8, bnall + hl 1d, 2026-11-15) → DEAD as a trade (median effect real)
Event study: such coins lag the top-100 by 170 bp (2020–23, t −3.1) and 374 bp (2024–26, t −7.0) over 10 days in log terms; low-volume highs
did not hold (+140 → −8). Strategy: bnall WF OOS −0.44 (0/8 >0, mdd −99%), HL −0.26 (0/8). Reasons: simple-return mean excess only −80 / −4 bp
(right tail), shorts pay funding (−34%/yr, −90%/yr in 2025–26), costs 7%/yr. Hourly, 15-min and 5-min bars: same shape (median −17 to −54 bp,
mean ≈ 0). High-volume new LOWS also keep falling (−143 / −297 bp over 10 d): no capitulation bounce in the cross-section (R6 not supported).

### friday_follow: Friday's move continues into Saturday (opposite of InSilico R21; bn 1h, 2026-11-15) → OPEN (passes the walk-forward; survivorship check before candidate)
Follow each liquid coin's ≥ 2–4% move of the 24 h before Friday 17:00 New York for 24 h. Event study +88 bp (2020–23, t 2.8) and +104 bp
(2024–26, t 2.7); no other weekday does this (Saturday's move reverses). WF bn_1h OOS 1.21 (8/8 >0, worst 1.02); with the clock time traded
as four tranches (12/15/17/20 h) **OOS 1.06, grid med 0.98, 4/4 >0, worst 0.78, $200 0.84, corr BTC −0.03, cagr 20%, mdd −30%; 2021 negative.**
Weak points: the 82 coins are hand-picked survivors; on the full top-100 at the UTC-day cut it is +46 / +47 bp (t 1.0 / 1.5), top-30: nothing. → FF1.
**FF1(a) survivorship check (2026-11-19, pre-registered 11-17, bn100 = all 698 perps ever in the point-in-time top 100, hourly, delisted incl.) → stays
OPEN (weaker than thought), no book.** WF OOS pick 0.78 / 6.1y, **grid avg 0.61**, med 0.47, 4/4 >0, worst 0.43 (2× costs), $200 −0.11, DSR 0.30; rule
needed min(pick, avg) > 0.8. Decomposition (research/studies/ff1_decomp.py): +42 bp gross per Friday (t 2.7; top-3 weeks 25%), costs ≈ 11 bp/week
(turnover 82×); the P&L is the long leg of the hand-picked 82 (+1.11 of +1.55); coins outside them +14 bp/week 2020–23 and **+0.8 bp 2024–26**; 2026 −13%.
Diagnosis: on survivors "follow the move" is partly "be long what later survived". Untried: market-relative move (excess over the universe), shorts only.

### Weekend fades, second pass (InSilico R21, 82 coins 1h, 2026-11-15) → gap fade DEAD; Sunday-move fade OPEN
Fading the Friday→Sunday gap: −8 / +33 bp (n.s.), with the first pass's six walk-forward configs that form is dead; fading Friday's own move
loses (−88 / −104 bp: it continues, see friday_follow). Fading the Sunday 12:00→18:00 New York move for 24 h: +20 bp (t 1.1) / +105 bp (t 2.6),
positive in both samples but not pre-registered: one confirmation on new coins before it counts.
**W3 replication (2026-11-19, pre-registered rule, research/studies/w3_sunday_fade.py) → CONFIRMED; OPEN pending its walk-forward.** 616 bn100 coins NOT in the
82, point-in-time top 100: +61.9 bp per event in SIMPLE returns (median +51.5, n 9,398, 343 Sundays, t 2.32 on event-day means), ≤ 2023 +28 bp (t 1.2),
≥ 2024 +88 bp (t 2.3), every year + (2023 only +8). Plumbing check reproduces 11-15 on the 82 (+19.7 / +106 bp log). Caveats: most of it may be a
market-wide Sunday fade (one bet per Sunday, ≈ 50 a year), fades of down moves are skewed (mean 77, median 33 bp). Next: pre-registered WF (backlog W3).

### Unit-price bias (InSilico R28, bnall top-100, 2026-11-15) → DEAD (an alt-season effect)
Cheapest fifth by price per unit vs the universe: +52 bp/week in 2020–23 (t 2.1), −52 bp/week in 2024–26 (t −1.3); vs the dearest fifth
+59 → −200 bp/week (t −3.4); alt-season-only +71 → −47. Three formulations, reversed out of sample: it was the 2021 alt season.

### US-session momentum (InSilico R24, 30 coins 1-min, 2026-11-15) → DEAD (a bull-phase effect)
After a US-session (13:30–19:15 UTC) up-move ≥ 1.5%: +102 bp excess over 72 h in 2021–23 (t 2.1), then −6 bp on the same coins in 2024–26 and
+26 / +71 bp on unseen coins, with 2025 −105 to −178 and 2026 −57 to −106. Three variants (plain, with a single-print band, ≥ 3%) fail held-out.

### Empty moves get refilled (InSilico R9, 10 coins 1-min, 2026-11-15) → OPEN (two forms failed, low prior)
Fading a 4-sigma 5-minute move made on < 1.5× usual volume: +66 bp at 15 min in 2021–23 (n=342, t 1.4), +3.6 bp in 2024–26 (n=444).
With the 11-10 minute study (fade any 4-sigma move: unstable) two formulations; not tested: thin-book measure from L2 instead of volume.

### Stock / commodity perps in `bnall` (2026-11-22 retro, assumptions row 19) → data error fixed; Binance numbers with 2026 in the sample were flattered
Binance lists 246 TRADIFI perps since 2026Q1; live drops them (contractType), bnall/bn100 did not: 46% of the bnall top-30 by volume in 2026Q3 was AAPL, AMD, ….
Fixed: config/bn_tradfi.json, bars cut at the onboarding day. Same configs, to 10-31, full sample old → clean: xsmom_k 1.23→1.20, flow 1.49→1.43, tsmom 0.92→0.95,
xsmom 1.34→1.31, blend 1.19→1.18, listing_short 0.42→0.33; **2026 only: flow 0.90→0.45, listing_short +0.36→−0.30, xsmom 1.61→1.35**. Walk-forwards not yet re-run → TF1.
Sunday fade replication (W3) re-run on clean bn100: +65 bp (t 2.43), ≤ 2023 +28 (t 1.2), ≥ 2024 +92 (t 2.5): still CONFIRMED by its 11-19 rule. FF1 not re-run (OPEN, low prior).
### Live candidate list = research universe? (2026-11-22, research/studies/live_universe.py; row 19) → yes on both venues
Direct test (recorded live lists on 4 bars 11-17 → 11-22 vs the clean, fully refreshed bnall): live's top-30 contains 29, 30, 30, 30 of the research top-30. HL by proxy 98.8%.
The Binance 24h-volume proxy said 95.1% (2026: 87%) and a bad blend@bn, but it ignores that held coins stay listed; the direct number wins. No change to live.
### Live fills vs the decision close (2026-11-22, research/studies/fill_delay.py; row 20) → Binance ≈ 0, HL costs about +5 to +17 bp (t 1.3–2.8, 14 runs): OPEN
Live decides ≈ 12 min after the bar close the backtest trades at. HL notional-weighted +15 bp (alts +17, BTC +6), median run +5–7 bp, +6 without the two largest runs;
Binance +0.4 (t 0.3). Weak, but HL's live "0.9–4.7 bp slippage" measures against the mid at the fill and omits it, so "×0.56" must include a drift term → C1.

### T0a live-vs-backtest tracking: 10 single-entry shadow books, 7–8 live days (scripts/live_vs_backtest.py, 2026-11-17) → live = backtest on HL
HL books track their replay almost exactly: daily corr 0.99–1.00, tracking error 5–21 bp/day, turnover equal (tsmom 1.06 vs 1.09), position
corr 0.88–0.98, cumulative tsmom +8.32% vs +8.25%. Costs: live ≤ model except listing_short (0.20% vs 0.13% of equity: new listings are
thinner than the model thinks; C1). Binance x-sec books: corr 0.68–0.91, TE 80–200 bp/day, explained by the replay's universe, not live:
today's top-volume list contains coins (AGT after its pump) live could not hold then. Fixed: paper.record_universe (point-in-time universe per bar,
from 11-17). Re-run weekly; quote it next to every live number. **No engine bug found.**
### R1 squeeze tail of the Binance x-sec books + LV1(c) high-vol shorts (bnall 1d; explore ≤ 2023-06, confirm 2023-07+; 2026-11-17) → small fix adopted
Leg sums (explore, before funding): alt shorts lose (xsmom −0.59 vs longs +1.83; flow −0.70 vs +2.35); the worst 1% short coin-days (WAVES, FTT,
DOGE 2021…) cost more than the other 99% earn. But removing alt shorts collapses the books (SR 1.23 → 0.33, mdd −23 → −41%): **they hedge the alt
factor; a leg's P&L sum is not its value.** No-short filters fail on explore (r7 top-20% 7-d risers, liq less-liquid half: lower SR); high-vol shorts are
NOT the losers (median +31–39 bp), so **LV1(c) is answered: no**. Symmetric 5% per-name cap after vol targeting (pre-registered, research/batches/
2026-11-17_r1.json): confirm xsmom 1.61 vs 1.69 (mdd −14.4 vs −16.0), flow 1.24 vs 1.19 (−21.2 vs −21.8), xsmom_k 1.23 vs 1.37 → 2/3 pass → `cap: 0.05`
on xsmom@bn, flow@bn, xsmom_k@bn. A risk limit, not edge. Untried: intraday stop via the live watcher (hourly data needed).
### T2b(e) listing_short liquidity hysteresis (cost fix after live XTEN churn; fixed configs, tag t2be, 2026-11-19) → rejected (pre-registered rule failed on HL)
Enter at 7-d dv ≥ $1M, stay while ≥ $0.5M (B) vs one threshold (A). Explore bnall ≤ 2023-06: re-entries 7.1% → 3.0%, SR 0.44 → 0.45. Confirm: bnall 2023-07+
SR 0.38 → 0.37, cost 1.37 → 1.22%/yr; **HL: re-entries 43% of events (!), cost 3.68 → 2.88%/yr, but SR 1.45 → 1.37, mdd −28.6 → −31.8% → FAIL.** On HL the
low-volume exit is also a squeeze filter (thin dying coins, volume returning on pumps). Entry floor 2× loses signal. Re-check the same rule after C1
(threshold names cost ≈ 3× the model live). research/studies/t2b_hyst.py.

### InSilico T1 resting bids 30 σ below the last price, causal top-20 coins, exit 60 min (2026-11-22, is3_ladtop.py) → CONFIRMED by card, not yet a book
Explore 2021–23 +187 bp/fill (n 644, 215 d, every year +), pre-registered 2024–25 +259 (n 356, p .001, two lottery fills 35% of it), 2026 vault once +203 (n 142, p .006, ex-top3 +150).
Account 10% × 5 slots: SR 2.3 / 1.9 / 2.8, cagr 35–38%, worst booked day −8%; 5% size halves everything. Any-coin version refuted (60 fresh coins +13 bp), so the narrowing to liquid coins was post hoc before the vault.
Not yet real: entry at max(limit, minute close) +115 / +150 / +84 (2026 p .18), so the edge is the resting fill; 2025-10-10 marks −34% inside the hour at 10% size (booked −8%). Stops, calm filters and "don't quote when BTC falls" all make it worse
(the cascade is what pays). Needs: live resting-order paper with real queue and outage behaviour, walk-forward, costs ×2 (E2).
E2a 2026-11-23 (is3_e2.py, registered WF `ladder`/bntop20_1m): 18 configs k20–40 × hold 15–240 × slots 5/10, 5%/order, PERCENT_PRICE band: OOS SR 1.94, +14.7%/yr, booked mdd −6%, DSR .98, every year +; all 18 positive but the pick < grid avg 2.19, so trade the FROZEN k30 h60 (2.14; 2× cost 2.04; one bar late 2.14; $200 2.16). Incubation-eligible on Binance; the live resting-order book (E2b) is the missing proof.
E2b 2026-11-23: live paper book running (kripto/ladder.py, kripto-ladder.service): shadow:ladder@bn $2,000 + small $200, candidate, one-bar-late quotes, fills only 30 bp through on later minutes. Not in main_bn until live fills match the backtest (~5 fills/week, ~116 bp/fill gross one-bar-late).
E2c/d 2026-11-23 (is3_e2risk.py, is3_e2d.py): minute-low mark worst −17% of equity at 5%/order (2025-10-10, 2024-01-03) vs booked worst day −4.6%; daily loss caps change nothing (loss lands in one batch minute); exits 3 h late on cascade days do not hurt. Not short insurance: +11% in the main_bn mix's 20 worst weeks, weekly corr −0.12. Live size cut to 2.9% (pre-set: −50% on the largest batch, 17 fills, must stay above the 25% kill); BTC no longer fills in the $2,000 shadow.

### InSilico S1: sources re-read against the rules as coded (2026-11-22) → no verdict, but several older DEADs were verdicts on my translation
Read: 374 chat records (image descriptions; 8 images opened by eye), 2 guides, 46 templates, rule pages of 3 PDFs. 11 rules had been flattened: R3 (thin fast bar, not the sign of 7 groups), R4 (two tests),
R14 (valley between two humps), R19 (second target), R1 (magnitude), R7 (location), R18, R23, R24, Hull, R30. 33 new queue forms, 11 forms reworded; those rules are not settled until they run.
New data: 107 hand-drawn levels of 2020-06..10 (4 coins, plus one 2021) have creation timestamps inside the templates, i.e. a dated record without hindsight (authorship unproven) → queue T2e.

### InSilico S2: every picture and video opened by eye (2026-11-23/24) → no verdict, the stored descriptions hold
253 images (4 unreadable low-res scrolls), 21 video sheets + tape keyframes + 13 transcripts, 140 truncated cited records finished, PDF remainders scanned (keyword greps, not line by line). 0 contradictions with the
stored descriptions, so forms built from them stand. The pictures still added things the text lacked: his size groups are recomputed from the PREVIOUS DAY (M4a), exhaustion = market orders getting smaller and rarer (M2f),
mousetrap entry = first bar where buyers take over at the level (M3e), Friday pump after the US cash close (C2g), hourly 'salad' profile (P1g). Two claims need data we do not collect yet: book pulls/lifts (backlog W2) and single big liquidations (L1p).

### InSilico T2: forensics of his own dated examples (2026-11-24) → OPEN (nothing beyond 'big down day' / 'a line near price'; underpowered)
His capitulation days (M4e) are ordinary >= -3% down days: 'all trade-size buckets negative' happens on 54% of them and changes nothing (next 3 d +0.51% vs +0.55%). 56 unseen analogs: +79 bp vs matched
+74 (MDE 353). His 85 dated 2020–21 levels: after the first touch price goes THROUGH them more than through distance-matched placebo lines (60 min −18 vs +11 bp, p .03) and they are not touched more often.
Consequence: M4a now scores the size of the negative bucket shares, not the sign. If his edge is real it is in what candles don't show (book: backlog W2) or in his discretion. research/is3/T2*__*.json, studies/is3_t2*.py.

### InSilico T3: context model / spring strength after a liquidation climax (2026-11-24) → DEAD (4 forms; explore COINS10 2021–23, 63k climaxes)
tg:167 'the initial mechanical spring tells how strong the bounce will be': no. Fade return by spring decile is flat (+7..+13 bp at 60 min) and turns negative when > 54% is already retraced (−11 bp vs matched, p .02,
MDE 12.5): a strong spring = bounce used up. A weak spring does not predict continuation (−1 bp vs matched). Ridge on 22 features: OOS IC +0.075 (t 3.2; shuffle −0.003) but = 'fade dumps, ride pumps' (−7.5 bp vs that
rule); sizing by prediction = sizing by volatility. All below taker cost. Untried: tree models (not installed). Lesson: always test a model against the simplest rule it could be rediscovering, not only against a shuffle.

### InSilico T4: exits as decisions instead of a timer, on the live ladder fills (2026-11-24) → OPEN by the MDE rule, practically: keep the timer
Explore 2021–23, 1,147 one-bar-late T1k30 fills, baseline = market 61 min after the fill (+148 bp): leave when the bounce stalls −94 bp (p < .001), the same after 15 min −63 (p .007), on the first new down-climax −85
(p < .001), quick exit only on lone fills −3 (p .06). The bounce lasts hours; "take it and run" cuts it. Hindsight best close +385 bp, so exits matter, just not these. Live ladder unchanged.

### InSilico T5: 1-min bounces and continuations by context (2026-11-24) → OPEN (one live idea: up-spike continuation)
Explore COINS10 2021–23: 116k ordinary >= 3σ minutes fade +2 bp/60 min; level, round number, trend, breadth, taker share, trade size, BTC residual move it < 5 bp (MDE ~5). Effort without result (high volume, small
range) +2 bp vs +18 for large-range bars: claim reversed. OI split of 1-h moves: puke falls bounce like any fall; OI-up falls continue only in 2022; NL/NS trapped cells too rare at 1 h (MDE > 200).
Up-spike >= 8σ, breadth >= 2, long 60 min: explore +27 vs −2 (p .002), confirmC +47 vs 0 (73 coins, p .009), confirmT +37 vs +3 (p .075, MDE 59): not CONFIRMED; median +2..7 bp, top-3 days 44–74%. Vault untouched.
Use: don't rest asks against broad up-spikes (ladder feature idea). Scripts research/studies/is3_t5{a,d,e,f,g}.py.

### InSilico P1 / R14 gap fill (2026-11-24) → DEAD (the reverse holds: volume memory)
Explore COINS10 2021–23, profiles from 1-min klines in 10-bp bins, placebo = the same bins mirrored around the next open. Next-day volume in yesterday's thin third −0.86 pp, busy third +2.5 pp (every year;
hourly −0.43 / +1.24 pp); thinnest tenth most avoided. Bimodal valley (his picture) +0.6 pp p .29; nearest LVN reached first 49–50% (random walk 50); delta gaps = volume effect once volume is controlled;
LVNs approached ≥ 3 times and not filled: price drifts toward, not away (n 198, p .3, MDE 85 bp). Scripts research/studies/is3_p1.py, is3_p1cg.py. Possible FEATURE only: busy zones are where tomorrow trades.

### InSilico P2 / R16–R18, R41, R42 balance laws and session profiles (2026-11-24) → DEAD (12 forms)
Explore COINS10 2021–23, every level vs a placebo (same construction 8 days earlier moved to today's price, or same distance). 3-day balance edges reject 43% vs 47% placebo; IB edges 48 vs 52%; 4-bp single prints
fill 48 vs 51%; naked POCs reached 48.5 vs 53% (p .02); poor lows = tailed lows (74.6 vs 74.9%); fat-node / deviation breaks = median-level breaks (MDE 20 bp), OI split no help; R/F and TPO-vs-volume POC
gap only echo today's range. 80% rule = random walk (session −2 pp, daily −1.7 pp) once unresolved trades are excluded (pass-2 '26–30% vs 37%' was that bias). Scripts research/studies/is3_p2.py.

### InSilico C1 calendar claims incl. the Almanac (2026-11-24) → OPEN by the MDE rule, practically nothing
Explore 2021–23, BTC + EW top-30 daily vs other days; FOMC/CPI dates from federalreserve.gov / bls.gov. 0 of 176 cells (weekday, turn of month, hour of week) survive 10% FDR. Underpowered positives: FOMC day before / day
+122 / +218 bp (MDE 173 / 325), first day of month +127 (MDE 176), turn of month +62 (MDE 83). Lunar waxing−waning −780 bp then +413 in 2024–25 (noise). Down Fri/down Mon → bounce, not decline. Tax-loss lows:
2 usable Decembers, both worse. Expiry weeks, equinox, September, Santa, May–Oct, triple witching: nothing. Script research/studies/is3_c1.py.

### InSilico C2 time of day: kill zones, filler hours, CME break, illiquid hours (2026-11-24) → kill-zone story dead; Friday 16–20 NY open (→ FF1)
Explore COINS10 2021–23, NY clock with DST, placebo windows of the same geometry. London-zone sign → NY zone −6 bp (no continuation); filler not given back; London collar reached 49% (mirror 50);
illiquid-hour ≥ 2σ moves fade less than liquid ones (−5 vs +12 bp); same half-hour yesterday: 1-bp reversal; Monday US open: nothing. CME 17–18 NY +4.6 bp vs other hours (p .22; 2021 only).
Friday 16–20 NY +26 vs +5 bp Mon–Thu (p .18, MDE 38): test inside FF1. Script research/studies/is3_c2.py.

### InSilico P3 / R15 naked and composite POCs (2026-11-24) → DEAD
Explore COINS10 2021–23, mirror levels as placebo. Naked daily POCs touched within 5 d 54.8% vs 57.6% mirror; weekly = mirror; monthly −9 pp. 20-d composite POC no magnet vs the 20-d mean. First touch of a daily
naked POC +15 bp/60 min vs −1 for mirror touches matched on approach side and distance (p .09, MDE 18.5); larger for far, old and THIN nodes (fat nodes ≈ 0) = generic bounce. Weekly/monthly VAH/VAL 'reactions'
were an approach-side artifact. Lesson: compare level touches within the same approach side. Script research/studies/is3_p3.py.

### InSilico O1 / R29 oscillators: pinned extremes mean trend (2026-11-24) → DEAD
Explore 2021–23, COINS10 1h/4h + bnall top-100 1d, baseline = same coin at the same trailing-14-bar return decile. RSI > 70 for 1/3/6 bars adds nothing stable (no run-length dose); re-entry dips = matched;
3 failed sell signals precede a DROP at 1h (−58 bp, p .02). RSI back through 50 after > 70 is followed by the trend resuming at 1h/4h/1d (shorts lose, p .03–.06; long card p .18). Ladder filter (fills when
daily RSI ≥ 50): explore +243 vs +68 bp, confirmT 2024–25 +183 vs +137 (p .60) → fails; the gap was 2021. Scripts research/studies/is3_o1.py, is3_o1_card.py.

### InSilico O2 / R30 the author's own indicators (2026-11-24) → DEAD
Explore 2021–23, COINS10 1h/4h + bnall top-100 1d, baseline = same coin at the same trailing-14-bar return decile, ~70 cells. VZO (signed volume) alert ends are followed by MORE of the same flow; invalidated
exhaustion bars lose at 1h; Leledc, MACD-cross fade, VZO midline/veto, camarilla (= placebo pivots), regression channel (= placebo widths), sham-pump fade: nothing; 1-min Fisher turns 0–3 bp gross. Hull55+180 at 1h
+17 bp/6 h (p .03, absent at 4h/1d). Crayons H (failed new high in an uptrend): less upside than ordinary uptrend bars (+28 bp/6 h, p .003) but shorting it loses → F2 feature idea. Crayons climax: no formula published.

### InSilico N1 / R26 round numbers, 'hundy roll' (2026-11-24) → DEAD
Explore 2021–23, one-significant-digit levels vs placebo levels 37% of the way to the next. +6% before −3% from 2–3% below a round level in an up move: 35.0% vs 31.8% placebo (random walk 33%, p .18);
first daily close 1–2% beyond → back within 5 d 93 vs 92%; 1-min first-touch reaction −21 bp vs placebo (p .06: run through, not defended). Script research/studies/is3_n1.py.

### InSilico N3 tape behaviour (2026-11-24) → OPEN as features only; absorption dead after confirms
Explore 2021–23. Absorption (3-day taker-imbalance z ≤ −2 while price holds, long 5 d): explore +146 bp vs matched (dose monotone) → confirmT −72, confirmC +47 (p .27): fails (2021–22 regime). Shrinking zigzag
swings (1h): counter-trade +4 vs −10 bp after strong swings (p .002) — a 'trend tiring' feature like O2 j, not a trade. Nothing: buyer-streak fade, shakeout reclaim, delta flip (rare), HTF filter (no difference, as
he says), painted hour closes, non-overlap impulses (anti-dose in efficiency), change-of-character bar, AVWAP distance and his 90-day AVWAP anchors (= random anchors). Scripts research/studies/is3_n3*.py.

### InSilico N4 / R32–R33 lead-lag, decoupling canary, crash asymmetry (2026-11-24) → DEAD (asymmetry true)
Explore 2021–23, 107 coins, 5-min baskets by volume tercile: no lead in either direction beyond a 1-bar bounce (corr −0.02..−0.04); alt-BTC correlation drops do not precede larger BTC days; thin-minus-BTC
divergence predicts BTC the other way (−22 bp/day, p .03). 1-min down/up tail ratio 1.2–2.0 at 8–12σ, rising each year (dumps sharper than pumps) = the ladder's raw material. Script research/studies/is3_n4.py.

### InSilico M1 / R3 rotation momentum on move bars (2026-11-24) → DEAD
BTC/ETH/SOL 2021–23 aggTrades move bars (.2/.43/.8%), author7 and previous-day-quantile size groups. Riding an all-green run to the first all-red bar: +2 bp vs bars of the same coin-day, side and
prior up-run (p < .01, MDE 1–2 bp) = 1/7 of a taker round trip, worse with longer runs. All-red bar at a 24 h/7 d high: no better short than any bar at the high. His thin-fast boxed bar: −6 bp vs matched.
Top-|delta share| bars "reverse" −22 bp/1 h, but 94–100% are sub-1-s torn-book bars; 5-min late entry: +3 vs matched (p .63). Lesson: on range bars, match within day AND on the prior price path (null failed twice before that). Scripts is3_m1*.py.

### InSilico N2 / R13 spot delta vs perp delta (2026-11-24) → OPEN (general claim dead; his narrow case underpowered)
Binance spot 1h archives (30 coins) vs perp taker flow, daily, explore 2021–23. Spot-led rallies (spot-minus-perp imbalance z, top quintile) = same coin same-size rallies (−17 bp/3 d, p .70); as a
cross-sectional rank −6 bp/1 d (MDE 19); spot agreement adds +1 bp to perp flow momentum (perp flow, not spot, carries the information). His case (rally + perp selling + spot buying, + rich funding as the
carry condition) +62 bp/1 d vs matched, every explore year +, p .22, n=179 (MDE 132); 3 d flips in 2022–23. Not pre-registered. Reopen only with spot for ~100 coins. Lesson: a sign-flip null on any long-only
daily rule earns +σ²/2 (≈ +57 bp/3 d here) by convexity; run the null on event minus matched. Script research/studies/is3_n2.py.

### InSilico M2 / R7 order velocity ×10 (2026-11-24) → OPEN (rule dead; survivor = crash-day liquidation fade)
BTC/ETH/SOL aggTrades range bars 0.1/0.2/0.43% + COINS10 1-min, explore 2021–23. 5–20× changes in trades per bar are the norm at his 0.1% size on Binance (63% of SOL 2021 bars); no reversal or
continuation vs within-day matched from 5 min late (MDE 2–11 bp); count drops are sub-1-s torn-book bars. Engine-lag proxy (clogged bursts continue) and exhaustion row (fading activity) both backwards and
tiny. Survivor: ≥10× burst on a slow down bar at the 24 h low, long 5 min late for 60 min: +50 bp vs matched explore (n=600), pre-registered, confirmT +65 (p .047) but ex-top-3-days +12 < taker, 85% of it
2025-10-10 / 2025-02-03 / 2024-04-13 → the liquidation fade (L1/E1), FAILED as a separate edge. Scripts is3_m2.py, is3_m2m.py.

### InSilico M3 / R4 R10 R12 R35 mousetrap, absorption, trapped cohorts (2026-11-24) → DEAD
BTC/ETH/SOL aggTrades range bars 0.2/0.43%, explore 2021–23, entries 5 min late, ≥ 1-s bars. Mousetrap at the prev-day low with a volume surge on the second test = near-level placebo (−13 bp/240 min,
MDE 43, anti-dose); his small-sell/large-buy split is rare (44) and negative; absorption bars (takers against the bar) = within-day matched (MDE 11; the +71 bp tail is 2021-05-19 / thin-SOL wicks);
trapped small sellers below a reclaimed level: no dose (MDE 51), but LARGE sellers below it were right (weaker rebound every year); volume at a bar's extreme → slight continuation. Script is3_m3.py.

### InSilico F0 filter harness + F1 filters on flow / xsmom (2026-11-24) → harness built; F1 closed OPEN (nothing usable)
research/studies/is3_filter.py: a filter is judged against 200 random masks with the same on-share and persistence (a random 80% mask alone cut flow's mdd −23.5% → −16.4%, 87th pct: not a pass).
bnall 1d, explore 2021–23. R8 backwards: blocking longs at volume-spike 20-day highs costs 0.5–0.7 SR (volume breakouts are the best longs). RSI-pin filters touch < 2% of weight: nothing.
No shorts for 1 day after a cascade day (median coin ≤ −7%): explore flow 1.58 → 2.14, xsmom 1.19 → 1.62 (≥ 99.5th pct, every year), pre-registered, confirmT 2024–25 FAILED both (−0.25, −0.32): the
next-day bounce after cascades (+61..+291 bp 2020–23) reversed in 2024–25 (−28, −150 bp). Lesson: 'bounce after a flush' held 2021–23 and failed 2024–25 three times (O1, N5, F1g).
F1 a/e/f/h (evening): trade-size breadth, value-area location (3 readings, VA from bn100 1h day profiles), round numbers, poor extremes = random masks or worse. Blocking positions AGAINST
value (long closing below VAL) costs flow 1.3 SR: those are the book's best days because of the plain next-day reversal (standalone: +4 bp vs return-decile matched, MDE 90). is3_f1.py, is3_f1loc.py.

### InSilico M4 / R1 R2 capitulation with adaptive buckets, in a trend, pitstops (2026-11-24) → OPEN (MDE rule only; every form ≤ baseline)
Adaptive 7 size groups (prev-day septiles of 12 bins), BTC/ETH/SOL 2021–23: most-negative quintile +130 bp vs matched (p .34, MDE 314), no dose; his literal picture −151; 4-h bars flat.
R2 on bnall (most one-sided selling day of an uptrend on a pullback): anti-dose. Buying breadth: nothing. Pitstop (red bar at a high → first green bar) on his 0.5% range bars: −38..−45 bp vs green
bars in the same move (p .06). Binance size-bucket footprints read as continuation, not exhaustion. is3_m4*.py.

### InSilico M5 / R19 range -> impulse -> retest on range bars, queue fills, placebo levels (2026-11-25) -> DEAD
BTC/ETH/SOL micro bars 0.2/0.43% range bars + 44 thin coins on 1-min klines (0.5/1%), explore 2021-23, 6 forms. Real level - placebo (0.63x/1.37x distance) -1.5..+0.6 bp (MDE 1-9) for the old range
high, the range's VAH (POC slightly worse), his post-breakout-low target, his average-1-min-candle target (maker or taker exit). Touch fills ~0 gross; the more volume must trade through our bid before
it fills, the worse (q250k -6..-46 bp gross, placebos the same): adverse selection, not levels, sets the result. Strongest-impulse quintile -6 bp vs placebo (his 'unless abnormal pressure').
Confirms range_retest (11-11) with his bar type and a queue model. is3_m5.py.

### InSilico M6 / R33 trend systems on move bars instead of time bars (2026-11-25) -> DEAD
BTC/ETH/SOL micro bars 2021-23, fills as of +1 s, 6 bp/side, baseline = hourly tsmom with the lookback matched to the same flips/yr. Range bars (0.5-2%), trend-reverse and zigzag (0.5-4%):
+1..+8 bp/trade gross, +3..+7 bp more than time bars (p .001-.016), every cell net negative (pooled net SR -0.9 or worse); the gain over time bars vanishes at low turnover, where 1-2 month hourly tsmom beats
P&F (1-2% boxes). Volume bars = time; delta bars worse (intraday delta reverses). Double reversal at a level faded = single swing (-0.1..-0.9 bp), placebo levels worse. Lesson: filling at the deciding
trade itself fabricated 2,070 flips on 2021-02-22 (ms crash prints); intraday move-bar studies need a latency fill. is3_m6.py, is3_m6c.py.
