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
E2 b done (13:47 UTC session): live book running. kripto/ladder.py (kripto-ladder.service, 1.5 s client, 20 klines calls/min, weight ~20/min), books shadow:ladder@bn $2,000 + small:ladder@bn $200, marked and kill-switched by kripto.live, funding by venue_bn.
 Quote valid only for minutes opening after it was computed = the one-bar-late backtest (2.14). Universe rebuilt daily in a child process from bnall (0.42 GB, 14 s); matches is3 top_universe exactly on 2026-10-31 / 06-15 / 2025-03-02.
 First tick: 20 coins, 18 quoted (2 outside PERCENT_PRICE). Kept out of main_bn: promote only when live fills (count, bp/fill vs backtest 116 bp one-bar-late) say the fill model holds. Next: E2 c (risk: margin, 2025-10-10 minute replay, daily loss cap), d (crash-insurance view).
 What to check weekly: fills/week (backtest ~1,600 / 5.8 y ≈ 5/week at one-bar-late across 20 coins), mean bp/fill net, worst intraday mark.

## E2 c (think-through 2026-11-23 22:20 UTC, before any run)
No new source text: c is the engineering risk of the live book (shadow:ladder@bn, one-bar-late rule, 5%/order, < 5 open, all same-minute fills taken, kill switch at −25% from peak in kripto.live).
What the booked-daily numbers hide and this form measures on the one-bar-late fills (e2_k-30, band rule), minute by minute (fill → exit at t+61):
 (1) intraday MARK of the account (each open position at the minute low = worst case, and at the close): worst mark drawdown from the running peak vs the booked worst day; would the 25% kill have fired?
 (2) gross when a cascade fills many coins in one minute (rule takes them all): max simultaneous gross, and the margin resting bids lock (Binance reserves initial margin for open orders: 18 coins × 5% = 90% notional).
 (3) outage during a cascade: exits delayed to 240 min on days with ≥ 5 same-minute fills (proxy: cannot close for 3 h).
 (4) a daily loss cap (stop taking fills for the rest of the UTC day once the day's marked P&L < −2/−3/−5%), judged on SR, mdd, worst day; the T1 lesson says filters that skip cascades hurt, so expected: cap costs SR.
What he does NOT say: he sizes so that a cascade of fills is survivable ("overbetting kills"); the size rule, not the signal, is the risk control. Kill/keep: if the minute-mark mdd at 5% would breach 25%, the live size is wrong → cut it (rule = largest size whose worst minute mark ≥ −15%).
E2 c done (is3_e2risk.py, data/is3/e2c_risk.json): worst minute-LOW mark −17.4% of starting equity (2025-10-10), −16.9% (2024-01-03), vs booked worst day −4.6% → under the 25% kill; 5%/order kept (10% would be −35% = killed).
 Gross reaches 95% when a cascade fills 19 coins in one minute; resting bids lock up to 100% notional → a real account needs cross margin ≥ 2×. Exits 3 h late on cascade days do not hurt (SR 2.05, h240 > h60 there).
 Daily loss caps do nothing (the loss arrives in one batch minute). Size is the only risk lever; the 25% kill is reachable only at ≥ 8%/order.

## E2 d (think-through 22:50 UTC, before any run)
Claim (S1 c: Artemis "short convexity", HOFM "overbetting kills"): a resting bid under a crash is SHORT a put: small steady gains, rare big losses, and the losses land exactly when
the other books also lose. Test: the ladder's booked daily P&L (one-bar-late, band, 5%, 5 slots) next to the main_bn mix (flow@bn, xsmom@bn, blend@bn, 1/3 each, bnall 1d, research.evaluate, tag E2d)
and BTC in the 20 worst weeks of each; weekly correlation. Insurance-seller verdict if ladder sum in the mix's 20 worst weeks < 0 and corr > 0.3. Size: (i) worst case −50% on every fill of the largest same-minute
batch (19) must stay above the 25% kill → f; (ii) half-Kelly from daily returns. If (i) or (ii) < 5%, the live size is too large and must be cut (decided now).
E2 d done (is3_e2d.py, E2d__insurance.json): NOT short insurance at the booked level: +11.3% over the main_bn mix's 20 worst weeks (18/20 ≥ 0), +3.9% over BTC's; weekly corr −0.12 / +0.08.
 Pre-set worst case (−50% on all 17 fills of the largest batch must stay above the 25% kill) → f ≤ 2.94%: live SIZE 0.05 → 0.029 (kripto/ladder.py; BTC can no longer fill in the $2,000 shadow, step 0.001 ≈ $60 > $58).
E2 CLOSED OPEN: everything left is live evidence (fills/week ≈ 5, bp/fill vs 116 one-bar-late; at 2.9% expect ≈ +8%/yr simple). Next item per queue.

## S2 b1 (think-through 2026-11-23 22:40 UTC, before opening anything)
Reading item: the risk is confirming the stored vision descriptions instead of looking. Per image: what is drawn, the visible entry/exit/level/timing, and a flag
contradict yes/no vs the description (descriptions printed by /tmp-style helper from items.jsonl image.vision). b1 = the 2021-03 profile thread (tg:15–59), tweet-overlay
"sentiment" pictures (tg:136–154), the 1-min fade pictures (tg:165/173 = L1/T5f sources) and the range-500 footprint momentum sequence (tg:199–222 = R3 / M1e source).
What he does NOT say but must be doing, to look for: where the entry is relative to the profile (edge vs POC), whether the fade examples have a resting order visible (DOM/limit
heatmap), and what invalidates the footprint "rotation" (the frame where he would be out). A new form only if a picture shows a mechanism with data we hold and a nameable baseline.
S2 b1 done (40/40 opened by eye, 0 contradictions: the stored descriptions of this batch are accurate). New: M4f pitstop-then-continuation (tg:206 'demand momentum is no mo, PITSTOP ... and breakout' at the all-red bar on the high,
 then 8 h rotation with big all-red bars that make no new low at wVAL = absorption, go = first bar whose buckets flip green, outcome +0.4% breakout). tg:165 dated 15 Feb 2021 02:21 UTC and hand-checked (fixture for L1/T5f).
 tg:52: the session with POC at its own extreme (time+volume at the low) is his reversal picture; P2 family. Next: b2.
S2 b2 done (40/40, 0 contradictions). No new form: the pictures map to M5 (range-high retest; tg:229 hand-checked: ETHUSDT perp 8 Apr 2021, range high 2074.96 22:26 UTC, breakout 23:03, retest wick 2071.37 ~23:35, 2085.6 at 23:44),
 M4e (20 Jul 2021 all-bucket negative day = bottom), M2e (capitulation bar = most trades), P2g ('issa fart': thin-volume wick low), P2h (R/F 0 'perfection'), O1d (RSI out of band = trend), W1, B0. Next: b3.
S2 b3 done (8/8, 0 contradictions): M4e's three capitulation pictures confirmed by eye; the Jan 2022 one retested its low 2 days later (−2.4%) before rallying → M4e must look 2–5 days out, not only next day. Next: b4.

## S2 b4 (think-through 2026-11-24 04:55 UTC, before opening anything)
b4 = tg:17–205 (Mar–Apr 2021) + tg:296: mostly tweet/text screenshots, book pages (HOFM, Wilmott, Almanac, PTJ clipping), memes, two Exocharts settings dialogs and the
oscillator template. Expected: few trading rules; the risk is the opposite of b1 (assuming "just a meme" without looking). Look for: (1) any number in the settings
dialogs that differs from what M1e / T5 use (TSize levels in tg:205, row set in tg:204, Tick*47 in tg:17), (2) the oscillator template (tg:86) = his trend/range regime
rule for O1, (3) the 'X is dead' sentiment tweets = B0 (no lawful tweet data) unless a date + price can be checked by hand (tg:135 VIX 22 Mar 2021).
What he does NOT say: the sentiment fade needs a price location too ("double bottom + laser eyes" tg:141), i.e. the tweet is a filter on a level, not a signal.
S2 b4 done (40/40 opened, 0 contradictions). Mostly tweets/book pages/memes. Useful: tg:205 his TSize groups are 'AI levels' from the PREVIOUS DAY only (31k/57k/111k/155k/250k
 on XBTUSD; our fixed EDGES match that snapshot) → M4a primary changed to 1-d quantiles (30 d = variant); tg:204 colour grades capped at the 90th pct → M1c should clip z there; tg:78 he calls
 his lines 'meme lines, reactive' (placebo levels stay mandatory). Cross-cutting idea from Wilmott p.17 (tg:158): 'avoid the hands just a little worse' = check the 2nd-best bucket of every dose-response. Next: b5.

## S2 b5 (think-through 2026-11-24 ~05:00 UTC, before opening anything)
b5 = tg:118–289 (Mar–Sep 2021) + wa 18.10.18–18.10.21 (tweets 2021–2025). Contains rule-bearing pictures: tg:210 'anomaly = one-voiced bias through all 7 groups ... ends in reversion
or serious puke if faded' (M1/M4 source), tg:230 'bid at previous high, ask at average size of that timeframe's candle' + Wyckoff range→impulse (M5 source), tg:231 'anatomy of a price surge'
(thin weak base leg), tg:261 the FPBS Excel export (which columns he actually studies), tg:279/290 per-day TSize cells, tg:288 '10 laws of market dynamics' (balance areas = P family),
wa 18.10.19 'real alpha is price reaction to pulls and lifts of limit orders' (needs L2 deltas: we collect HL L2 hourly only). Check each picture's numbers against the stored text;
what he does NOT say: in tg:230 the ask size is a TARGET distance (avg candle range), not an order size, i.e. a fixed-R target after a range break-retest; check the picture says so.
S2 b5 done (40/40 opened, 39 legible: wa 18.10.19(2) is a 119-px-wide scroll, unverifiable; 0 contradictions). Rule pictures all map to queued forms (M1, N3k overlap, N3a swing speed, P2 balance laws, N1 round
 numbers). Only gap: wa 18.10.19 'real alpha is price reaction to pulls and lifts of limit orders' needs book deltas we do not collect → backlog W2 (HL websocket l2Book collector). Next: b6.

## S2 b6 (think-through 2026-11-24 ~04:52 UTC, before opening anything)
b6 = 40 WhatsApp screenshots (wa 18.10.21–18.10.35, tweets 2021–2025): mostly attitude/psychology. Rule-bearing ones to read closely: 18.10.24(1) Sep 2021 'mechanical reaction to 40,000,
bottoms need time/volume, V-reversals rare' (N1/M4), 18.10.28(1) 'change of character = stable negative deltas start to pour rotations of high positive deltas' (M4f/M1), 18.10.29(1) 'mean rev
course ... just needs order velocity' (X1f), 18.10.35(3) 'liquidations pull orders that don't come back ... spring-back to origin' (L1), 18.10.32(3) faucet withdrawals (R20 small-size edge),
18.10.23(3) 'Saturday after Friday's downpush' (W1), 18.10.24 Chinese New Year, 18.10.23 sell in May, 18.10.28(3) September (C-family calendar), 18.10.34 venue choice for flow (Bybit inverse).
What he does NOT say: in CHoCH the threshold is relative to the coin's OWN routine (z vs its recent distribution), not an absolute delta; check the picture for numbers that fix the scale.
S2 b6 done (40/40 opened, 38 legible; 0 contradictions). Attitude tweets mostly; every rule claim is already a queued form (C1, V1a, M3b, N3f, X1f, W1). New angle: wa 18.10.35(3) the spring-back
 needs ONE big position liquidated FULLY → needs liq prints (data/bn/liq from 2026-11-17) → backlog L1p, testable from 2027-02-17. CHoCH (wa 18.10.28(1)) = break of the coin's own routine: z-score, no fixed threshold. Next: b7.

## S2 b7 (think-through 2026-11-24 ~04:55 UTC, before opening anything)
b7 = wa 18.10.35–18.11.01 (tweets 2021–2023), denser in rules than b6. Read closely: 18.10.42(2) Nov 2020 'relative change in trade count by 10 times for rotation = change of order velocity =
change of character' (X1f/M2e: is the 10x per range bar, i.e. per fixed distance? check the chart), 18.10.41(1) 'need extremes, x10 of normal, never fade during the extreme', 18.10.41 exchange
latency/overload as a momentum flag (no data: B0), 18.10.38(3) size cohorts with x20 leverage get liquidated before TP (tsize: mid-size clip cohort), 18.10.49 illiquid coins move first (lead-lag:
testable on bnall: does a thin-coin basket lead BTC at 1h?), 18.10.55 daily all-buckets-negative = local bottom, not symmetric (M4e, already), 18.11.00(1) volume spike into highs = top, 18.11.00
Sep 24 / Santa Dec 18–23 (C1e), 18.11.01 anchored VWAP from macro lows (anchor at a nearby volume cluster if the extreme is thin), 18.10.59 Monday collar (W1, closed).
What he does NOT say in the 10x rule: the comparison base (previous rotation? median of last N?) — check the picture's numbers.
S2 b7 done (40/40 opened, 39 legible; 0 contradictions). New form M2f: the 4th row of his tape table (wa 18.10.54(3)) 'market orders becoming smaller & less frequent as price moves -> exhaustion'
 had no test. wa 18.10.42(2): his 10x trade-count rule promises 'reversal, or at least consolidation' → M2a scores 'trend ends', not reversal only. Rest maps to queued forms. Next: b8 (5), then v, p.
S2 b8 done (5/5, 0 contradictions). His clock is EET (wa 18.11.01(2): regular 16:30–23:15 = 09:30–16:15 NY) → every time he writes = NY + 7 h. New form C2g: Friday post-US-cash-close pump
 (wa 18.11.03 'most fridays have nice pump post cash'), not the same as friday_follow (UTC Friday → Saturday). All 8 image batches done: 253 images opened (88 on 11-23, 165 today; 4 unverifiable low-res scrolls), 0 contradictions. Next: S2 v (videos), p (PDF/truncated records).

## S2 v (think-through 2026-11-24 ~04:57 UTC, before opening anything)
22 videos (out/av: 22 contact sheets, 544 keyframes, transcripts, stored descriptions). Most are memes/audio. Tape videos to watch frame by frame: Mousetrap 3 (2:03), Mousetrap2 (24 s),
MousetrapTwitter (59 s) = M3 mousetrap source (S1e said: two tests of a level, the second with many times the volume; check that holds in every clip and WHERE the entry is: trap bar close,
next bar, or a resting bid at the level), 2022-07-16 DOM ladders (what moves in the book before the move: pulls/lifts = backlog W2), WhatsApp 18.10.20 cat 'Insilico casual fading routine'
(tape-table sequence, M2f), 18.10.20(1) quote stuffing. Plan: every contact sheet opened (22), keyframes of the 6 tape videos opened in full, transcripts read for audio-only ones.
What he does NOT say: in a mousetrap, the stop — below the trap bar's low? Look for it in the frames.
S2 v done (21 sheets + 4 full keyframes + 13 transcripts; 0 contradictions). The mousetrap clips are static ES footprints with narration: entry 'as soon as those buyers take over, right at
 that spot' after a high-volume test that cannot move price → M3e entry = first bar with positive delta at the level (was: close back above). The '18.10.20' cat video carries his tape table (M2f). Next: S2 p.

## S2 p (think-through 2026-11-24 ~05:00 UTC, before reading)
S1e read the 163 cited records only to ~500–900 chars. Rebuilt the cited set from insilico_rules.md + queue + pass3 (/tmp script, regex on tg:/wa ids): 189 records (superset), 140 longer than 500 chars,
91k chars unread past char 500. Read all of it; then the PDF remainder: HOFM case histories (p6–59), Artemis remaining 42 pages, Almanac calendar pages (skim for rules with a crypto analogue only).
Looking for: conditions/exits/stays-out stated late in long messages (the tail of a post is where he qualifies the rule), and numbers that fix a threshold.

## T2 (think-through 2026-11-24 05:05 UTC, before any run)
Source: owner 11-22 "he won't give everything on the platter". His examples are the only labelled data we have: each is a moment HE chose. What he does NOT say but must be doing:
he picks moments where something is EXTREME relative to the coin's own recent routine (volume, trade count, delta share, speed), at a LOCATION (prior low/high, POC, range edge, round number),
and he only posts winners (selection bias: an analog test (c) on unseen moments is the only honest use; the examples themselves can never be the test set).
a = the table (from S1/S2 per-image notes, dates hand-resolved; 2020 ones need T2e data), 1-min Binance path after each anchor: +15/60/240 min, 1/3/5 d, MFE/MAE, vs the same horizons from
every minute of the same coin-month (placebo distribution, percentile). No verdict from a: n ≈ 10–15, it is a description. Bias warning written now: exits he describes are partial
(TP1/TP2/origin), so the path, not a single return, is the fair description.
T2 a done (research/studies/is3_t2a.py, T2a__table.json): 10 examples, 8 tradable with minute data. His winners are good but not freakish: +1 d +3.5% mean, median 79th pct of their month's
 minutes (60 min: 87th). Counterexample: his 'Issa fart, not a bottom' stay-out (2021-09-21) rallied +6.9% next day. The 4 daily M4e days (all buckets negative) +1 d +3.6% mean, 4/4 > 0 at 3 d.
 Next: T2b feature vector (needs taker share / trade count / location per example; 1-min klines have n and tbqv → enough for a first pass on the 4 minute-level examples).
T2 b done (is3_t2b.py, T2b__daily.json): nothing distinguishes his 4 capitulation days from other >= -3% down days. 'All buckets negative' happens on 54% of such days and adds nothing
 (next 3 d +0.51% vs +0.55%). M4a reworded: dose = magnitude of the negative bucket shares, not the sign. Minute examples not pooled (3 families, 1–2 each). Next: T2c analogs (daily family: nearest
 neighbours in feature space on 2021–23 down days excluding his 4, forward 1–5 d vs random down days of the same size).
T2 c think-through (05:06 UTC, before running): explore only (2021–23), BTC/ETH/SOL (the coins with TSize). Pool = every coin-day with ret <= -3%. Features (standardised per coin over its 2021–23 down days):
 ret_z, range_atr, qv_z, n_z, taker, avg_trade, dd5, dd20, dd90, clv, peak_min, tsz_min, tsz_large. Events = the 15 nearest pool days (Euclidean) to each of his 4 BTC days, excluding +-5 d of
 any example; long at the day close, gross = simple 3-d return (his 2–5 d window, fixed now). Baseline = 5 matched pool days per event (same coin, same ret decile). Expected from T2b: ≈ baseline.
 Checks: causality = features on data cut at 2022-06-30 equal to full for earlier days; null = 20 coin-toss sign flips of the forward return per day, diff ≈ 0.
T2 e think-through (05:10 UTC, before downloading or running): 107 levels with creation ms (S1d), 85 BTC (BitMEX/Bybit inverse + Binance), 13 ETH, 6 LINK, 3 LTC; proxy prices = Binance USDT perps
 (inverse/perp basis a few $: noted, not corrected). Fixed now: side = support if level < close of the creation minute, else resistance; first touch within 30 d after creation (low <= level for
 support, high >= for resistance); reaction = simple return from the level at +15/60/240 min in the bounce direction; placebo levels = the mirror (same distance on the other side of the creation
 price, side flipped) and the same side at 0.63x / 1.37x the distance. Diff vs placebo by day-block bootstrap (is3_lib.stats). Dose: none available (labels instead: naked POC/VAH, single print,
 HVN, plain level). Duplicates (same price within 0.1% on the same symbol) counted once. Data: data.binance.vision monthly 1m zips 2020-06..2021-01 (+ existing 2021 file), separate dir data/is3/k1m_2020.
 What he does NOT say: the level is a resting order area, so the reaction should appear within minutes of the first touch; later touches are weaker (count first touch only).
T2 c: analogs = matched down days (diff +6 bp, MDE 353). d: one stay-out example; analogs better, n.s. e: 85 dated levels: price goes through them (−28 bp vs same-side placebo at 60 min, p .03), touch rate = mirror.
 First null run with 20 coin-toss copies read +67 bp: small-sample noise (400 copies: +15/+2/−2 bp over 3 seeds); is3_t2c now uses 400. T2 CLOSED OPEN (MDE rule). Next per queue.
