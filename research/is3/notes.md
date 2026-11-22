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
