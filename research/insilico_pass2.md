# InSilico rules, second pass: think-through before any test

Started 2026-11-15 (prompts/insilico_pass2.md). The first pass tested one literal form per rule. This file is the thinking that
should have come first. **Nothing below has been run.** Section per idea family: what the author actually does, the mechanism,
why the first-pass form was a poor translation, the formulations worth exploring, the samples, and what would change my mind.

Samples, fixed now. EXPLORE: 2021-01..2023-12, coins BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC. CONFIRM: 2024-01..2026-10 and
coins never used in exploration. Honest limits of that split, from what the first pass already looked at:
* liquidation fade: the literal config has seen 2021–2026 on 30 coins. Only the ~500 other Binance perps and live paper are clean.
* trade-size buckets: the sign-only form has seen BTC/ETH/SOL for the whole period. New forms have not, but I know the broad facts
  (structural sell bias, continuation after one-sided buying). Clean confirmation = other coins' aggTrades, downloaded only then.
* profile rules: untouched everywhere.

Sources not available: the author's Medium articles (he points to them for the liquidation trade and for "empty stop-driven
moves"; Medium refuses automated reading) and the BitMEX public trade archive (403). Bybit's inverse BTCUSD trade archive is
open (≈ 90 MB/day in 2021): the nearest thing to the venue he read.

---

## 1. Trade-size buckets (R1 capitulation, R2 capitulation in a trend, R3 rotation exhaustion)

**What he actually does** (tg:199–223, 274–284; wa 18.10.55–57, 18.10.38 (3)).
* The tool colours each size group's delta by how unusual it is (8 colour steps up to the 90th percentile). His words are about
  intensity: "bright red", "strong one-voiced bias that stands out", "tails, not the mid noise". Sign alone is never the signal.
* Intraday he reads it on fixed-distance bars (Range 500 ≈ 0.4%), at a location: after a run into the weekly high every group
  turns bright red → the demand run is over; after a rotation low every group turns green → ride. He waits for the bar to close.
* The daily rule ("negative in all 6 → local bottom") is shown on three days that were also the largest down days of their
  month (−5,625, −4,608, −2,624 points) with every bucket at −2% to −21% of its volume. So it is "a big down day on which every
  size class dumped hard", not "a day on which every bucket happened to be slightly negative".
* R2: inside an uptrend, the pullback day that "spins more delta than at any other point" is the low.
* Venue: BitMEX XBTUSD, by 2021 a small venue of mostly professional accounts ("less apes, more smart traders"). He says the
  reading is exchange-sensitive and that perp shorts are mostly spot hedges, so negative perp delta alone is not bearish (R13).

**Mechanism.** Forced or panicked selling by every participant class at once exhausts the sellers who can still be forced; the
next marginal trader is a buyer. For this to be visible, the flow has to be abnormal for each class, and it has to happen on a
venue where taker flow is speculation rather than hedging.

**Why the first-pass form was a poor translation.**
1. Sign only. On Binance "all buckets negative" happened on 17–30% of days, and negative days outnumber positive ones 2–6 to 1:
   that is the hedging bias he describes in R13, not capitulation. A rule that fires one day in four cannot mark bottoms.
2. Fixed USD buckets from 2020 to 2026 while prices rose 10×; his buckets are refitted from the recent size distribution.
3. No location: he uses it after a run or on a large down day; I used every day.
4. One venue, the noisiest one by his own standard.

**Formulations to explore** (descriptive event studies first; each compared with a matched baseline, not with zero).
* T1 *Abnormal capitulation.* Per coin and bucket: delta/volume as a z-score against its own trailing 90 days (this removes the
  structural sell bias). Event = a down day of at least 1.5 daily σ on which every bucket's z < −1. Baseline = down days of the
  same size that are not one-voiced. The question: does one-voiced abnormal selling add anything to "it fell a lot"?
* T2 *Capitulation inside a trend* (R2). Same event, only when price is above its 50-day mean; baseline = other pullbacks of
  the same size in uptrends.
* T3 *Size disagreement.* On down days, large-bucket z positive while small-bucket z negative (size absorbs what retail dumps),
  and the mirror image. This is the daily cousin of the mousetrap and uses the one thing buckets give that plain flow does not.
* T4 *Rotation exhaustion* (R3), intraday on volatility bars built from the 5-minute bucket data (accumulate until price has
  moved 0.4%): after ≥ 3 bars up into a 1-day high, a bar whose buckets are all abnormally negative. Not a book: an exit and
  entry-timing signal for positions the slow books already hold.
* T5 *Venue.* T1 on Bybit inverse BTCUSD for 2020–22. If the rule does not hold even there beyond his three examples, the idea
  is dead at the source. If it holds there and not on Binance, the question becomes which venue plays that role today
  (Hyperliquid, where `tsz` now records one address as one order).
* T6 *As a feature, not a rule.* The first pass found that one-sided BUYING across all sizes is followed by gains. Does
  breadth across size classes improve the existing `flow` signal beyond the plain taker imbalance it already uses?

**What would change my mind.** For: T1 or T2 shows excess forward return over its matched baseline in exploration, the same sign
on BTC, ETH and SOL, and it survives on unseen coins and 2024–26. Against: no excess over "it fell a lot" in T1–T3, and T5 shows
nothing on the author's own venue type and era. Then the reason is known (his examples were large down days, and large down days
bounce on average regardless of who sold) and the idea can be called dead.

---

## 2. Profile and auction rules (R14 gap fill, R15 prior POC, R16 single prints, R17 balance laws; R19 at profile levels)

This is the largest part of the author's material (the first third of the channel) and the first pass never tested it. I ranked
it low because "it needs volume-at-price". That was wrong: his time profiles (TPO) need only each 30-minute bar's high and low,
which we have exactly; volume-at-price can be approximated from 1-minute bars.

**What he actually does** (tg:27–58, 80–81, 133–134, 288; wa 18.10.31 (2), 18.10.23 (1); templates).
* Profiles per day and per session (UTC: Asia 00:00, London 07:00, CME 13:30, Pre-Close 19:15), 30-minute periods, value area 68–70%.
* Claims, in his order of confidence: prior POC / fat nodes are reactive on first touch and better support than the daily open;
  a composite POC is a magnet; thin areas and single prints left by a fast move get revisited ("most of times"), session ones
  more reliably than daily ones; after the fill there is a mechanical bounce; a single-print zone sitting right under a big POC
  did NOT fill (he explains why); value tends to form next day where the previous day traded least; the ten balance laws
  (accept back into value → travel to the other side; edges reject until proven otherwise).
* He uses them as targets and locations ("we target those points"), combined with flow at the level. Never as signals alone.

**Mechanism.** Positions were opened where volume traded; those holders defend or exit at their entry (reaction at fat nodes),
and fast moves through thin areas leave resting interest unfilled on both sides (revisits). Plausible, widely believed by
futures traders, and also the textbook case of a pattern that looks true because prices revisit nearby levels all the time.

**The trap to avoid.** "Price came back to the level" proves nothing: a random walk returns to a level 1% away within a day most
of the time. Every test here needs a placebo: for each real level, a fake level at the same distance on the other side of
price (and a time-shifted one). The claim is true only if real levels are touched more often, or react more strongly, than placebos.

**Why this family fits the account better than what I tested.** Trades are few (a handful per coin per week) and the targets
are large (a value area is 1–3% wide), so costs of 10–13 bp per round trip do not decide the outcome the way they did for the
1-minute scalps.

**Formulations to explore.**
* P1 *Single-print fill.* Session single prints (a price band visited in only one 30-minute period, inside the session's range).
  (a) Magnet: is an unfilled band revisited within 1–3 sessions more often than its placebo? (b) Reaction: after the fill, does
  price bounce away from the band more than from the placebo? Tradable form if (a) holds: enter toward the band when price
  starts moving at it, target the far edge. Check his exception (band directly under a prior POC fills less).
* P2 *Prior POC first touch.* Yesterday's and the prior session's POC: forward return over the next 30–120 minutes after the
  first touch, signed away from the approach direction, vs placebo levels and vs the daily open (his explicit comparison).
  Tradable form: resting order at the level, target the value-area edge. This is R19 done at the levels he names, with the
  volume-at-the-level fill model instead of the blanket trade-through.
* P3 *The 80% rule* (balance law 1). Open outside yesterday's value area, trade back inside and hold there for two 30-minute
  periods → enter toward the far edge of value, stop outside the near edge. One trade per coin per day at most; fully
  mechanical; the classic falsifiable statement of auction theory. Baseline: the same entry with yesterday's value area
  replaced by a placebo band of equal width.
* P4 *Gap fill* (R14). Does today's time-at-price concentrate in yesterday's thin zone more than chance (overlap of today's
  value area with yesterday's lowest-volume third vs with a random third)? Descriptive; if true it feeds P1/P3 as a target.
* P5 *As a filter.* Do the slow books' entries do better or worse when made at a prior POC / inside vs outside value?

**What would change my mind.** For: real levels beat placebos in exploration by a margin that is large next to costs, on most of
the 10 coins, and the same in confirmation. Against: real and placebo levels are indistinguishable in P1, P2 and P3. Then the
reason is the classic one (levels look reactive because any level is revisited) and the family is dead for mechanical use.

---

## 3. Liquidation fade (R5), the survivor

**What he actually does** (tg:165–168, 173–174; wa 18.10.18, 18.10.25 (1), 18.10.26, 18.10.24 (1), 18.10.35 (3)).
* 1-minute chart, no feed needed: liquidation candles on the highest volume (his box marks the TWO largest volume bars at the
  low), then "a significant green bounce on insignificant volume". Enter at that candle's close, half off at an intermediate
  level, half at the origin, "do a round quickly".
* His reason: liquidations sweep one side of the book, makers pull and "those orders don't come back", so the side price slid
  through is empty and "it takes little action to slide back". He tracks individual large liquidations.
* Limits he states: in an impressive cascade you wait for the END of the liquidations; in a downtrend it repeats ("liq → bounce,
  refuel → liq") so the bounce is a scalp, never a bottom ("bottoms take time"); "not so much for bearish pivots".

**What the first pass showed.** +78 bp per trade over 730 trades on 30 coins, including 20 never fitted on; nothing on the short
side, as he says. But days with a single trigger lose a little and days when five or more coins trigger make +155 to +413 bp;
three days carry 72% of the profit; per day it is not significant.

**What that pattern means.** The mechanism needs FORCED selling. My trigger (a 6σ minute on 5× volume) cannot tell a liquidation
cascade from a news dump: after news the sellers are informed and there is no bounce. Market-wide trigger days are the days
that really were cascades. So the first-pass form was right about the entry and wrong about the condition: it never checked
that liquidations happened.

**Formulations to explore.**
* L1 *Open-interest condition.* Binance publishes 5-minute open interest per symbol back to 2020-09 (public archive, small
  files). Liquidations destroy open interest; new shorts create it. Event = the same dump, split by whether open interest fell
  over the dump (by ≥ 1–2%) or rose. Prediction from the mechanism: the bounce is in the OI-falling group on single-coin days
  too. This is the direct test of the author's explanation and I did not think of it in the first pass.
* L2 *Perp discount.* Forced perp selling pushes the perp below the index. Event split by the premium at the low (premium
  index klines are public). Same prediction.
* L3 *Cascade breadth.* Enter only when ≥ 5 coins trigger within 30 minutes. This was seen in the data, so only coins outside
  the 30 count, and it must be fixed before their data is downloaded.
* L4 *Wait for the end* (his own rule for large cascades): enter on the first up-close bar after the volume peak has passed
  (volume below half the peak), instead of the first up bar. Compare drawdown inside the trade, not only the mean.
* L5 *Risk filter for the slow books.* After a cascade day (L1 definition), do new shorts opened by trend / listing-short books
  lose money over the next 1–3 days? If so, delay them. Costs nothing to trade and uses the effect where fills are not a problem.
* L6 *Fill realism.* Entry and stop slippage of 30–50 bp, no fill in the first minute, and Hyperliquid's own behaviour on
  2025-10-10. Then the live 1-minute paper book (backlog E1), the only thing that can settle what fills would have been.

**What would change my mind.** For: L1 or L2 moves the profit from "three days" to "most OI-falling events", i.e. single-coin
events with falling open interest are positive, on unseen coins, with a day-clustered t above 2. Against: even conditioned on
falling open interest the profit stays in the same three days. Then it is a bet on rare market-wide crashes with the worst
possible execution, and it stays a watch item, not a strategy.

---

## Order of work after this checkpoint
1. Profile family first (P3, P2, P1 with placebos): never tested, the author's main subject, and the least cost-sensitive.
2. Liquidation fade L1/L2: one small download (open interest, premium), a direct test of the mechanism on the one survivor.
3. Trade-size T1–T3 on the existing data, then T5 (Bybit) only if T1–T3 leave the question open.
Remaining families (mousetrap at real levels, weekend with the "collar" reference, R6/R8/R9, R28) get their think-through after these.

---

# Exploration results (2026-11-15; sample 2021-01..2023-12, the 10 original coins; BTC/ETH/SOL for trade sizes)

Scripts: `research/studies/is2_profile.py`, `is2_liq.py`, `is2_tsize.py`, `is2_bybit.py`. Returns in bp before costs unless
stated. "t" is day-clustered. These numbers were looked at freely and are NOT evidence; the confirmation tests below are.

## Profile rules: the levels are not special, two side-effects are
| formulation | result | reading |
|---|---|---|
| P3 80% rule (2,764 trades) | far edge reached 30.3% vs 37.2% for a random walk with the same geometry (t −7.9); −1.0 bp per trade | fails: price that re-enters yesterday's value turns back out more often than chance |
| P2 first touch of yesterday's POC | +8.4 bp over 2 h (t 4.0); fake POC from 8 days earlier: +6.8 bp (t 3.8) | fails: any level a dip reaches bounces the same; the POC adds ≈ 2 bp |
| P2 value-area low / high | low: +9.9 real vs +14.7 placebo; high: −0.4 vs −1.1 | fails; shows an asymmetry instead: dips bounce, rallies do not fade |
| P1 single-print band filled before the same distance the other way | 48.1% real vs 51.2% placebo (random walk 50%) | fails as a magnet |
| P1 after a US-session (13:30–19:15 UTC) impulse | band filled only 42.4%; fading it −42 bp per trade, 0/10 coins positive | the OPPOSITE holds: US-session impulses continue (2021 −71, 2022 −43, 2023 −1; up-impulses −75, down-impulses −10) |
| P1 bounce in the 30 min after a band IS filled | +10.4 bp (t 5.7) real vs +1.2 bp placebo | real and specific to real bands, but below a taker round trip (≈ 13 bp) |
| Session momentum, US session up-move ≥ 1.5% | next 72 h +136 bp (t 3.0), 9/10 coins; down-moves −12 bp | lead: this is R24 (kill zones: "trends coming out of New York persist"), long side only |

## Liquidation fade: the size of the dump is what matters; open interest does not
* L1 open-interest split (z=4 triggers, n=599): fell > 2% −7.9 bp, fell 0.5–2% −2.0, flat −3.8, rose −4.6. No separation, also with
  z=6. 35% of triggers have no open-interest row within 6 minutes: the archive has gaps exactly in the wildest minutes (those
  unlabelled triggers are the best ones, +133 bp at z=6). **Fails**, reason: 5-minute OI is too coarse and missing when it matters.
* Dose-response (m=5, full engulf, long, net of costs): z=4 +5.8 bp (n=599) · z=5 +28.3 (275) · z=6 +70.2 (154) · z=8 +150.4 (73) ·
  z=10 +193.8 (44). Win rate 54% → 64%. At z ≥ 8 the days with only 1–2 triggers are strongly positive too (+112 / +205 bp), the
  top-3 days are 53–60% of the P&L and the rest still makes +81–95 bp. Short side at z=8: −43.6 bp. Half engulf: +2 bp.
  Reading: a monotonic dose-response is what the forced-selling explanation predicts, and the first pass's z=6 was a middle setting.
* Exits: 15-minute hold +47 bp, 60-minute (base) +70, 4-hour +65: the edge is made in the first minutes, as he says ("do a round quickly").

## Trade-size buckets: one-sided flow continues; it does not exhaust
* T1 big down day with every bucket abnormally negative (n=14): next 3 days −235 bp vs +26 for other big down days. T1b total delta
  z < −2 (n=26): −77 vs +20. T2 the same in an uptrend (n=8): nothing. T3 large sell / small buy on a down day (n=13): −716 vs +58.
  None significant (3 coins), all with the sign OPPOSITE to "capitulation = bottom".
* T4 intraday, 5-minute bars: "top signal" (at a 1-day high, every bucket abnormally negative, n=76): price went UP 7 bp over the next
  hour (baseline +2). Capitulation at a 1-day low (n=192): worse than other bars at the low (4 h +9 vs +19 bp, t −3.7).
  At a 1-day high with every bucket abnormally POSITIVE (n=249): +28.8 bp over 4 h vs +9.6 (t 3.6).
* Reading: five formulations, same answer. On Binance, one-voiced flow across all trade sizes is continuation (the metaorder
  persistence the `flow` book already trades), at the daily and the 5-minute scale. Remaining honest gap: his venue (T5, Bybit).

---

# Confirmation results so far (2026-11-15; held-out: original coins 2024-01..2026-10, and 20 unseen coins 2021-2026)

Session stopped here by the usage limit. Done: B, C, D. NOT done: A (liquidation fade z=8 on 52 unseen coins; their 1-minute
bars were still downloading) and E (Bybit; download was at ~400 of 1,188 days). Both downloads resume if restarted; then run
`python -m research.studies.is2_bybit study` and the frozen lshock configs through `research.evaluate` (tag "confirm").

* **B US-session momentum: NOT confirmed.** Excess 72 h return after a US-session up-move >= 1.5%: original coins 2024-26 −5.7 bp
  (t 0.2); unseen coins +26 bp (t 1.0) and +71 bp (t 2.5). By year on the unseen coins: 2021 +115/+552, 2022 −6/−46, 2023 +169/+225,
  2024 +36/+44, 2025 −105/−178, 2026 −57/−106. A bull-phase effect that reversed in 2025-26, not a stable one.
* **C single-print bounce: NOT confirmed at the pre-set size.** Real minus placebo, 30 min after the fill: +4.4 bp (t 2.5), +5.1 (t 0.7),
  +3.8 (t 1.2). Present everywhere, but 4-5 bp, and the bounce itself fell from +10 bp (2021-23) to +2 bp (2024-26).
* **D one-voiced buying at a 1-day high: statistically confirmed, economically nil.** 2024-26, BTC/ETH/SOL: +6.4 bp over 1 h vs −0.9 for
  other bars at the high (t 4.7), +15 vs +3 bp over 24 h (t 3.9); the 4 h difference the test named is +1 bp (t 4.7 on daily means).
  Below costs: a confirmation feature for entries the slow books already make, not a book. The author's "top signal" (every bucket
  abnormally SELLING at the high) was followed by further gains in both samples (+34 bp / 24 h held-out, +116 exploration).
* Held-out checks of the exploration failures: 80% rule hit rate 25.7-30.5% vs 36.5-37.7% for a random walk (t −9.9 to −10.7) on all
  three held-out samples; yesterday's POC no better than a fake level; single-print bands fill 47.7-49.0% vs 50.7-51.9% placebo.
  The profile LEVELS fail in every sample. Verdicts to write next session: R14-R17 as mechanical level rules = three formulations
  failed (magnet, first-touch reaction, 80% rule), reason diagnosed (any level a move reaches reacts the same); R3/R1 on Binance =
  five formulations, one-voiced flow continues.
