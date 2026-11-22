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
