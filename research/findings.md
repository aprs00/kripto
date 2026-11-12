# Findings ledger

One entry per hypothesis ever tested. Read this before choosing research. Keep each entry ≤ 5 lines.
Verdicts: **ALIVE** (candidate/incubation/active) · **DEAD** (rejected; revisit only with a new angle stated) ·
**OPEN** (inconclusive or blocked on data).
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

### tsmom long-only (2026-11-08) → DEAD
2022 −33%, 2025 −11%: it is BTC beta, not an edge.

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
### xsrev: short-term cross-sectional reversal (2026-11-08, re-run 11-09) → DEAD
HL OOS −2.66, BN −1.81; 0/6 >0 on both. Turnover makes fees dominate.

### lowvol: betting against volatility, beta-hedged (2026-11-08, re-run 11-09) → DEAD
HL −0.24 (1/6 >0); BN OOS 0.44 but grid med −0.01 (3/6 >0). Not robust. Note 2026-11-10: under harness v2 (tranches, band 0.01) the
DEFAULT config is HL full-sample 0.90 (bnall 0.22) and H4's selection rule picks it as an HL blend leg; no new WF run, verdict unchanged.

### funding_contra: fade funding spikes vs own history (2026-11-08, re-run 11-09) → DEAD
HL −0.81 (0/8 >0); BN −0.42 (med 0.15). Not robust.

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
