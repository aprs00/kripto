# Findings ledger

One entry per hypothesis ever tested. Read this before choosing research. Keep each entry ≤ 5 lines.
Verdicts: **ALIVE** (candidate/incubation/active) · **DEAD** (rejected; revisit only with a new angle stated) ·
**OPEN** (inconclusive or blocked on data).
Numbers are walk-forward out-of-sample, net of fees + slippage + funding unless noted. SR = annualised Sharpe.

## Cross-cutting lessons (apply to everything)
* **Verify the plumbing, not just the result.** A unit bug silently voided a whole day of research (2026-11-09). Any
  helper touching timestamps/alignment needs a unit test on synthetic data with a known answer.
* **Costs are the binding constraint on Hyperliquid.** The HL top-20 by volume includes thin memes; slippage +
  fees took ~8%/yr off trend. Any HL strategy must be judged at HL cost levels, not Binance's.
* **$200 + $10 min order ⇒ any position < 5% of equity can't be opened.** Diversified (20–30 name) books can't
  be executed in the main book. Backtests use band 0.05 to mirror this.
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
* **DEAD on HL ≠ dead forever.** HL history grows every day. Re-test DEAD ideas that died on HL alone (not on BN
  too) once HL OOS history has grown by ≥ 6 months, as a pre-registered re-check (see backlog T0b).

## Hypotheses

> 2026-11-09: everything before this date was re-run with the fixed rebalance code (T0, same grids). Registry lines 1–179
> (git ≤ c1e3c1f) are invalid but stay in the registry (append-only); they only make DSR more conservative.
> The re-run numbers were close to the invalid ones (so the bug's backtest effect was smaller than feared).

### tsmom: multi-horizon time-series trend, L/S, vol-targeted (2026-11-08, re-run 11-09) → ALIVE (candidate, shadow)
HL OOS SR 0.43, grid med 0.47 (12/12 >0); BN 1.31 (med 1.02). Concentrated (top 8/12): HL 0.55 / med 0.90 (16/16), BN 1.03
(mdd −55%). bnall 1d OOS 0.97 (med 0.89, 12/12 >0): survivorship inflated BN-82 by ~0.3 but trend holds. Fails HL
gate (> 0.8). Signal is real but weak on HL; costs ≈ 4–5%/yr at top_n 12.

### tsmom long-only (2026-11-08) → DEAD
2022 −33%, 2025 −11%: it is BTC beta, not an edge.

### tsmom signal smoothing (EMA 3/7d) and $20M liquidity floor (T1c, 2026-11-09) → DEAD (smoothing) / weak (floor)
Smoothing halves turnover (63→28/yr) but Sharpe falls more (HL 1.11→0.34, BN 1.00→0.99 at best; lag kills the signal).
$20M/day floor: +0.1–0.5 SR on HL in 3/4 pairs, ≈0 on BN. WF OOS HL 0.57, BN 1.08. Not worth a separate book.

### xsmom: cross-sectional momentum, beta-hedged (2026-11-08, re-run 11-09) → ALIVE (candidate, shadow)
HL OOS 0.42 (med 0.72, 11/12 >0); BN-82 0.55; **bnall 1d OOS 1.27 / 6.1y (med 0.86, 12/12)**, corr BTC ~0. The band
halves it (lb28/3d: 1.16 at band 0.005 vs 0.58 at 0.05): needs breadth, so it isn't executable at $200. Fails HL gate.

### carry: short high funding / long low funding, dollar+beta neutral (2026-11-08, re-run 11-09) → DEAD on HL (re-check ~2027-05)
HL OOS −0.89, grid med −0.34 (2/12 >0); BN 1.06 (med 0.72). On HL high-funding names are squeezes that keep rising.
Concentrated: HL −1.05, BN 0.50. Carry needs breadth and doesn't transfer to HL.

### carry_trend: carry only where trend agrees (T1d, 2026-11-09) → DEAD on HL
HL OOS −0.88, grid med −0.52 (0/6 >0); BN 0.65 (med 0.88, 6/6). Conditioning on trend doesn't rescue HL carry.
Funding +2–3%/yr on HL can't pay ~5–8%/yr costs.

### listing_short: short new perps 1–14d after listing for 30–90d, BTC-beta hedged (T2, 2026-11-09) → ALIVE (candidate, shadow)
HL 1d: WF OOS 0.75 / 2.95y, grid med 1.11 (9/9 >0); cfg(1,60) at band 0.005: SR 1.57, corr BTC −0.06, short leg + every year.
bnall (923 BN perps incl. delisted, 6y): WF OOS 1.08 (9/9 >0) BUT band artifact (corr BTC 0.63); band 0.005 → SR 0.44,
corr 0.06, short leg ≈ 0 absolute (listings lag BTC beta). BN-82: −0.18 (survivors). Fails gate: HL < 0.8, DSR. Real but
modest; HL stronger (more airdrop launches?). Funding known for only 28% of HL short exposure.
### blend: equal-risk tsmom(top12) + xsmom_k + listing_short, 1 pre-registered rule (T4, 2026-11-09) → ALIVE (candidate, shadow; best so far)
HL 1d WF OOS **1.57** / 2.95y (full 1.82; 2× cost 1.54; band 0.005 1.64; corr BTC 0.17; years 2.9/2.2/0.4/1.7). Components'
corr 0.02–0.28 → return-level blend 1.63, so diversification, not a bug. bnall 1.02 / 6.1y but corr BTC 0.51, 2021–22 < 0;
DSR 0.62 < 0.9 → **fails gate** (only clause failed). Caveat: component params chosen after seeing their results → T4b nested re-test.
### xsmom_k: top/bottom-k x-sec momentum, k = 3–5, beta-hedged (T11, 2026-11-09) → ALIVE (candidate, shadow)
1d WF OOS HL 0.55 (med 0.44, 8/8 >0), bnall 1.37 (med 0.89, 8/8, DSR 0.87). Executable at $200 (≥ 7% legs).
HL costs ≈ 10%/yr → 2× cost SR 0.26; band 0.005 legs-only SR 1.37, BTC hedge leg −7%/yr. Fails HL > 0.8 alone.
### xsrev: short-term cross-sectional reversal (2026-11-08, re-run 11-09) → DEAD
HL OOS −2.66, BN −1.81; 0/6 >0 on both. Turnover makes fees dominate.

### lowvol: betting against volatility, beta-hedged (2026-11-08, re-run 11-09) → DEAD
HL −0.24 (1/6 >0); BN OOS 0.44 but grid med −0.01 (3/6 >0). Not robust.

### funding_contra: fade funding spikes vs own history (2026-11-08, re-run 11-09) → DEAD
HL −0.81 (0/8 >0); BN −0.42 (med 0.15). Not robust.
