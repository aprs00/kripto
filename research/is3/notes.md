# InSilico third pass: running notes (newest last; think-through per item before its first run)

## M0 (2026-11-22, laptop)
Builder checked on 2021-05-19: 169k micro bars, 24.6k range bars of 0.43%. Not a bug: 8.27M trades, ids and times in order, but 12:00–14:00 UTC the book was torn and trades
bounce 30–40 bp between bid and ask in the same millisecond (realized vol 0.22 on 1-min closes, 0.32 on 1-s). TRAP for M1–M6: in torn minutes range bars are bid-ask bounce.
Every M-form must report results with and without bars that complete in < 1 s (t1 − t0), and entries at the NEXT trade's far side (+spread), not at the bar close.
RAM 1.15 GB peak per worker (busiest day), 3–15 s a day → `--workers 1`, 45-min chunks:
  systemd-run --user --unit is3-m0 -p Nice=19 -p MemoryMax=1800M -p RuntimeMaxSec=2700 --working-directory=$HOME/kripto .venv/bin/python -m scripts.mbars_build BTCUSDT ETHUSDT SOLUSDT --start 2021-01-01 --end 2023-12-31 --workers 1
Progress = number of files in data/bn/mbars/<SYM>/ (1095 each for the explore years).

## L1 liquidation fade (think-through 2026-11-22, before any run)
Source (tg:165–167, 173–174; wa 18.10.18, .25(1), .35(3)): 1-min chart, liquidation candle(s) on the highest volume, then an opposite candle "relatively big yet on low volume" that
"swallowed back the price to levels from which red one pushed"; enter at its close; targets: two intermediate levels, "brave ones" the origin; "do a round quickly unless impressive
cascade, in which case we sit at the end of liquidations... consolidate". Says once it is symmetric (tg:166), later "not so much for bearish pivots" (wa 18.10.18).
Who pays: liquidated longs sold at any price into a book makers have pulled. Why it may not be tradable: in those seconds spread and latency are worst; pass 1–2 filled at the close.
Gap noticed on re-reading: he marks the TWO largest red bars and the reversal need not be the very next minute. The old code demanded climax at t−1, reversal at t. → form h.
Kill: with entry 1–2 min late and +30 bp per side the edge is ≤ 0 outside the top 3 days (a). Keep: cascade-only / wait-for-end / hedged form positive ex-top-3 with dose-response.
Honest limit: z=8 base form has been seen on all 83 coins and all years, so confirm cards of unconditional forms are not clean; only new conditions and live fills are.

## W1 weekend / CME (think-through 2026-11-22, before any run)
Source: tg:70 "winkdex BTC collar, can pretty much safely target it as ask/bid on sunday evening as we will gravitate towards it in monday"; tg:69 between opens = low activity, the next open
"returns to high volume collar"; wa 18.10.59 "routine pre fut open bait pump and then stop run ... return to collar price of Friday"; wa 18.10.23(3) Saturday bounce after Friday's down push.
"Collar" = the WINKDEX blended volume-weighted price, not the CME close the first pass used. Proxies fixed now: vwap 14–16 NY Friday; fattest 10-bp volume node of Friday 09:30–17:00 NY; 16:00
print; 17:00 (old). It is a resting TARGET on Sunday evening (18:00 NY), so exit at touch, else Monday 17:00 NY. Who pays: weekend traders moving price in a book makers have left.
Placebo: the same construction Tue → Thu 18:00 → Fri 17:00 (same clock distance, makers present). If weekend ≈ placebo, "gravity" is just that nearby levels get touched.
Change my mind: touch trade beats placebo with dose in gap size, in 2021–23 and held out. Era caveat: makers-off weekends (2021) vs CME 24/7 trading since 2026 (the mechanism may be gone).

L1 closed OPEN (2026-11-22). Key surprises: (1) the reversal bar is everything (same drops without it: +4 bp); (2) the bounce grows with the size of the fall and lasts hours, not minutes;
(3) liquid coins bounce more; (4) perp discount adds nothing beyond fall size. New forms d=2..5 are as good as d=1 (so ×2 events). Confirm: L1h, L1f not passed.

## T1 resting ladders (think-through, before any run)
What he does not say: in 2021 BitMEX paid makers 2.5 bp and he calls his scalps "rebate harvest": he is the resting order. In a cascade "contrarians slip thru an empty book": the only fill one can
KNOW on paper is a resting bid that price trades far through. That is also the honest fill model: a limit k sigma below, filled only if the low is ≥ 10 bp beyond it. It removes the taker-after-close
problem that killed L1h. Adverse selection is in the data by construction (every fill counts, also the ones that keep falling). Danger: most fills are not cascades but slow news dumps;
quotes are re-set each minute, so a slow grind never fills (distance from the LAST close), only fast minutes do. Kill: mean after the fill ≤ costs in explore on all k, or no dose-response in k.

CORRECTION to L1 (review of my own claim, same evening): "equal drops without the pattern earn +4 bp" used the author's tight stop for both. Without a stop the plain drops DO bounce: z≥8 'any' +20 (x0), +41 (15 min),
+77 (60), +102 (240 min). The reversal bar still shows more (+396 at 60 min) but those are far more violent moments. The stop under the low is what hurts. → T4 must test stop vs no stop.

T1 state (2026-11-22 laptop): explore / confirm / survivorship done, see forms. FROZEN rule T1k30 = bid 30 σ (24-h std of 1-min log returns) below the last minute close, re-quoted each minute,
fill only if the low is ≥ 30 bp through, exit at market 60 min later, one position per coin. explore +184, confirmT +106 (n 164, p .038), confirmC +155 (n 2580, 361 days, p .005), delisted +148. Both
confirm cards pass; T1k20 fails confirmT (p .086). Account sim (5 slots × 10%): confirmC SR 2.1, cagr +32%, mdd −8.7%, every year + (2025 +7%); original coins 2024–25 SR 1.45, +7%/yr.
WEAK POINTS, do not hide: (1) entry at max(limit, minute close) is positive but not significant (confirmT +41 p .44, confirmC +70 p .18): the edge needs the resting fill; (2) 2025 events on the 73 coins
−57 bp (10-10: −30..−46% in 60 min on several alts); slot cap saves the account; (3) which 5 of 20 simultaneous fills you get is first-come in the sim; (4) the 2024–25 alt data were seen by lshock
tests (same crash days); (5) exit at market an hour later, slippage model not a crash model; (6) orders during venue overload.
Mechanism: σ is 24-h, so slow deaths never fill (LUNA 05-2022: 0 fills); only sudden dumps from calm; market-wide ones pay (breadth ≥ 20: +59 at k 8), lone ones do not.
NEXT: g (other coins on the server), h, d (sizing rules: slots, $200, HL fees), then vault 2026 ONCE for T1k30, close, then E2.
Data: data/is3/*.parquet is rebuilt by `is3_lshock build`, `is3_ladder build|frozen|dead`, `is3_weekend build` (copied to the server 11-22). DEAD24 minute bars: `is3_ladder dead` downloads them.
T1 d/h done (laptop). THE risk is simultaneous fills: 2024-02-28 17:31 hit 80 coins in one minute, 2025-10-10 similar. Any book must (1) quote ≤ 10–20 liquid coins, size so that ALL of them filling = ≤ 1–2x gross,
(2) stop quoting when full, (3) choose the universe causally (E2: 30-d volume rank at the previous day's close, not the in-quarter median used in account_batch). The universe cut was picked after seeing
2021–25, so its evidence is only the 2026 vault, the fresh coins' account and live paper. E2 pre-registers: k=30, top 10 and top 20, 10% each, hold 60.
T1 g running on the laptop (`is3_ladder fresh`, downloads 60 coins to data/is3/k1m). If no card T1g_k30__confirmC exists when you read this, run it on the server: systemd-run unit, ~1–2 GB download.
After g: vault for T1k30 (needs an is3_ladder `confirm(("vault",))` call: data to 2026-10), then close T1, then E2.
T1 g FAILED (fresh 60 coins, k30 +13 bp p .93). Do not talk it away: removing 2025-10-10 is hindsight and that day is exactly the risk this trade is paid for (it sells crash insurance: +150 bp often, −13..−16% per
fill in the one crash that does not bounce within the hour, on every coin set: fresh −1567, old 83 −1260). Two facts that are NOT hindsight-only: the liquidity dose is monotone in both independent sets (< 20M negative,
> 20M +119..+200), and excluding that day the fresh coins look like the others (+147). So: T1 as "any coin" is refuted; T1 as "liquid coins, hard cap on total exposure" is open → forms i, j. The vault
must NOT be opened for T1k30 on all coins; it is spent once on form i after j has fixed the exit rules on 2021–23. `account_batch(top=...)` has in-quarter ranking: build the causal universe first.

T1 g detail: 60 coins were drawn, 56 have minute data before 2026 (CFG, CHIP, LEND, MEGA have no 2021-25 minute data in the archive), 53 had k30 fills. All copied to the server (data/is3/k1m; ETH + SOL micro bars 2021-23 complete, BTC 626/1095).

## T1 j + i (think-through 2026-11-22 20:30 UTC session, before any run)
What the source does not say: the ladder-catcher he describes is watching. He knows whether it is "impressive cascade, in which case we sit" (tg:167) and "unless abnormal pressure delivered" (tg:228): he stays
out / keeps out when the move is market-wide and unfinished. A blind re-quoting bid does the opposite: its fills bunch in exactly those minutes. So the missing condition is about WHOSE flow it is and whether
it is over: (1) how many other coins of the quoted set fell with it (known only after the fill: can govern the EXIT, not the entry), (2) BTC's own move over 4 h before (known before: can govern quoting),
(3) was it calm before (σ ratio; k·σ does that), (4) he is out "quickly" → short holds cap the tail, not a stop placed where others' stops are. Fixed now, tried on 2021–23 only:
 exits  : hold 15 / 60 / 240 / 1440; stop −3/−5/−10% below the fill (touched in the minute AFTER the fill; filled at min(stop, that minute's close) = taker in a falling market); stop + reload forbidden (1 per coin-hour)
 quoting: cancel all when BTC 4-h return < −2 / −3 / −5% at t−1; cancel after the first batch of the day (24 h pause); both pre-fill knowable
 size   : all same-minute fills taken, 10% each, stop quoting at 5 open (as in account_batch) → judge the ACCOUNT (worst day, mdd, SR), not only bp per fill
Universe: top-20 and top-10 by 30-d mean Binance volume up to the previous day's close, clean bnall, age ≥ 30 d and ≥ 365 d. 20% of those coin-days had no minute data here (1000SHIB, APE, GMT, TRUMP...): the
earlier top-20 numbers were survivor-ranked. Missing coin-months (plus the month before) go to data/is3/k1m_top. Kill: in causal universe 2021–23 the account with the best-motivated rule is not better than plain T1k30,
or the edge is in coins I already had only. The vault is opened once, for one frozen (universe, k30, exit, quoting) and only if its 2024–25 card (already partly seen) is not negative.
T1 j done (2021–23, causal top-20, 644 fills / 215 days / 92 coins, includes the 20% of coin-days missing before; is3_ladtop.py; checks: equals is3_ladder.fills on the same coins, null −34 bp (se 18), causal ok).
 Plain T1k30: h15 +135, h60 +187 (p .002, ex-top3 +136), h240 +211, h1440 +228 gross; pessimistic entry max(limit, close) h60 +115 (p .002), every year + (2021 +616, 2022 +69, 2023 +118). top-10: +195, age ≥ 365: +150.
 STOPS HURT: 3/5/10% stops at 60 min: +14 / +44 / +70 instead of +187 (p .68/.25/.12): the trade is paid for sitting through the overshoot. STAYING OUT WHEN BTC FALLS HURTS: dose is the opposite, BTC 4-h < −5%:
 +1248 (n 30, 11 days), −5..−3%: +531, −3..−1%: +135, ±1%: +78 → he is right that the cascade is where it pays, and a "wait for calm" filter removes it. Pause-a-day: SR 2.3 → 1.4. Account (5 open max, batch fills, 10% each): h60 SR 2.28 / mdd −5.7% / worst day −4.3%; h15 SR 2.19 (half the profit of h240, tail similar).
 So no rule of mine improved on the plain 60-min exit. 2021-09-07 +, 2021-05-19 + are a third of the profit; 2022-09-13 −, 2023-06-10 −, 2023-08-17 − are the bad days (11–18 coins in one minute, all −): market-wide NEWS dumps.
 Frozen for form i: top-20 causal, all ages, k=30, 30 bp through, taker exit after 60 min, no stop, no quoting filter; account: 10% each, no new quotes when 5 open, all same-minute fills taken.
T1 i confirmT (2024–25, causal top-20, pre-registered in fb57ce3; first push was rejected by a concurrent queue commit, the local commit is older than the run): n 356, 110 d, 85 coins, +259 bp (p .001, ex-top3 +191), pessimistic entry +150 (p .02), 2024 +189 / 2025 +356. Account SR 1.9, worst day −8.4%.
 But: two fills (LIGHT 2025-12-31 +180%, AIA 2025-10-10 +139%; bars printed, prices real, tiny books 0.1–9M USD a minute) are 35% of the sum; top-10 (no such coins) +145 (p .004), age ≥ 365 +145 (p .01), pessimistic +56 / +54 (p .25). Intraday mark: 2025-10-10 sum of each position's worst point
 = −34% of equity inside the hour (booked −8.4%), 2024-01-03 −29%; a 10% × 5 book would have hit any kill switch. Pass per the card, so the vault opens once (T1i, frozen rule, ladtop build 2026-01-01 2026-11-01).
T1 CLOSED CONFIRMED (2026-11-22). E2 inputs: universe = top-20 by 30-d volume at previous close (is3_ladtop.universe; minute data for past coins in data/is3/k1m_top, rebuild: `is3_ladtop universe`, `fetch`, then `build`).
 Size ≤ 5% per order (3% × 10 slots: cagr +10%, mdd −3.6% in 2024–25), all same-minute fills taken; intraday mark matters more than the booked worst day (bounds: 2023-11-09 −16%, 2024-01-03 −29%, 2025-10-10 −34% at 10% size); the fill must be proven live (max(limit, close) entries: 2026 p .18, SR 1.1).
 Not to try again: stops, BTC-fall or calm filters on this rule (they remove the cascade that pays). Vault for T1i is spent.

## S1 re-reading the sources (think-through, 2026-11-22 session)
Nothing to compute here; the risk is a lazy reading that "finds" only what the catalogue already has. Rule for a new form: a claim with a mechanism (who pays), data we hold, and a placebo/baseline I can name now.
Not a form: anything needing news / tweets / options / equities, jokes, psychology (kept only if it changes how a trade is managed → T4). What he does not say: where the picture contradicts the caption, believe the picture.
Order: a (uncited records) → b (indicator guides) → c (PDFs) → d (templates) → e (cited records against the rule as coded). Forms are ADDED only, never removed; each carries its source id.
S1 a done: 14 forms added. Biggest miss of passes 1–2: the second example in the "Issa fade" picture (wa 18.10.24(2)) is a volume spike with almost no body, then a small green bar on no volume = absorption, not a dump. L1 only ever tested dumps (z ≥ 6). → T5f.
 Also new: OI falling vs rising during a dump (wa 18.10.51: "almost all selling was closing") → T5g (5-min OI of 10 coins is on the server, 2021-12..2023); time-POC vs volume-POC disagreement (tg:49) → P2i. Trade-count lag proxy needs no micro bars (M2e, minute klines).
S1 b done: the guides give mechanics, not formulas. What passes 1–2 missed: (1) FSVZO entry is the first bar WITHOUT an alert (O2e), (2) Crayons p22: a signal whose candle is invalidated by a close beyond its open may be traded the OTHER way ("as impressive if not more") → O2k,
 (3) p15 yellow/aqua climax in a strong trend = pause, not reversal, (4) p24 stops go beyond the prior swing, never at the signal candle ("illiquid wicking"): same finding as T1/L1 (tight stops hurt). Any proxy that fails says nothing about his proprietary code; say so in the O2 verdict.
S1 d done. DISCOVERY: every drawing in the templates has an id that is a ms timestamp, so 107 unique levels (Jun–Oct 2020, BTC ETH LINK LTC) are dated, real-time human levels → T2e (data/ needs 1-min klines of 2020-06..2020-12 for 4 coins: data.binance.vision monthly, small). Levels are in research/is3/S1d__notes.json.
 Settings that differ from mine: his session single prints start at ~8–12 bp (3 rows of 4 bp), mine needed 30 bp (P2l); net longs/shorts panels (T5h); stacked imbalance 250/400% (M7d); weekly/monthly naked levels (P3d).
S1 c done. Usable: Almanac first-of-month / turn-of-month windows, down Friday + down Monday, Dec-15 lows (C1g–i). HOFM + Artemis have no rule but name T1's real risk (overbetting on one scenario; short convexity) → E2d: ladder P&L in the 20 worst weeks next to the other books, size from a worst case of −50% on every simultaneous fill.
S1 e done, S1 closed (reading item). Biggest corrections, all from pictures: (1) R3's demand bar is THIN and FAST (18M volume = lowest of the run, delta 78% of it, 24.98 buys/s vs 1–5, 137 sell trades vs 1,000–12,000): I coded only the sign of 7 groups → M1e.
 (2) R14's gap is the valley between two humps of yesterday's profile, not "the least-traded third" → P1f. (3) mousetrap = two tests, the second with many times the volume → M3e. (4) R1's examples are big negative shares on −2.6k..−5.6k days → M4e. (5) R7 at pdVAH → M2b. (6) the retest bid has a second target (A) → M5e.
 NEXT: E2a (walk-forward of the ladder), or T2 with the new form e (dated 2020 levels, needs 1-min klines 2020-06..12 of BTC ETH LINK LTC; ~24 small monthly files).

## E2 a (think-through 2026-11-23 01:50 UTC, before any run; T1i_audit read)
Source (tg:167/228, T1 records) adds nothing new for E2: E2 is the engineering of the T1 book. What a walk-forward must answer that T1 did not: does a CAUSAL choice among
k 20/30/40 × hold 15/60/240 × slots 5/10 (18 configs, refit every 60 d on all prior days like kripto.research.walk_forward, first 240 d burn-in) keep the edge, and does
the in-sample pick beat the grid average (assumptions row 9)? Fixed before the run, from the audit: 5% per order for every config (slots 5 = 25% gross cap, 10 = 50%);
fills with depth k·σ beyond the coin's Binance PERCENT_PRICE band (live_exchange_info.json multiplierDown; delisted coins 15%) are dropped; all same-minute fills taken;
costs 7 bp + volume slip per round trip, stress 2×; $200 twin = same with BTC/ETH fills dropped (5% = $10 < their $50/$20 min). 2021-01..2026-10 incl. the vault year
(already opened for T1k30 h60 only; k20/k40 and other holds in 2026 are new). Not modelled: a 1-min delay of a resting quote (needs a rebuild; next form if a passes).
Registered as one walk_forward line (strategy `ladder`, dataset `bntop20_1m`). Kill: OOS SR < 0.8 net, or < grid average, or 2× cost SR < 0.5.
What he does NOT say: the bid is a small resting order he forgets about; capacity is the slot cap, not the signal. So the account, not bp per fill, is judged.
E2 b gate (02:20 UTC). Frozen T1k30 h60 slots 5, 5%/order, band rule: base 2.14, 2× cost 2.04, ONE BAR LATE (quote from close t−2, exit +1 min; `is3_e2 build -30`) 2.14 (1,597 fills, 116 bp/fill vs 1,005 at 161:
 a stale bid is hit more often in the 2nd minute of a dump, worse per fill, same SR), first 6 / 12 months dropped 2.11 / 2.00, $200 2.16 → robust.worst 2.00 > 0. WF min(pick 1.94, grid 2.19) = 1.94 > 0.8, DSR .98 > .9,
 grid median 1.88 > 0. HL leg: not testable (no HL minute history); live paper is the test. → INCUBATION-ELIGIBLE on Binance. Form b stays open: the live book is code (next session, tests first, rule 6):
 spec: kripto/ladder.py run by a 1-min user timer or inside kripto/live.py; per minute for causal top-20 (30-d vol rank at previous close): σ = 24-h std of 1-min log returns from public 1-min klines, bid = close·(1−30σ),
 skip if 30σ > PERCENT_PRICE (1−multiplierDown); fill only if a LATER minute's low ≤ bid·(1−30 bp) (no same-minute look-back), 5% per fill, all fills of a minute taken while < 5 open, exit at the close 60 min later
 + taker fee + slip; books shadow:ladder@bn $2,000 + small twin; mark every 20 s via live.py marks. Binance request budget: 20 klines calls/min = too much at ≤ 1 req/s shared? → use one ticker/24hr + per-coin 1m klines limit 2 = 20 req/min, OK (≤ 1 req/s).
