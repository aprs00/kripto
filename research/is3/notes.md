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

## T3 b (think-through 05:14 UTC, before any run)
tg:167: "can determine how strong the bounce or dive will be from initial mechanical spring after liqs". Spring = share of the climax move (10-min origin -> extreme) taken back by the close of
climax+3; decision at that close, simple returns 15/60/240 min in the fade direction, explore coins/dates only. Expect monotone: strong spring -> bounce continues (book empty, contrarians slip
through), weak spring -> dive continues. Failure mode to watch: mean reversion of the 3-min move itself (bid-ask bounce on a torn book, the M0 trap) would show as NEGATIVE slope at 15 min.
What he does NOT say: the spring is relative to the fall, and he waits for it (no entry at the extreme). Form a (model) after b, only if b shows a curve.
T3 a/c/d done (is3_t3a.py): ridge on 22 context features has real OOS IC (+0.075, t 3.2; shuffle −0.003) but it is the side rule (fade dumps, ride pumps; 78% agreement, −7.5 bp vs the rule on matched
 climaxes). Sizing by the prediction = sizing by volatility (same risk-adjusted t). Spring (b) is not a dose-response; a strong spring means the bounce is used up. Trees untried (not installed).

## T4 (think-through 05:17 UTC, before any run)
Applied to the LIVE trade, not L1: the ladder (T1k30, one-bar-late fills, e2_k-30, explore 2021–23), live exit = market 61 min after the fill. His words: "do a round quickly unless impressive
cascade", "they give u money u take it and run". Rules (fixed in is3_t4.py docstring): a stall (2 closes no new high + up-volume < down-volume over 5 min, from fill+2), a2 same not before 15 min,
b first new down-climax, c hindsight bounds. All decisions one bar late. T1j/E2c already showed: stops hurt, 3-h exits on cascade days do not hurt (h240 > h60) → prior: early exits LOSE,
because the bounce lasts hours. Kill/keep: an exit is kept only if > base with p < .05 in explore; otherwise the timer stays.
T4 done/closed OPEN (is3_t4.py, data/is3/t4_exits.parquet): on the live ladder fills every decision exit loses to the 61-min timer (stall −94, stall≥15 min −63, first climax −85 bp, lone-fill quick exit −3).
 Hindsight best close +385 vs +148: timing matters, but not his 'take it and run'. The live book keeps the timer. Untested idea worth a form later: LONGER holds on cascade fills (h240 > h60 in E2c).

## T5 a (think-through 05:19 UTC, before any run)
tg:226–234 / 103–107: he trades 1-min bounces anywhere, not only after liquidations: bid the previous range high, fade at reactive levels. Question: of all |1-min move| >= 3 sigma (24-h sigma,
no volume filter), which CONTEXT decides bounce vs continuation? Explore = COINS10 2021–23. Decision one bar late (close of move minute +1); outcome = 15/60-min simple return in the FADE
direction. Features (all known at decision): z, vm, taker share of the move minute (signed toward the move), trades per bp of move, distance to prior-UTC-day high/low and 7-d high/low in sigma units
(is the move INTO a level?), distance to the nearest round number (1/2/5 x 10^k), hour, 24-h trend (signed), breadth (other COINS10 with >= 3 sigma same sign in the same minute). Output: fade return
by decile of each feature with day-block CIs; a feature 'works' only if its curve is monotone and its extreme decile differs from the middle by more than the 13-bp taker cost.
What he does NOT say: the level matters (into prior high/low), size of the crowd matters (breadth), and he stays out of news minutes (breadth ≥ 5 ≈ macro).
T5 a/b/c done (is3_t5a.py, data/is3/t5a.parquet): 116k ordinary 1-min >= 3 sigma moves fade +2 bp over 60 min; 11 context features (level, round number, trend, breadth, taker share, trade size, hour)
 move it by < 5 bp in their middle deciles; two extreme cells (+17 trend, +12 beyond prior-day extreme) are 2 of 110 and not dose-responses. Ordinary shocks are noise; only the deep resting fill (T1) pays.
T5 d done: BTC-hedged residual does not bounce more (top idio decile +1.3 bp, diff −2.3, MDE 5.6).
T5 e: up-spikes continue, down-spikes bounce (= the side rule seen in T3). Dose in z (+10/+18/+21 bp at z 5/8/12) and breadth (lone +2.5, 2–3 coins +45, 4+ +22). Pre-registered T5e_upspike_z8_b2_h60
 (breadth cut chosen after seeing it: said in the prereg). Explore +27.2 vs −2.2 (p .002), hand-checked (ETH 2023-11-09 14:51, +3.1%). confirmT +39.2 vs +2.5, diff +36.7, p .075, both years +, MDE 59: FAILS p.
T5 e recorded (10:50 UTC): confirmC passes (p .009), confirmT does not (p .075, MDE 59; top-3 days = 74% of its sum, ex-top-3 +11 bp < 13-bp taker). Not CONFIRMED, vault untouched.
 Diagnosis: the payoff is a fat right tail (pumps that keep running); a 2-year time sample has too few such days. The idea is not dead; what would settle it is the forward ledger
 (a shadow book only after Z1). Candidate FEATURE for the ladder: do not offer (resting asks) against an up-spike with breadth >= 2.

## T5 f (think-through 10:55 UTC, before any run)
Source wa 18.10.24(2) = tg:173 (23 Mar 21, BTC 1m): "Much efforts... getting GTFO by lil efforts. Issa fade!" Two examples: biggest red volume bar then a green bar on low volume engulfing it;
the second red bar had a volume spike with a SMALL body. Mechanism (Wyckoff effort vs result): aggressive sellers hit a passive buyer (iceberg/absorption); price does not give way; when
sellers stop, a little buying lifts it. What he does NOT say: it must be at a low after a decline (where trapped shorts sit), the absorber is a resting limit (so the edge belongs to the
passive side = our ladder, not a taker chasing the green bar), and he would skip it when the decline is broad (macro selling: breadth). State view, not trigger: among minutes with
volume >= 10x the 24-h median at a 60-min low after a 60-min decline, the long return (one bar late) as a function of rr = range / 24-h median range (effort without result = small rr).
Expect: small rr bounces MORE than large rr (his claim). Prior from T1/T5a: large-range dumps (climaxes) bounce; ordinary shocks do not. So the claim is a NEGATIVE slope in rr.
Variants fixed now: (1) rr deciles, no confirmation, entry c[q+1]; (2) + his confirmation (next bar green, volume < 0.5x the effort bar), entry c[q+2]; (3) mirror at 60-min highs (short).
Horizons 15/60/240 min. Baseline = same coin, same vm decile, rr in the top half (the stated comparator). Kill: low-rr decile not > baseline, or < 13 bp taker.
T5 f done (is3_t5f.py, T5f__curves): effort WITHOUT result does not bounce (+1.8 bp at 60 min, well powered, MDE 5); effort WITH result does (+17, the climax fade T1 already trades). His confirmation bar
 makes it worse. Slope opposite to his claim. Unstated condition I could imagine (absorption at a level) was already flat in T5a (levels do not move ordinary fades). Not added.

## T5 g/h (think-through 11:00 UTC, before any run)
Sources: wa 18.10.51 (Jan 21 2022 dump: "almost all selling was closing of positions ... everyone thinks it's too late to short", OI -5.5/-7.7%, "positions placed at the fattest side ...
puked down for repricing"); tg:199–203 + 12 Exocharts templates with an NL/NS panel (net longs / net shorts = OI change split by taker side); tg:203 "wait for it to rotate ... trapped tards puke
and u ride the momentum". Mechanism: a fall on FALLING OI = longs leaving (puke: forced sellers done when it stops -> bounce, no fuel left for more); a fall on RISING OI = new shorts (fuel for a
squeeze later) OR longs adding into the fall (trapped: OI up while takers BUY and price still falls = passive sellers absorb them -> they puke later -> continuation). What he does NOT say:
which horizon; that the split matters only for LARGE moves; that the trapped side's stops sit just beyond the move (so continuation should show within hours, not days).
Design fixed now: clock-hour bars from 1-min klines, 10 coins, explore 2021-12..2023 (BTC from 2021-01). Event = |1-h return| >= 2 sigma (30-d hourly sigma, shift 1), both directions, side
in the FADE direction. Decision 5 min after the hour (OI snapshot lag), simple returns 1/4/24 h. g: curve of the fade by d(OI) over the hour in its own 30-d sigma (dose), plus size dose.
h: four cells by sign(dOI) x sign(taker delta relative to the move): "trapped" = OI up and takers leaning AGAINST the move (buying a fall); claim: trapped -> continuation (fade loses).
Baseline: same coin, same move-size bin, other cells (matched). Kill: no monotone dOI curve and no cell differing from its matched baseline by > 13 bp at 4 h.
T5 g/h done (is3_t5g.py, T5g__curves; explore card T5g_fall_oiup_short_4h, not pre-registered): puke falls (OI down) bounce like any fall. Falls on rising OI continue (-39 bp top decile at 4 h)
 but only in 2022 and ex-top-3 ≈ 0. Trapped cells (OI up, takers against the move) have 99–339 events at the 1-h scale: MDE > 200 bp. What would make NL/NS work: minute-scale OI (we only have 5-min
 snapshots) and range bars as on his footprint; the 24-h continuation of 'OI up + takers pushing' is the flow-momentum effect already known.

## M0 (2026-11-24 10:56 UTC)
a/b done (is3_m0b.py): micro bars match 1-min klines to 1e-7 on volume; 24 bad coin-days listed in research/is3/mbars_bad_days.json (duplicated archive trades ETH/SOL 2022-09-11..13, a +47% bad print
BTC 2022-09-06 17:12, partial archives). M-forms: load that file and drop those days. Rerun is3_m0b after c to extend the list. c: unit is3-m0 started 10:53 (2024-01..2026-10, ~20 days/min
-> 3-4 chunks of 45 min; restart with the M0 command, --start 2024-01-01 --end 2026-10-31).

## P1 gap fill (think-through 11:00 UTC, before any run)
Sources: tg:29–38 (Jan 2021 thread on profiles: "U see gap u fill gap, price wants to be normally distributed"; tg:33 "We slip thru areas composed with high volume. We consolidate in areas of low
volume", boxes where a later day's bulge sits in an earlier day's thin section "key to hole"); wa 18.10.31(2) salad profile thread ("flow clustering ... location where price sticks / is skipped").
Earlier: single-print bands fill like placebo bands (is2_profile), so the LEVEL as a target is dead; the open question is the DISTRIBUTION claim: does the next day's volume go to yesterday's thin zone
more than to an equally distant zone? What he does NOT say: thin zones at the range TAILS are just far away (distance confound) -> placebo = the same bins mirrored around today's open (same distances);
the thin zone he draws is INSIDE the range between two humps (form f), and he expects it on the days after a trend day (two balance areas), so dose = valley depth and hump separation.
Fixed now: 1-min klines, volume spread evenly over each bar's range in 10-bp log bins, UTC days, COINS10 2021–23. a: share of today's volume in yesterday's least-traded third of its range bins
vs mirror; same for the most-traded third (his "slip thru high volume" predicts LV > mirror and HV < mirror). f: bimodal days (two humps each >= 30% of POC, valley <= 50% of the smaller hump,
>= 15 bins apart): next-day volume share in the valley band vs its mirror band; dose by valley depth. b: nearest interior LVN from the open reached before the same distance the other way
(random walk 50%) vs a placebo node set 8 days earlier at the same distance. Verdict needs effect beyond the mirror with day-block CIs; trade forms (d) only if a/f show something.
P1 done (is3_p1.py, is3_p1cg.py): the opposite of gap fill at both scales. Next day / next hour put LESS volume into the prior period's thin third (-0.86 / -0.43 pp vs the same bins mirrored around
 the open) and MORE into its busy third (+2.5 / +1.2 pp); thinnest bins most avoided (dose runs the wrong way). Valleys of bimodal days, LVN first passage (49–50%), delta gaps (= volume once volume
 is controlled) and 'approached but not filled' (n 198, toward not away, p .3) add nothing. Unstated condition tried: valley between humps (his picture), hourly salad (his thread). Closed DEAD.

## P2 balance laws / session profiles (think-through 11:05 UTC, before any run)
Sources: tg:288 (his "10 laws of market dynamics" table: accept into balance -> other side; edges reject until proven; imbalance seeks an older POC; what doesn't happen matters), tg:52–57
(Mar 12 2021: "lot of time? lot of volume? leggo" — fat TPO+volume at the lows -> up, at the highs -> down; "always buyers at the top, sellers at bottom, mostly stops blew" = trapped), tg:49–50
(time and volume POCs disagree -> "fuckery brewing"), tg:15 (session TPOs with IB, R/F), tg:133–134 (tails vs single prints differ), tg:253–254 (R/F 0 = symmetric normal profile).
What he does NOT say but must be doing: he reads a balance as a multi-day composite (days whose value overlaps), so an "edge" is the composite's extreme, not yesterday's VAH (pass 2 already
killed yesterday's VAH/VAL/POC as levels); an edge holds while the trapped side's stops are not yet run, so the claim is conditional on how much time built up there (law: time at the edge ->
break). Distance confound again: compare every level with the same construction from 8 days earlier moved to today's price (pass-2 placebo), and report first-passage odds vs random walk.
Order (budget): a + b in one harness (3-day overlapping-value composites, first touch of its high/low from inside, reject = back 0.25 width inside before 0.25 beyond, and the build count of
the 6 prior half-hours near that edge as b's dose), then g (poor vs tailed lows, retest within 5 d, matched by distance), f (close through the 20-d composite POC vs through the 20-d median close),
j (session IB first touch vs 37% offset), i (TPO POC vs volume POC gap -> next-day range). Explore COINS10 2021–23 only.
P2 done (is3_p2.py, P2{ab,gfi,jh,del,ck}__explore): 12/12 forms. Every profile level is, if anything, broken/avoided MORE than its placebo: 3-day balance edges reject 43 vs 47%, IB edges 48 vs 52%,
 4-bp single prints fill 48 vs 51%, naked POCs reached 48.5 vs 53%. No dose anywhere (build-up, fatness, R/F, poor lows). 80% rule = random walk once unresolved trades are not counted as misses
 (bug in pass 2, corrected in findings). Unstated conditions tried: multi-day balance instead of yesterday, his 4-bp resolution, OI falling at the break, time vs volume disagreement. Closed DEAD.

## C1 calendar (think-through 11:16 UTC, before any run)
Sources: tg:98, 181–182 (lunar / equinox remarks), wa 18.10.24(1) ("Moon at fall equinox is not really normal ... check charts for historical data"), 18.10.24 (Chinese New Year effect), 18.10.28(3),
18.11.00, 18.10.40(1), 18.11.02(1); the Almanac PDF he shared (down Friday / down Monday p120, tax-loss free lunch p175, first day of month p139/p226, triple witching).
Mechanisms worth a prior: turn of month (salary/DCA inflows, fund rebalancing), option expiry (dealer hedging pins price before, releases after; Deribit monthly = last Friday 08:00 UTC),
FOMC (risk premium drift before macro announcements, documented in equities). Lunar / September / Santa / CNY: no mechanism I believe; few observations -> effect + MDE only.
What he does NOT say: calendar effects are filters, not trades (he uses them to stay out or to size). So every result reports the effect on the EW top-30 and BTC, daily returns, explore 2021–23
then confirmT 2024–25 only for a form whose explore effect beats costs AND has an MDE below it. One table for c with BH-FDR inside it, decided before looking.
Data: bnall 1d (clean universe), EW top-30 by trailing 30-d quote volume (shift 1); BTC hourly from 1-min klines for the hour-of-week table.
C1 done (is3_c1.py, C1{a..i}__explore, dates in C1_dates.json): ~25 calendar tags + 168 hour cells; 0 FDR survivors; no tag's explore effect exceeds its own MDE, so no confirm card was run.
 Largest, all p .05–.07 and underpowered: FOMC day before/day (+122/+218 bp EW30), first day of month (+127), turn of month (+62). Lunar sign flips between eras. Process slip: my print
 functions showed the 2024–25 column for a and g before I had decided they qualified; noted in the form results; neither qualified anyway. Next time print explore only.

## C2 time of day (think-through 11:21 UTC, before any run)
Sources: tg:66–69 (kill zones = liquidity events; "all jump in ... few hours of action ... low testosterone time until next open, on which we return to high volume collar to continue action of
previous session; all in between main killzones ... is noise filler that gets filled back before next session"), wa 18.11.01(2) (legacy CME break times: break 23:15–23:30, full stop 00:00–01:00, pre-market
16:15–16:30 in his EET zone = 16:15–16:30 / 17:00–18:00 NY), wa 18.10.35 (Monday US-open TWAPs; "lose consistency"), wa 18.11.03 ("most fridays have nice pump post cash", Fri 23:00 EET = 16:00 NY),
wa 18.10.26(4) (moves "during illiquid hrs ... seen this game before"). (wa 18.11.03 (1)/(2) also advocate exploiting weak contracts: ignored, not research.)
What he does NOT say: the filler move is filled back TOWARD the previous session's busiest price, i.e. the target is a level, not a return sign; kill-zone continuation should depend on the zone's
volume (a zone without participation is not an event); illiquid-hour pumps are faded only when the book refills (the next liquid hour), so the horizon is "until the next zone".
Fixed now (explore COINS10 2021–23, NY time with DST): zones London 02:00–05:00 NY, NY 07:00–10:00 NY; filler = 05:00–07:00 NY. a: sign(London zone) x NY-zone return vs every 3-h window x the 3-h window
starting 2 h after it (placebo, same geometry). b: filler return sign x NY-zone return, and NY zone reaching the London zone's volume POC before the mirror distance. c: 17–18 NY and 16:15–16:30 NY
(to 2021-06) per coin per year vs other hours. d: 1-h moves >= 2 sigma in the coin's least-liquid quartile of week-hours, fade until the next liquid hour, vs same-size moves in liquid hours.
e: taker imbalance and return in half-hour h vs the same half-hour yesterday (lag 48) and vs lags 47/49 (placebo). f: Mon 13:30–17:00 UTC drift and imbalance vs Tue–Fri. g: Fri 16–20 NY vs Mon–Thu 16–20 NY.
C2 done (is3_c2.py, C2__explore): kill zones do not continue (NY reverses London -6 bp, n.s.), filler is not given back, the London collar is not a NY-zone target (49%), illiquid-hour moves fade LESS,
 same-clock half-hours reverse by 1 bp (opposite of Heston), no Monday TWAP footprint. Two positive but underpowered drifts: CME break hour +4.6 bp (decays after 2021) and Friday 16–20 NY +21 bp
 (MDE 38) -> belongs to FF1 (friday_follow). Closed OPEN for g only; the kill-zone story itself is dead.

## P3 naked / composite POCs (think-through 11:25 UTC, before any run)
Sources tg:29, 38, 44–47 (Mar 12 2021: a single-print window failed to fill "because it's harder to break down, sp was left by stops triggering on composite poc"; "slid thru huge volume area ... automatic
reaction and mechanical longs after price hit the POC of this consolidation area"; "all profile levels very reactive"). Already known: yesterday's POC reacts like a fake level (pass 2), naked POCs are NOT
destinations after imbalance days (P2c 48.5 vs 53%). What he does NOT say: the reaction should come from resting orders of the people who built the volume (they defend their average price), so it
should be strongest for OLD, FAT, untouched levels on higher timeframes (weekly / monthly), and at the FIRST touch only. So the fair test is first touch of naked weekly/monthly POCs (d) with a mirror
placebo, plus the daily ones (a, c) and the 20-day composite as a magnet vs plain mean reversion (b).
Fixed: a level is evaluated once, at the close of the first day after its period, if untouched that day (naked); forward window 5 d (daily), 10 d (weekly), 20 d (monthly). Touch prob vs mirror level
(same distance, other side). Reaction at the first touch: 60-min return one bar late signed away from the approach, and +-30 bp first passage; vs the mirror level's first touch and vs the daily open.
P3 done (is3_p3.py, P3__explore, P3_sidematched__explore): naked POCs are touched less than mirror levels (daily −2.7 pp, monthly −9); not magnets after 2–5 σ either. First touch of a daily naked POC bounces
 +15 bp (mirror matched on side and distance −1, p .09); the dose runs with distance travelled and AGAINST node fatness, so it is the generic bounce after a long move. Weekly/monthly VAH/VAL 'reactions'
 were an approach-side artifact (lesson: any level-touch reaction must be compared within the same approach side; touches from above and below have different drifts). Closed DEAD.

## O1 oscillators (think-through 11:30 UTC, before any run)
Sources tg:86, 91–92 (5-panel template: uptrend = buy oscillator dips that turn up, sell above +40; "if indicator reaches 100 it doesn't mean it has to reverse, it means stupidly bullish ... red flag it
won't reverse is multiple tools signalling down and price still rising ... 3–4 signals to reverse in close proximity -> it's full of shit and we keep tanking"), wa 18.10.36/37 ("Quick guide ... How TA
guys fucked up": RSI out of its mean = turbo bull; full-retard mode, standard behaviour not expected). Mechanism: an oscillator is a transform of past returns; pinned = strong recent trend; his claim is
time-series momentum dressed as RSI. What he does NOT say: whether RSI adds anything beyond the past return itself. So the baseline for every form is the same coin at the same trailing-14-bar return
decile without the RSI condition. Failed-signal count (c) is the only part that is not a plain return transform. e = filter: does the live ladder's dump-fade do worse when the coin's daily RSI is pinned
(he says 'do not fade' in that state)? Explore COINS10 1h/4h 2021–23 and bnall top-100 daily 2021–23.
O1 done (is3_o1.py, is3_o1_card.py): RSI is a transform of past returns and adds nothing stable to them (a, b). His 'reversal signal' (RSI back to 50) is followed by the trend resuming at 1h/4h/1d
 (d; long card p .18, not pre-registered); 3 failed sell signals at 1h precede a drop, not continuation (c). Filter e (ladder fills by daily RSI) passed explore (+243 vs +68) and FAILED confirmT (+183 vs
 +137, p .60): a 2021 bull-year artifact. Lesson: a filter on a book that already works must be compared within years before pre-registering (2021 carried the whole gap).

## O2 his own indicators (think-through 11:35 UTC, before any run)
Sources tg:90, 98–100 (Hull Suite = one HMA(55) vs its value 2 bars ago; VZO vs RSI: "RSI at an extreme while VZO barely moves = sham pump"; camarilla = his mentor's tool), Crayons V3.4 / FSVZO V2.8 guides
(climax, invalidation 'hit rate as impressive if not more', H/W failed extensions, VZO alerts and midline). Mechanism candidates: VZO is signed volume / volume = taker-flow proxy (flow persistence is real on
Binance); exhaustion / failed-extension bars = stop runs at extremes; the rest are price transforms (expect nothing beyond the past return). What he does NOT say: his tools are filters he reads together
(confluence, X1), and a label is only acted on at a location; so each form here is a single-tool screen, and failure means 'not alone', not 'useless in confluence'.
Fixed now: explore COINS10 1h/4h + bnall top-100 1d, 2021–23; baseline = same coin, same trailing-14-bar return decile (as O1); horizons 6/24 bars (1h), 6/18 (4h), 5/10 (1d). VZO = 100·EMA14(sign(dc)·v)/EMA14(v);
FSVZO proxy = WMA4 of VZO (causal), alerts |VZO| > 40/60/80 (dose; VZO is bounded at 100 so his 60/85/105 scale is mapped down). Leledc: count of close > close[4] (and <) > 6, then an opposite-colour
bar at the 30-bar extreme. Camarilla from the prior UTC day (H3/L3 fade, H4/L4 break) vs levels at 0.63x/1.37x the distance. Deferred: f (Crayons climax labels), g (1-min Fisher), h (regression channel).
O2 9/13 forms done (is3_o2.py, O2__explore; peak RSS 1.94 GB - at the limit, run alone): none of his indicators beats 'same coin, same past return'. Wrong-way signals: end of an abnormal-selling VZO alert
 is followed by more selling (flow persistence), invalidated exhaustion bars lose at 1h, daily bearish Leledc bars precede rises. Only Hull55 turns at 1h show +9..+20 bp gross (p .03-.11), absent at 4h/1d.
 Bug caught before recording: mixed-side forms with one-sided matched baselines (now asserted in the script). Left: f (Crayons climax labels), g (1-min Fisher), h (regression channel), j (H/W failed extension).
O2 j done (is3_o2.py j): an H (failed new high in an uptrend) is followed by less upside than ordinary uptrend bars (+28 bp at 6 h, +71 at 24 h on 4h, p .003) but not by a fall: shorts still lose.
 Feature idea for F2 (trim trend longs after an H), not a trade. O2 left: f, g, h.
O2 g done (is3_o2g.py): 1-min Fisher turns are worth 0–3 bp gross (MDE ~1 bp), −10..−16 net. O2 left: f (Crayons climax labels, vague), h (regression channel vs hand-drawn placebo).
O2 h done (regression channel = placebo channels), f skipped (no formula in the guide; d and k are its public analogues). O2 closed DEAD: ~70 cells, 3-4 at p < .05 as chance predicts, several wrong-way.

## N1 round numbers (think-through 11:46 UTC, before any run)
Source tg:119 (Flood's 'hundy roll' thread he reposted: buy at 97–98 expecting a run through 100 to 106; "human beings are dumb enough to shoot for round numbers"), wa 18.10.24(1) ("current action is mechanical
reaction to 40,000"). Mechanism: limit orders and stops cluster at round prices (documented in FX/equities: Osler); targets attract, then stops beyond them extend the move (overshoot). What he does NOT say:
'round' depends on the coin's own price scale -> use one-significant-digit levels (d x 10^k); the placebo must have the same geometry, so placebo = the level 37% of the way to the next round level.
Lesson from P3: compare touches within the same approach side. a: daily bnall half-0 coins 2021–23, close entering 2–3% below a level from below while close > close 20 d ago: +6% before -3%
(daily first passage, 30 d; random walk ~33%) real vs placebo. b: COINS10 1-min, first touch after >= 2% away, 60-min return one bar late away from the approach, side-matched real vs placebo.
c: first daily close 1–2% beyond a level after crossing: back to the level within 5 days, real vs placebo.
N1 done (is3_n1.py): round numbers behave like placebo levels: hundy roll 35 vs 32% (RW 33), overshoot-return 93 vs 92%, first-touch bounce weaker than placebo (−21 bp, p .06 = runs through). Closed DEAD.

## N2 spot vs perp delta (think-through 11:50 UTC, before any run)
Sources wa 18.11.00(2), 18.11.02(2): a rally led by spot buying (with perp delta negative = perps shorting into it) is the strong kind; perp-led rallies are leverage and fade. Mechanism: spot buyers are
unlevered and do not get liquidated; perp-led moves are paid back by funding and liquidations. Not on the server: spot taker flow. Data = Binance spot 1h klines (taker-buy quote volume) from
data.binance.vision/data/spot (same public archive host as the futures files; flagged in STATUS). Unit is3-n2 started 11:49 (30 top coins 2021-01..2025-12, 1 req/s). Forms once it lands:
a share of the 24-h up move's taker imbalance from spot vs perp -> next 24/72 h; b his exact case (spot-led rally with negative perp delta); c cross-sectional daily spot-minus-perp delta, and as a flow feature.

## N3 tape behaviour (think-through 11:53 UTC, before any run)
Sources tg:93, 163, 239, 289; wa 18.10.28(1) (change of character picture), 18.10.44(2), 18.10.54(3) ("in control: the one that absorbs"), 18.10.50(1) (last minutes painted), 18.11.01(1) (his AVWAP).
Mechanism worth a prior: absorption (f) = aggressive sellers met by a passive buyer; if price does not fall under heavy selling, the passive side is bigger -> up next. Known context: Binance taker flow
PERSISTS (flow book), and T5f found effort-without-result does not bounce at 1 min; f is the multi-day version (residual of price on delta). b/e are exhaustion stories (a persistent buyer tiring,
a record-volume reclaim of a broken low). What he does NOT say: absorption only means something when the delta is large relative to the coin's own normal, so the dose is the delta's z-score and
the price residual; and it should hold cross-sectionally (coin vs coin the same day), not just in time. This session: daily forms b, e, f on bnall half-0 top-100 coins 2021–23, baseline = same coin at the
same trailing-14-day return decile (O1 harness). Remaining forms (a, c, d, g–k) next session.
N3 b/e/f done (is3_n3d.py, is3_n3d_card.py): absorption passed explore (+146 bp vs matched over 5 d, dose monotone, 2 of 3 years) and failed both confirms (2024-25 -72, unseen coins +47 p .27).
 Second filter-like idea today that lived on 2021-22 only. Pattern worth keeping in mind: daily explore cards dominated by 2021 rarely survive; ask for every explore year to be positive vs matched before
 pre-registering a daily form (O1e and N3f both had one null/negative explore year). Remaining N3 forms: a, c, d, g, h, i, j, k.
N3 c/i/j done (is3_n3m.py): delta-flip change of character too rare (48 at 1h); HTF trend filter makes no significant difference to 1-h momentum (+5 bp, MDE 10), as he claims; painted last
 minutes are not faded (the push continues, same as at minutes 25-30). N3 left: a, d, g, h, k.
N3 k/g done (is3_n3kg.py): non-overlapping impulses carry a little at 1h (+29 bp vs matched, p .06) with an anti-dose in efficiency; his overlap exit adds nothing; the change-of-character bar does not
 reverse. N3 left for next session: a (successive swings), d (weekly/monthly AVWAP distance), h (his AVWAP anchors). Then N4, N5, the M-items (need M0c), F, X, L2 (due 12-05).
N3 a done (is3_n3a.py): shrinking swings mark a weaker trend (counter-trade +4 vs -10 bp after a strong swing, p .002) but never pay a counter-trade. Same shape as O2 j (failed new high): both are
 'trend is tiring' features for F2 (trim trend exposure), neither is a reversal signal. N3 left: d, h.
N3 d/h done (is3_n3dh.py): weekly/monthly AVWAP distance has no significant curve (regime shapes as he implies, n.s.); his 90-day-extreme AVWAPs react like random-anchor AVWAPs. N3 closed OPEN
 (absorption failed both confirms; shrinking swings and failed new highs are 'trend tiring' features for F2, unconfirmed).

## N4 lead-lag (think-through 11:56 UTC, before any run)
Sources wa 18.10.49, tg:114–116: illiquid coins move first (insiders / thin books show the move before BTC), and alts decoupling from BTC is a canary for a BTC move. Prior from the literature
(Lo–MacKinlay; crypto studies): large, liquid assets LEAD small ones (information arrives where liquidity is), so his claim runs against the prior; it could hold for idiosyncratic pumps but those
do not lead BTC. What he does NOT say: lead at which horizon; any lead must survive asynchronous trading (thin coins' stale prices make them look like they LAG). Fixed: 5-min bars, all coins with
1-min klines, static volume terciles (mean quote volume 2021–23, descriptive), explore 2021–23. a: cross-correlations thin->BTC vs BTC->thin at 5–60 min, plus a sign trade. b: daily alt-BTC
correlation drop (vs its 30-day mean) and thin-minus-BTC divergence -> next-day BTC |move| and direction. c: 1-min tail asymmetry (down vs up >= 5/8/12 sigma counts) per year.
N4 done (is3_n4.py): no lead-lag (thin coins do not lead BTC; nothing beyond a 1-bar bounce), correlation drops are no canary, thin-coin divergence points the wrong way (-22 bp, p .03).
 Dumps are sharper than pumps at >= 8 sigma (down/up 1.2-2.0, growing each year) — true, and already what the ladder trades. Closed DEAD for lead-lag.

## N5 empty moves / volume on rallies (think-through 11:58 UTC, before any run)
Sources wa 18.10.58, 18.11.00(1), 18.10.35(1) ("not much of a squeeze, too little volume, squeeze would be sharp volume candle"), tg:231, 286–287; R6 "a low on thin volume is not a bottom". Pass 2: empty
5-min moves (low volume) faded +66 bp in 2021–23 but +4 in 2024–26 (unstable). What he does NOT say: 'thin' should be measured by participation (trade count) not notional, because one whale fill
looks like volume; a drift on falling volume = no sellers (continuation) only if it is a drift (many small bars), not a jump. Fixed: COINS10 1h/4h (and 5-min for a), explore 2021–23, baseline = matched
(same coin, same move-size bin or same trailing-return decile). d (HL L2 thin-book) waits for L2 history (>= 2026-12-10).
N5 a/b/c done (is3_n5.py): empty-by-trade-count moves are not refilled; volume on rallies says nothing at 1h/4h; thin-volume lows ARE undercut more (84 vs 75%) but price is higher 24 bars later
 (+230 vs -3 bp at 4h): the undercut is a stop-run, not a continuation. Candidate idea (not a form yet): buy thin-volume 4h lows with a stop BELOW the likely undercut. N5 d waits for HL L2 history.
N5 e (added, tested once): thin-volume 4h lows passed explore even under the per-year rule (all 3 years positive) and failed both confirms (-24, -9.5 bp). Third 2021-heavy explore that died in confirm today:
 the per-year rule is necessary but not sufficient when one year carries most of the magnitude. Next session: N5 d waits (HL L2 >= 2026-12-10); M-items need M0c; then F0/F1/F2 (two 'trend tiring' features to test as filters), X1, L2 (due 12-05), N2 (spot data landing).
Units at session end (12:00 UTC): is3-m0 (M0c: BTC 2024-01..2026-10 done 1035/1035, ETH 103, SOL 0; ends ~12:24, restart with the M0 command, --start 2024-01-01 --end 2026-10-31; then rerun
 is3_m0b to extend mbars_bad_days.json), is3-n2 (spot 1h, 7/30 symbols so far; ends <= 12:33; restart: systemctl --user reset-failed is3-n2; systemd-run --user --unit is3-n2 -p Nice=19 -p MemoryMax=800M
 -p RuntimeMaxSec=2700 --working-directory=$HOME/kripto .venv/bin/python -m research.studies.is3_n2_download — resumable).

## M1 rotation momentum on range bars (think-through 13:00 UTC, before any run)
Sources tg:199–223 (range-500 footprint sequence on XBTUSD, 7 size groups; tg:203 "wait for it to rotate ... trapped tards puke and u ride the momentum"; tg:216 "price go up, ts green, ts
becomes bright red? its over", sometimes an 8 h bleed, sometimes quick fade), S1e/S2 picture notes (the boxed green bar is THIN and FAST). Mechanism: when every size group lifts offers at once the
buying is not one actor but a crowd, shorts are being forced out (trapped) and the move feeds on itself until a bar where every group sells. Prior: Binance taker flow persists (flow book), T5f found
effort-without-result does not bounce at 1 min, so continuation after one-voiced flow is plausible but tiny per range bar. What he does NOT say: he is not paying 13 bp on 10-bp bars: at 0.1% bars any
edge must beat costs over the whole ride, so the hold (green run -> first all-red) must be many bars; he exits into strength on the red bar = a passive exit is possible; the colour only means something
relative to price (green with price not rising = absorption, M3). Data: BTC ETH SOL micro bars 2021–23 (explore), groups = tsize author7, a bar is all-green when every non-empty group has delta > 0
and >= 4 groups are non-empty. Baseline for a = the same exit rule entered after the same number of consecutive UP bars that are NOT all-green (isolates the colour from the price run), m = (width, run, side).
Change my mind: all-green rides beat plain-up-run rides by > costs with a dose in run length, every explore year. Sub-1-s bars reported separately (M0 trap); entry one micro bar late as the delay stress.
M1 null check (13:25): colour labels shuffled within day, 2022, 0.43% bars. First baseline (up-run bars not green) FAILED the null (+12 bp): range bars mean-revert, so events must be up bars
 and the baseline must match the prior price-run length; then still +4 from day composition (green-heavy days are up days). Final baseline = same coin, same DAY, same side, same prior
 up-run length (L.matched m = day_side_pl): null +1.2 / -0.4 / +5 bp (r = 1/2/3). Lesson: on range bars a colour test needs within-day, same-price-path matching.
 Hand-check BTC 2022-03-10 05:52: ride exits at the next all-red bar -50 bp, correct; four 0.43% bars inside one millisecond at 05:54:03.586 (torn book).
M1 a/b/c/e done (is3_m1.py, is3_m1c.py; data/is3/m1_explore.txt, m1c_explore.txt): riding all-green runs earns ~0 (+1.9 bp vs within-day matched, MDE 1.8, anti-dose in run length), the
 first all-red bar at a 24h/7d high is no better a short than any bar at the high, his thin-fast boxed bar goes the WRONG way (-6 vs matched). The one strong-looking curve (top |delta share| decile
 reverses -22 bp/1h) is the torn-book trap: 94-100% sub-1-s bars, gone at 5-min late entry outside 2021/SOL. RAM: is3_m1 explore peaked 3.1 GB (over the 2 GB rule; ran in-session, finished in 2 min);
 is3_m1c keeps float32 features, 0.83 GB. Next M1 form: d (adaptive size groups) as a variant of a.
N2 think-through, part 2 (16:58 UTC, before any run). Source re-read and image opened (1 of 2 images; the other, 18.11.02(2), is the CT longs/shorts framework, not about delta): Dec 2021,
 "huge negative volume deltas in the parabolic leg during the main run to 50k, derivatives red as f ... it's just spot hedges. Seen many bears perish". Claim: in a rally, negative PERP taker delta is
 hedging by spot holders (or carry), not bearish conviction; bears who read it as bearish are the trapped side. What he does NOT say but must be doing: (1) judging delta relative to normal (perp
 taker ratio sits near 0.5, spot's has its own level), so each coin's spot and perp imbalance is z-scored vs its own trailing 30 days; (2) the hedge story needs SPOT buying at the same time (else
 negative perp delta in a rally is just short covering ending); (3) multi-day horizon (a "leg"), so hold 1 and 3 days, decision at the UTC day close, perp prices. Data: perp daily tbqv (bnall files,
 30 coins), spot daily = sum of spot 1h; days where spot and perp closes differ > 2% are dropped (LUNA after May 2022 etc.). Only daily resolution exists for perp taker flow on these coins.
 Samples: explore 2021-23 (30 coins), confirmT 2024-25; confirmC would need spot for coins 31-60, downloaded only after a prereg. Change my mind: spot-led rallies (D = zspot - zperp high)
 beat same-coin same-rally-size days by > costs over 3 d with a dose in D, every explore year.
N2 a/b done (is3_n2.py explore|checks): spot-led rallies earn exactly what same-size rallies earn (-17 bp vs matched at 3 d, curve flips by year); his exact case (rally + negative perp delta + spot
 buying, n=221) = matched (-1 bp), +98 vs negative-perp-without-spot (p .27, MDE 230): too few events. Null: raw sign-flip null is +57 bp for ANY long-only daily rule (simple-return convexity);
 run the null on event minus matched instead (clean here). Next: c (cross-sectional D rank; D as filter on flow).
N2 c done: XS spot-minus-perp rank -6 bp/1d (MDE 19); spot agreement adds +1 bp to perp flow momentum. Spot delta has no information beyond perp delta at daily resolution.
N2 d added (17:2x, before run): his "spot hedges" are cash-and-carry shorts, which only exist when funding/basis pays them. So the unstated condition is funding: rally + perp selling + rich funding
 (above the coin's own 30-day median) should continue; rally + perp selling + poor funding = real bears. Tested once, h1/h3, matched same coin same rally bin, and rich-vs-poor as a direct contrast.
N2 d done, N2 closed OPEN (17:35): carry condition (rich funding) + spot buying + perp selling in a rally +62 bp/1 d vs matched (all explore years +, p .22, n=179, MDE 132), 3 d flips; not pre-registered
 (fails "beats baseline", and a 2024-25 confirm of ~120 events could not see 60 bp). Path to reopen: spot for coins 31-100 (unseen = explore + confirm with 3x the events).

## M2 order velocity x10 (think-through, before any run)
Sources opened (3 images): wa 18.10.42 and 18.10.41(2) (BTC Nov 2020, ~16-point = 0.1% range footprint, 'Trades count' row: 826 -> 80 on consecutive up rotations at the top next to pdVAH,
 then a 40-point pullback and a range; 701 vs 100-250 neighbours on the capitulation bar at the low, then a 250-point rally), 18.10.42(2) (Discord 11/13/2020: "relative changes in trade count by 10
 times for rotation = change in order velocity = change in character ... if not reversal it signals consolidation start at least"). 18.10.29(1) (cat meme, "just needs order velocity") by description only.
Mechanism: trades per fixed-distance bar = aggressive orders needed to move price one rotation. A 10x jump = a crowd hitting into liquidity (capitulation / chase: effort); a 10x drop = the same
 distance covered by a handful of orders (vacuum, nobody left on the other side) or the crowd vanished. Either way the regime of the last bars ended: he predicts reversal OR lower volatility.
What he does NOT say but must be doing: (1) he only looks at it at a reference (pdVAH, day extreme, after a long run): b tests that; (2) the count is relative to the bar's own neighbours, so
 the dose is the log ratio, both directions; (3) on 2021+ Binance, sub-1-s torn-book bars give fake count drops (one sweep = few aggTrades over 0.1%), so report >= 1-s bars separately and enter
 one bar / 5 min late; (4) he would fade with a limit order, not chase: test the reversal outcome AND the consolidation outcome (next-hour range vs matched), the latter as a feature for F-items.
Fixed: BTC ETH SOL micro bars 2021-23 (explore), widths 0.1% (= micro bars, his size), 0.2%, 0.43%; n = aggTrades count (taker orders, closer to 'orders' than raw fills). Event bar = the one AFTER
 the ratio jump/drop is known (decision at its close). Outcomes: 'reversal' = return against the event bar's direction over 15 min / 1 h / 4 h; 'calm' = next-1h high/low range / previous-1h range.
Baseline = M1 harness: same coin, same UTC day, same bar side, same prior same-direction run length (m = day_side_pl), non-event bars. Null = trade counts shuffled within each day.
Change my mind: |log ratio| >= log 10 bars reverse by > 13 bp vs matched at 1 h with a dose in the ratio (5/10/20x), on >= 1-s bars, every explore year.
M2 a/c/d done (is3_m2.py; data/is3/m2_explore.txt, m2_null.txt): 5-20x count changes are the NORM at 0.1% bars on 2021+ Binance (63% of SOL 2021 bars); no reversal vs within-day matched from
 5 min late at any width or dose; drops look like +10-15 bp reversals from the close but are 82-100% sub-1-s torn-book bars. Next-hour range 2-5% lower after events (null 0): real, tiny (F-feature).
M2 b explore: at a 24 h extreme, >=1-s 0.43% bars, LONG side only (down burst at the low = his 701 example): +50 bp vs matched (p .001, n=600, 2021/22/23 +82/+19/+63, BTC/ETH/SOL +17/+15/+85,
 dose 27/50/42); raw +96, +16 at crash costs; the same on sub-1-s bars -6; short side (burst at the high) -14. ~36 cells searched; overlaps L1. Pre-registered M2b_long10_w43 (+_raw); confirmT
 2024-25 after M0c SOL lands. pdVAH/VAL proximity: nothing (n.s., mixed signs).
M2 e/f think-through (17:0x, before run). e source opened (wa 18.10.41, Dec 2021 tweets): "orders pile in as lag increases in the trade engine; as long as it's clogged assume the same direction; when
 it unclogs ..." (he leaves the punchline open: the push is over). Proxy without latency data: trades/min vs the coin's trailing-24h median (x). Clogged = x >= K and above the previous minute; unclogged
 = a burst (max x of the last 15 min >= K) now below half its peak. Side = direction of the last 15 min. f: his tape table "market orders smaller and less frequent as price moves -> exhaustion".
 Both on COINS10 1-min klines 2021-23, enter at the close of the next minute (1 min late), 15/60/240 min; baseline = same coin, same year, same move-size decile (|15 min| or |60 min| return / sigma).
 What he does not say: the engine-lag edge was an FTX/BitMEX phenomenon (overload = mark price stale); on Binance 2021+ the matching engine rarely clogs, so I expect at most the generic
 flow-continuation inside bursts, and the dose must be in x.
M2 e/f done (is3_m2m.py; data/is3/m2m_explore.txt): engine-lag proxy backwards (clogged bursts reverse -5 bp/60 min, 2021 only; unclogging nothing, MDE 3); exhaustion row backwards and tiny
 (falling count+size +1 bp vs matched, rising count -5). Binance minute data has no 'clog' to read; the FTX-era mechanism is not in this venue's data. Only M2b_long10_w43 remains (confirmT pending SOL).

## M3 mousetrap / absorption / trapped cohorts (think-through 17:05 UTC, before any run)
Sources re-read (records, video descriptions + transcripts as stored; videos not re-watched this session): tg:168 (tape table: absorption = frequent large market orders failing to overwhelm limits),
 tg:169-171 (three ES footprint 'Mousetrap' videos: price bases on a level, a bar undercuts it with very heavy volume and small-trade selling, cannot progress, closes back up; enter "as soon as
 buyers take over right at that spot"; trapped shorts' stops print 1600/1000/683/1013 lots), tg:206 ("simpler version of mousetrap = basics of momentum trading").
Mechanism: stops and breakout sellers cluster just under an obvious level; a large passive buyer absorbs them; once sellers are exhausted the trapped shorts' stops fuel a fast rally.
 Prior evidence in this programme: N5 (thin-volume lows ARE undercut, the undercut is a stop-run, price higher later; failed confirms), N3f absorption (daily, failed confirms), M2b (a >= 10x
 trade-count burst on a slow down bar at the 24 h low rebounds +50 bp vs matched in explore; confirm pending) = the closest thing yet to his mousetrap.
What he does NOT say: (1) the level must be one that many see (prior-day low, weekly low, a multi-touch base), not any low; (2) entry is AFTER the failed test, on the first bar with positive
 delta near the level (a confirmation entry, not a resting bid), stop below the trap bar's low (risk known, small); (3) the second test's volume relative to the first is the dose (e).
Plan: e first (his narrated version, dose = 2nd/1st test volume), then a (level type + small-sell/large-buy split), b (absorption bar on range bars), c, d. Baseline = within-day matched
 (M1/M2 harness) and undercuts of the same level WITHOUT the volume burst. >= 1-s bars only; entry 1 bar / 5 min late.
M3 e done (is3_m3.py explore): prev-day-low mousetrap with a volume surge on the second test = placebo near-level entries (-13 bp/240 min, MDE 43), anti-dose. M3 b done (is3_m3.py b): absorption bars
 (takers against the bar) follow-through = matched (MDE 11); the one +71 bp tail cell is crash-day/thin-SOL wicks (188/597 on 2021-05-19). Next M3: a (level types + size split), c, d.
M2 b confirmT (17:1x): +65 bp vs matched (p .047, n=202, both years, every coin +) but ex-top-3 +12 < taker -> fails; 85% of the sum from 2025-10-10, 2025-02-03, 2024-04-13. It is the crash-day
 liquidation fade (L1/E1). M2 closed OPEN. Bad-day list extended to 2026-10 by rerunning is3_m0b (13 new BTC, 13 ETH, 4 SOL days; SOL 2026 still building). Lesson: on intraday long-the-dump forms,
 print the top-3-day share in explore too (explore had ex-top3 +31 of +50; confirm +12 of +65): crash days dominate every capitulation test.
M3 c/d done, M3 closed DEAD (17:1x): trapped small sellers no dose (MDE 51), large sellers below the level were right; volume at the bar's extreme = slight continuation (MDE 11). Pattern across
 N5, M1, M2, M3: on Binance 2021+ every 'trap / exhaustion / capitulation' footprint read either equals its baseline or reduces to the crash-day liquidation fade. Remaining M-items (M4-M7) should
 be judged with that prior: test the crash-day share FIRST (top-3-day share and the result with 2021-05-19, 2022-05/06, 2022-11, 2024-04-13, 2024-08-05, 2025-02-03, 2025-10-10 removed).

## F0 filter harness (17:2x)
Built research/studies/is3_filter.py + tests/test_is3_filter.py (4 known-answer tests pass). Usage: w, panel, slip = F.book(strategy, dataset, params); F.judge(name, w, panel, slip, mask, sample, side=None|+1|-1).
 One judge = 201 backtests (~4.5 min, 0.56 GB on bnall 1d flow): run F1/F2 judges in a unit if more than two. Real-book check: a random 80% mask cut flow's mdd -23.5% -> -16.4% at the 87th percentile
 of random masks (not a pass): every 'it cut the drawdown' claim must be read against that. Random masks' median dSR -0.24: cutting names costs Sharpe, so the bar is relative, not 0.

## F1 filters for the Binance books (think-through 17:2x, before any run)
Books: flow (lookback 3, cap .05) and xsmom (lookback 28, daily, cap .05) on bnall 1d (clean, survivorship-free), explore <= 2023; harness F0 (200 same-share same-persistence random masks).
b (L5 / liquidation-fade lesson): after a cascade day the market bounces (liquidation fade, E1/L1, M2b confirm: 85% of a capitulation edge sat on crash days), so a long/short book's SHORTS
 are what gets squeezed. Cascade day (fixed now): cross-sectional median daily return of the coins with a price that day <= -7%; block shorts for the next 2 days (dose: -5/-10%, 1/3 days).
 The harness zeroes the blocked shorts (exits them), stronger than 'no new shorts': stated.
c (R8 "a volume spike into highs = ran into sellers"): block longs in a coin whose close is its 20-day high on volume >= 3x its 20-day median (dose 2x/5x).
What he does not say: both are about WHO is trapped (late shorts after a flush, breakout chasers at a high); the filters only help if the book actually holds those positions on those days, so
 report how much weight the mask touches. Pass = dSR > 0 at >= 95th percentile of random masks, and the same sign in each explore year.
M0 closed (17:2x): c done, all three coins 2130 days to 2026-10-31; bad days now BTC 18 / ETH 20 / SOL 32, most new ones 2026-05-09..06-08 (archive volume mismatch) -> the vault loses about a month.
F1 b/c/d done (is3_f1.py; data/is3/f1_explore.txt, f1d_explore.txt): c backwards (blocking longs at volume-spike 20-day highs costs 0.5-0.7 SR, 0th pct: breakouts on volume are the best longs);
 d nothing (RSI-pin filters touch < 2% of weight, main variants fail); b's pre-set 2-day block fails but a 1-day block wins in both books -> g: thresholds -5/-7/-10% all + in flow, -7% every
 year + in both books (flow +0.86/+0.78/+0.34, xsmom +0.46/+0.49/+0.46; xsmom 99.5th pct of 200, p .009). Pre-registered F1g_{flow,xsmom}_casc7_1d; confirmT 2024-25 running (is3-f1c).
 F.judge now refuses confirm samples without a committed prereg (it had no such guard; test added).
F1 g confirmT (17:5x): FAILED both books (flow dSR -0.25, xsmom -0.32, every 2024-25 year negative). Next-day bounce after -7% cascade days: 2020-23 mean +61..+291 bp, 2024 -28, 2025 -150 (43% up).
 Third 2021-23 'bounce after a flush' result that dies in 2024-25 (O1 ladder-by-RSI, N5 thin lows, now F1g); the intraday version (M2b, 60 min) replicated in direction but only on 3 crash days.
 Honesty note: my diagnosis table printed 2026 too (7 cascade days, next day +228 bp); seen, not used, F1g is failed by its pre-registered confirm. F1 left: a (tsize breadth in flow), e (POC), f (round/poor low).
F1 a done (17:58): tsize breadth on BTC/ETH/SOL inside flow = random masks (dSR -0.05, 58th pct). F1 left: e (prior POC / value area) and f (poor lows) need intraday profiles for the
 whole flow/xsmom universe -> build from bn100 1h (hourly profile per coin-day; RAM: probe first) next session.
F1 e/f think-through (18:5x UTC, before any run). Sources: P5 (pass2 plan: "do the slow books' entries do better at a prior POC / inside vs outside value?"), R26 tg:119 (Flood's
 "hundy roll", seen via its stored description, image not re-opened: price trending into a round number is pulled through it and overshoots ~6%), P2g poor lows (unfinished extremes).
Mechanism: (e) Dalton: a close outside yesterday's value = initiative activity, inside = balance; a momentum book should earn more when it sides with initiative and less in balance.
 (f) round numbers attract resting orders/stops; R26 says momentum carries THROUGH, so the book's shorts just below a round level are the trapped side; poor (single-print-free)
 extremes are 'unfinished', so a long whose prior-day low is poor should face a retest.
What he does not say: the location only matters for NEW entries near the level and when the level is fresh (one day old); the harness masks positions per day (exits them), stated.
Build: per-coin day profiles from bn100 1h (klines_1h_all, 698 coins, per-coin reads, no wide panel): 30 log bins over the day's range, hour qv spread uniformly over the bins
 it covers; TPO = hours touching a bin; POC, VA(frac). Day d's profile ends at day d's close = the bar the book trades at: causal. Coins without hourly data: unfiltered (report coverage).
Forms: e1 block positions against location (long & close<VAL, short & close>VAH), e2 block positions while close inside VA, e3 (Dalton's responsive reading, the opposite) block
 longs above VAH / shorts below VAL; dose VA 50/70/85%. f1 R26: block shorts within 1/2/3% below the next round level (1,2,5 x 10^k); f2 block longs whose prior-day low is poor
 (bottom bin touched by >= 2 hours) and shorts whose high is poor. Pass = F0 rule (dSR > 0, >= 95th pct of random masks) + every explore year + in both books (flow, xsmom).
Prior: P1-P3 found profile levels = placebo levels on COINS10 minute data, so I expect nothing; the filter question is still separate (does location change the BOOK's P&L).

## M4 capitulation with adaptive buckets (think-through 19:0x UTC, before any run)
Sources re-read (tg:274-279, 283-284 as stored text/vision descriptions, not re-opened; wa 18.10.55-57 have no stored text, their content is known from S2 b3 which opened them):
 TSize = 7 size groups, each day's delta per group; "it fixes on close ... trend trading systems is close only"; "each size has its own function ... sometimes it's just stops"; tg:279 participation
 grew then got "kicked off by size players". His capitulation days = every bucket deeply negative (-3..-21% of its volume) on a day that fell hard, then bottom (S2 b3: retest within 2 d, then rally).
Prior: T2b (all-negative = 54% of >= -3% days, nothing), pass 2 (abnormal one-voiced selling on big down days CONTINUES -235 bp/3 d vs +26), Bybit literal rule +77 bp n.s. So the
 sign rule is dead on Binance; the open question is the MAGNITUDE with buckets that ADAPT to the coin's own trade-size distribution (tg:205 'days back for AI levels = 1').
What he does not say: (1) the buckets are relative (his ladder moved 31k->12k between 2021 and 2022), so a fixed ladder puts most of 2024 BTC flow in one bucket; (2) the signal is
 'even the big size sold', i.e. the LARGE groups' negative share is the capitulation, small groups selling is just retail; (3) he enters on a later confirmation (2-5 d window), not the close.
Build (a): 12 fixed notional bins -> 7 adaptive groups = cut points at the previous day's cumulative-volume septiles (coarse: 12 bins, say so); variant: previous 30 days. Dose = min group
 delta share and the two largest groups' delta share (continuous, quintiles among >= -3% down days). Long at the day close, 1/3/5 d simple returns; baseline = same coin, same day-return
 decile down days. BTC/ETH/SOL 2021-23 only (tsize coverage). Change my mind: the most negative quintile beats matched by > 100 bp at 3 d, rising with the dose, every year.
 Expected from pass 2: the opposite sign (continuation).
M4 a/e done (is3_m4.py; data/is3/m4a_explore.txt): adaptive 7 groups from 12 bins (prev-day / 30-d septiles). Most negative quintile of min group delta share +130 bp vs matched (p .34, MDE 314),
 no dose (least-selling quintile best), 2022 negative; his literal picture (all buckets -3..-21%, day <= -7%) -151 vs matched. Null +64 bp on all surrogate down days = simple-return convexity (baseline handles it).
 Next M4: b (4-h / session bars), c (R2 largest one-sided delta of a trend's life on a pullback), d (one-voiced buying breadth), f (pitstop in a strong move).
M4 b done: 4-h bars, flat quintile curves, Q1 -48 bp vs matched (MDE 133). Shorter bars do not help.
M4 c done (is3_m4c.py, bnall half 0, 12 cells): most one-sided selling day of an uptrend's life on a pullback = matched pullbacks or worse, anti-dose in N. Same sign as pass 2 (one-voiced selling continues).
M4 d done: breadth of one-voiced buying (bnall) = matched market days (+5..+53 bp n.s., not monotone).
M4 f think-through (19:0x): tg:206, 216-222 (stored descriptions; BTC range bars Apr 5-6 2021): strong rally, a bright-red (all buckets selling) bar at the high = "demand momentum no mo, pitstop";
 8 h of red-ish rotation that holds above wVAL; first bar whose buckets turn green -> breakout to a new high. Not said: the rotation must HOLD (no new low below the move's midpoint), the entry is
 the first all-green bar (a confirmation, taker entry), the stop is the rotation low. Build on 1-h bars (12 x 5-min tsize, adaptive groups from the previous day; his were ~300-pt range bars: coarser,
 say so), BTC/ETH/SOL 2021-23. Strong = 24-h return >= z sd (z 1.5/2/3); pitstop = all-negative bar making a 24-h high; entry = first all-positive bar within 12 h with the low since the
 pitstop above the 24-h move's midpoint; forward 4/12/24 h. Baselines: (1) same sequence outside strong moves (z < 1), (2) all-positive bars in strong moves without the pitstop sequence, same coin, z decile.
M4 f/g done (is3_m4f.py 1-h, is3_m4g.py range bars): pitstop -> first green bar = worse than any green bar in the same strong move (4 h -20/-38/-45 bp at >= 3/5/8% moves, MDE 45-98), null -8+-10.
M4 CLOSED OPEN (MDE rule missed narrowly, every form <= baseline, strongest cells opposite sign). Lesson: across M1-M4, N5 and pass 2, Binance size-bucket footprints consistently read as continuation.
F1 h done (is3_f1loc.py h): value-location reversal = plain 1-day return reversal (below VAL +4 bp vs return-decile matched, MDE 90). Explains e1's cost (mechanical, not value).

## M5 range -> impulse -> range (think-through 19:0x UTC, before any run)
Sources re-read (tg:226-234 stored text + vision descriptions, images not re-opened): ETH 1m Apr 2021, range high 2073.9 broken, run to 2082.7, pullback to the old high, bounce "at least one candle";
 "bid at previous high, ask at average size of that timeframe's candle ... capture spread almost every time"; "1 life, 1 trade"; "works across all rotations, especially range-based ones (tr), from
 profile levels"; "unless abnormal pressure"; tg:228 the second test wicked THROUGH the level (stop run) before bouncing.
Mechanism: breakout buyers and stopped shorts leave resting interest at the old range edge; the first retest meets it; the maker earns the bounce + 2 maker fills instead of paying spread.
What he does NOT say: (1) queue: his bid sits from the breakout on, so he is early in the queue; a fill on a mere touch is plausible only if volume at the level exceeds the queue ahead of him;
 (2) when the level breaks (tg:228) he holds or stops: unstated -> stop one bar width under, taker; (3) "one attempt" = first touch only; (4) he skips 'abnormal pressure' (crash days).
Prior: range_retest DEAD on 1-min klines (trade-through fills lose; touch followed by +-1 bp; profile levels = placebo). New here: range bars (his bar type), a queue-volume fill ladder, placebo levels.
Build (a): micro bars BTC/ETH/SOL 2021-23 -> range bars w = 0.1 / 0.2%. Range = 10 bars inside 3w; breakout close > range high; bid placed when price first reaches range high + 3w (impulse
 confirmed), lives 2 h, first touch only. Fill ladder: touch / touch + Q notional traded at or below the level (Q = $50k, $250k; pro-rata of each micro bar under the level) / trade-through 1 bp.
 Exit: maker ask at +1w (one bar), stop at -2w taker, timeout 60 min taker. Fees maker 2 bp, taker 5 bp + 1 bp. Mirror for breakdowns. Placebo levels at 0.63x and 1.37x the distance (same
 placement time, same fill/exit rules). Change my mind: real - placebo > 0 under the queue fill (Q = $50k) after fees, every year, both sides.
M5 a run note (22:4x): first unit died at once (EMFILE: mbars.load kept ~1000 lazy NpzFiles open under the unit's fd limit), fixed in kripto/mbars.py (eager read). Range-bar
 widths in the code are 0.2% / 0.43%, not the planned 0.1/0.2%: micro bars step 10 bp, so a 0.1% range bar would be ~1 micro bar (stated deviation, decided before results).
M5 e plan (before any run): target A = lowest low between the breakout close and placement (the post-breakout consolidation, always above B by construction), order rests 6 h,
 position up to 6 h, stop -2w; same fill ladder and placebo levels (placebo target keeps A's distance above its own level). Require A - B >= 1w so the trade can pay 2 maker fees.
M5 b/d plan (before runs): b = level is the 10-bar range's approx. value-area high (top-volume 5-bp bins to 70%) or its POC instead of the range high; placebo at 0.63x/1.37x of the
 placement-to-level distance; skipped when the level is < 2w below placement. d = the same order on thin coins' 1-min klines (h/l/qv stand in for micro bars; fill minute cannot also exit),
 thin = explore median daily quote volume $0.5-50M (44 coins, data/is3/m5d_coins.csv, chosen before any run), range bars 0.5% / 1% so +1w >> 4 bp maker round trip.
M5 c plan (before run): his literal target = the average 1-min candle (mean ln(h/l) of the 1440 finished klines before placement), first touch only, same queue ladder / stop / 60 min;
 c = maker exit (1 bp trade-through, 2x2 bp), ctk = taker exit on the first touch (2+6 bp). OOM fix: one year at a time (SOL 2021 alone = 1.3 GB RSS) -> micro-bar forms run serially.
M5 d done (23:2x): thin coins = placebo levels at every fill rung (MDE 2-9 bp); the more volume trades through our level before we count a fill, the worse (q250k -40 bp gross,
 same for placebos): queue-position fills on thin coins are pure adverse selection. Touch fills ~0 gross. No level effect to sell, before or after costs.
M5 a done (23:2x): BTC/ETH/SOL range bars 0.2/0.43%: real old range high = placebo levels (diff -1.5..+0.6 bp, MDE 1-3), touch ~0 gross, queue fills worse with Q. Same as d, same as 11-11 range_retest.
M5 a dose by wait (placement -> fill, 5/15/40/80/120 min): real = placebo in every bucket (his >40-min retest is not special). Added f (before run): impulse taker-delta share
 (side-signed, breakout bar -> placement; always > 0, median .25) as the 'abnormal pressure' dose; real - placebo by quintile; pass needs a monotone dose and top quintile > costs.
M5 e done (23:3x): his A-target, resting 6 h: 0.2% = placebo (-3.7 vs -3.1); 0.43% n138 +7.6 vs -3.0 (p .07, MDE 15) with placebos straddling it and queue fills negative -> no confirm.
M5 c done (00:0x): mean-1-min-candle target, maker vs taker exit: real = placebo; taker exit +0.5 bp gross, -2.5 bp net vs maker; all rungs net negative. b (VAH) = placebo too (POC pending).
M5 b done (00:1x): VAH = placebo, POC slightly worse than placebo; all net negative.
M5 f done: impulse-delta dose flat at 0.2%; strongest quintile -6 bp vs placebo at 0.43% (his skip rule is real as an avoid). M5 CLOSED DEAD (6 forms, MDE 1-9 bp, every level = placebo,
 queue fills adversely selected). Sceptic check: tested on his bar type, with his two targets and a queue model, on liquid and thin coins: the idea, not just my translation. Next: M6.

## M6 trend systems on move bars (think-through 00:5x UTC 11-25, before any run)
Sources re-read (tg:103-107 text + stored vision descriptions of the two menu screenshots, images not re-opened; tg:195 is a forwarded quote, no rule): range / rangeUS (TR = trend-reverse)
 / P&F / volume / delta bars are "the real noise suppression ... real edge", "time is noise for me ... I care about levels, price points". Menu: TR 44-26 ... 700-420 (reverse ~0.6x trend).
Mechanism claimed: sampling in price instead of time removes quiet-time noise, so a trend rule sees cleaner swings. Sceptic: a deterministic resampling cannot create drift; any gain must come from
 (1) volatility-adaptive lookback (a range-bar lookback spans long time when quiet, short when busy) or (2) intrabar reaction (signals fire the moment a distance is covered, not at an hour mark).
What he does NOT say: he never trades a mechanical trend system on these bars; they are his CHART for levels / footprints, entries are discretionary at levels (M5 = placebo). A TR bar
 "follow until the reversal bar" is a stop-and-reverse with a fixed retrace = zigzag / Kagi; on a random walk it earns -costs. Turnover: small bars flip often, taker 6 bp/side kills it, so widths >= 0.5%.
Build (a): BTC/ETH/SOL micro bars 2021-23 -> range bars w 0.5/1/2%; tsmom sign(c_t/c_{t-N}-1), N 5/10/20; P&L on the micro-bar grid (position from the next micro bar), 6 bp per side.
 Baseline: hourly-bar tsmom with lookback L chosen ONLY to match the range version's flips per year (same coin). Compare daily Sharpe (gross, net) and the day-block bootstrap of the daily
 difference; trade card (per-trade simple gross) vs time-bar trades. Null: sign-flipped micro bars (gross must be ~0). (b): ATAS-like TR bars, trend X 0.5/1/2/4%, reverse R = 0.6X, always in
 the last bar's direction; variant: plain zigzag (retrace R from the running extreme). Change my mind: move-bar net Sharpe > matched time-bar net Sharpe in every explore year for most cells.
Prior: trend on liquid perps is crowded (CLAUDE.md); bar type rarely matters in the literature (Lopez de Prado's bars help statistics, not drift). Expect range = time within noise.
M6 run note (01:1x): first m6a explore run filled at the deciding trade itself; 2021-02-22 14:17 BTC printed +-2 % ms ping-pong trades and the rule "flipped" 2,070 times that day
 (cards m6a_* of 01:0x are that bug; rerun overwrites them). Fix decided before any result was read as evidence: every fill (move AND time bars) at the price as of decision + 1 s, stress 5 s.

## M7 delta at price and exact volume profiles (think-through 01:1x UTC 11-25, before any run)
Sources re-read (tg:59-61 text + stored vision of the Exocharts TPO/delta screenshot, image not re-opened; R10, R14-R16 rows): per-price delta column beside each session profile (-37M at the prior
 POC, -14M at the London POC ...); "we don't look at every number, only anomalies that stand out". So: the outlier delta-at-price cell, and WHERE it sits (extreme / POC), is his read.
Mechanism: a big negative delta at a price that then holds = passive buyers absorbed aggressive sellers there (support); the same at a price that breaks = sellers won. He reads it with location.
What he does NOT say: (1) the sign of the follow-through (absorption vs initiative) depends on whether the price later held, which is known only after; the tradable part is the location
 at the close (an outlier sell cell at the day's low that the close is well above = absorbed); (2) "anomaly" is relative to the day's own cells, so scale by day volume; (3) next session, not
 next minute: he trades the reaction when price returns to that cell.
Prior: P1-P3 (1-min kline profiles) = placebo levels; M3 absorption = matched; Binance footprints read as continuation (M1, M4). New here: exact 10-bp profiles from aggTrades (micro bars).
Build (a): BTC/ETH/SOL 2021-23 daily profiles from micro bars (10-bp bins, mbars.vap). Features: the bin with the most negative and most positive delta, its |delta| / day volume (dose), its
 location in the day's range (bottom / middle / top third) and whether it is the POC bin. Outcome: next-day simple return (close->close, and the first touch of that bin within 3 d: bounce
 60 min). Baseline: matched days, same coin, same day-return decile and same close-location tercile. (b): P3's best form (first touch of a naked daily POC, +15 bp/60 min vs mirror, p .09)
 with the exact POC, mirror placebo, approach side matched. Change my mind: a cell with |delta| share in the top quintile and a monotone dose beating matched by > MDE in every year.
M7 a done (is3_m7.py, research/is3/m7a_explore.txt): outlier delta-at-price cell: next day = matched (+7 bp, MDE 62), no dose in a 30-cell grid; first retest of the cell = a low-delta
 placebo bin on the same side (+8.4 vs +8.5 bp/60 min, MDE 7), the largest cells worse (anti-dose). The generic +8 bp is the dip-touch long drift of 2021-23 (long side +16, short +1).
M7 b done (is3_m7.py b, m7b_explore.txt): exact POC first touch beats its mirror by ~+10 bp/60 min (long +7.9 p .19, short +12 p .023), as P3 found with kline profiles; below a taker round trip.
 Two independent profile builds now agree on a small real POC touch effect: a FEATURE-sized timing input at most (entry location for a book already trading that direction).
M7 c plan (before run): at the exact-POC first touch, the next 5 min: taker delta against the trade (sellers into a long) as a share of that window's volume, and 'held' = price never
 > 1 bin through the POC. Entry at touch + 5 min + 1 s, 60 min. Absorption = top-tercile opposing delta AND held; compare with held + low delta, and with mirrors under the same condition.
M7 c done (m7c_explore.txt): absorption at the POC touch (held 5 min vs top-tercile opposing delta) +0.9 bp/60 min = mirrors (+5.6) = low-delta touches; the b bounce is over within 5 min.
M7 d done: stacked imbalance zones = neutral zones (X7.5 +17 bp n 61, MDE 37, 2021 negative: no prereg). M7 CLOSED DEAD. Sceptic: his rows are ticks, mine 10 bp; the POC result agrees across two builds, so the profile is not the bottleneck.

## X1 confluence (think-through 01:2x UTC 11-25, before any run)
Sources re-read (tg:59-61, tg:168 text; wa 18.10.42 (1)/(2)/plain as OCR + stored vision, images not re-opened): "climax points when we just sweep it on low liquidity ... doesn't really work as
 reversals alone, need bit more stuff as confluences"; tg:168 conviction / momentum / absorption / exhaustion vocabulary; "anomalies that stand out".
Mechanism: a climax sweep is forced flow (stops, liquidations) into a thin book; it reverses more when it runs into resting interest at a level many watch (prior-day / weekly low),
 because the sweep there also triggers the stops parked under that level and then finds the passive bids that defend it.
What he does NOT say: (1) which way the level works: a sweep THROUGH yesterday's low (stops taken, then reclaim) vs a bid that fills just ABOVE it; (2) the confluence is a filter on an
 entry he already has, so the right test conditions the CONFIRMED ladder (T1k30) fills on location, not a new trigger; (3) distance matters only within ~a day's range.
Build (a): T1k30 one-bar-late fills (data/is3/e2_k-30.parquet, causal top-20 universe), explore 2021-23; fill price = close two minutes back x (1 - depth). Location: log(p / prior UTC
 day's low) and log(p / prior 7 days' low), in units of the coin's 24-h sigma-based depth too. Outcome h60 (and h240). Bins: through the level by > 2%, 0-2% through, 0-2% above, > 2% above.
 Baseline: the other fills matched on depth quintile (is3_lib.matched). Change my mind: fills through or at the level beat the rest by > MDE with a monotone dose, every year.
Prior: P-series levels = placebo; T1 is driven by the depth / violence of the move, not by location. Expect nothing, but the filter use is untested.
X1 a done (is3_x1a.py, x1a_explore.txt): ladder fills at/through prior-day or weekly lows = depth-matched other fills (+38 p .47 / -9); the distance curve is the depth curve. 91% of fills are fresh lows of the day anyway.
X1 b done (is3_x1b.py): selling-climax hours at the prior exact POC = the same hours away from levels (-11 bp/4 h, -3/24 h), mirrors similar.
X1 c done (is3_x1c.py): single-print fill + absorption -0.3 bp/60 min vs mirrors +20 / no-absorption +18 (n.s.): wrong way if anything.
X1 d done (is3_x1d.py): Sunday move away from the collar on falling volume CONTINUES (toward-collar -130 bp vs placebo +10, p .21, MDE 200, every year -, median +6). Lead for N5 f/e (due 12-10), not a prereg.
X1 e done (is3_x1e.py): pinned RSI + fat-node cross = 22 events (2021 alt rallies); all pinned-up days already +552 bp/3 d, so the card's 'pass' (baseline n 1) is void; node adds n.s. on top of the pin.
M8 closed UNTESTABLE (01:2x): no M1-M6 survivor (M2b failed confirmT); six unseen coins not downloaded, sample kept for a future survivor.
X1 f done (is3_x1f.py, x1f_explore.txt): velocity climax at a round number = placebo grid = no level (deduped, 5-min-late entry, MDE 13). CAVEAT for M2 (closed OPEN, confirm failed anyway):
 its g15/g60/g240 start at the range bar's exact closing print and its events cluster in ms whipsaw (123 in one second on 2022-01-05 19:45:21); raw medians of +30-160 bp/h by year were that
 artifact. late60 + 1 per coin per 30 min gives ~0. X1 CLOSED DEAD. Sceptic: each confluence was built from his own words and the confirmed ladder where possible; the idea, not a translation.

## F2 filters for tsmom / blend / listing shorts / funding pair (think-through 04:5x UTC 11-25, before any run)
Sources: same rules as F1 (L5 cascade delay, R8 tg:286 "demand up, volume down, price keeps shooting up" / volume spike into highs = sellers, P5 value location, E2 clock tilt, C1 dates).
Books (bnall 1d, clean, explore <= 2023, F0 harness, 200/100 same-share same-persistence random masks): tsmom@bn (lookbacks 14/28/56, top 12, tv .3), blend@bn (BLEND_COMPONENTS),
 listing_short (bnall); fspread_hold@pair only where the form makes sense (its history on pair is short: say so).
Prior from F1: every daily filter on flow/xsmom was random-mask or worse; the one explore pass (1-day short block after cascades) failed 2024-25. Location blocks were mechanical reversal costs.
What he does NOT say: (1) L5 is a DELAY, not an exit: existing shorts stay, only shorts that would be opened/increased the day after a cascade wait one day (F1 exited them, so a) tests the
 real delay, with the random comparison using the same delay on random days); (2) trend books hold for weeks, so a 1-day delay costs little if wrong and the trapped side is the NEW short;
 (3) R8 is about the rally's volume trend, not one spike: c1 = block new longs at a 20-d high on a >=3x spike (F1c's form, backwards there), c2 = keep longs only where the 14-d rally came on
 FALLING volume (his positive statement) vs rising; (4) macro days: he stays out around news, i.e. flat the book (or halve) on the FOMC/CPI day itself, d; (5) e: the trend entry's location
 vs yesterday's value (initiative close above VAH for a long = Dalton's go-with), new positions only.
Change my mind: dSR > 0 at >= 95th pct of random masks, every explore year, in >= 2 of the 3 books. b (execution hour) is a cost question: measure the book's trade-weighted drift from
 00 UTC to hour H on bn100 1h (delay cost per hour, weekday vs weekend); a tilt counts only if some H beats 00 by > 2 bp per traded unit in every year.
F2 b done (is3_f2b.py, f2b_explore.txt): delaying a daily book's trades by 1-23 h forgoes +1..+13 bp per unit traded (blend positive in 4-5 of 5 years at every H >= 8 h); no clock tilt, weekend
 executions no better. Agrees with fill_delay (11-22): execute at the close. Units is3-f2ad / is3-f2ce running forms a,d / c,e (04:54).
F2 a done: cascade short-delay passes in blend only (dSR +0.23, every year), tsmom 2022 -, listing_short nothing. Not preregistered: fails my 2-of-3 rule, and F1g's confirm already showed the bounce gone in 2024-25.
F2 c done: R8 backwards again (spike blocks 0th pct, falling-volume-only adds cost blend 0.45 SR); rising-volume mirror = random masks.
F2 fspread_hold@pair: 0 invested days in explore (HL funding history starts 2024), so no filter can be explored without spending its confirm sample; left out of F2 (stated).
F2 d confirmT (05:2x): FAILED both pre-registered books (blend +0.08 at 66th pct, listing_short -0.14 at 38th). Fourth 2021-23 macro/bounce pattern that does not carry into 2024-25.
F2 e done: value location of trend entries = random masks or the mechanical reversal cost; e3 blend shorts +0.18 pooled but 2021 negative (1 of 20 cells).
F2 f done: failed-new-high trim costs (his side); failed-new-low short block passes blend 5 d only (dose reversed at 1 d). F2 CLOSED OPEN: nothing usable; the recurring blend-only 'no new shorts after a flush' lead is the F1g family whose 2024-25 confirm failed. Sceptic: the books tested are the ones that trade; the delay form was his L5, not my exit.

## LD2 ladder flush-batch control (think-through 21:2x UTC 11-26, before any run)
Source: backlog LD1/LD2, library N13 (Gueant §11), findings LD1 (PC, ~80% coverage). No chat records (not an InSilico rule; a ladder control queued here).
Mechanism: the ladder's tail is one flush minute where up to 17 bids fill at once (E2c: minute-low mark -17% at 5%/order). The 6th+ fill of a batch is the same bet as the first five on a
 correlated market; a cap bounds the batch so the per-order size can be re-derived (E2d rule: -50% on every fill of the largest possible batch must stay above the 25% kill -> size = 25%/(0.5 cap)).
What is not said / must be true: (1) a cap is only worth it if the truncated fills earn LESS per unit risk than the kept ones; SR is scale-free, so a size-matched base (same ret/yr) is the
 comparison for the worst day / worst 5 days; (2) truncation is in volume-rank order, so a second control is RANDOM thinning to the same fill count (200 draws): does WHICH fills are dropped matter?
 (3) LD1's confirm (2024-26/10) was spent once on cap 3 with 80% coverage: the server's 2024+ is not fresh for this ladder family; any confirm here is a second look, stated as such.
Pre-registered (a): explore 2021-23 on the server's full top-20; PASS = cap5 SR >= base - 0.1 AND worst5 at matched ret/yr better than scaled base by >= 25% AND cap5 worst5 above the 95th pct
 of random thinning. Only then one confirm 2024-01..2026-10. (b) size re-derivation reported, no new test. (c) skew A_0.5 alone and with cap 5, same rule.
LD2 a/b/c done (is3_ld2.py, research/is3/ld2_explore.json; server full top-20, 1852 cand / 107 coins, base SR 2.33 vs PC 2.46): cap 5 = size effect (worst5 only +8% better than a ret-matched
 scaled base, 74th pct of random thinning; cap3 +14%, cap8 +9%): FAIL, no confirm. b: E2d-rule size under cap5 = 10%/order -> +20% /yr, worst day -4.7% (explore), reported only.
 c: skew A_0.5 fails the TAIL rule (+15%, 94th) but is better in SR every year (2.72 vs 2.33; 3.47/0.86/3.56 vs 2.97/0.43/3.00), SR 100th pct of thinning: it picks better-priced fills.
LD2 d pre-registered (before any 2024+ look at A): confirm 2024-01..2026-10, PASS = A_0.5 SR >= base + 0.2 AND SR >= 90th pct of random thinning. 2024+ already seen for base/cap3 in LD1.
LD2 d done: confirm A_0.5 SR 2.16 vs 2.04 (FAIL, +0.2 needed); 2024 +0.9, 2025 -0.1, 2026 +0.05; tail +26%/99th pct (not the criterion). LD2 CLOSED OPEN. Sceptic: the cap and skew are the controls the backlog named, on the full universe; the skew's small gain is real-looking but under the bar.

## FC1C HL-BN funding gap (21:3x UTC 11-26)
Form a needs HL funding before 2024-07: the server has none either (136 coins start 2024-07-01, the download default). Backfill 2023-05..2024-06 from the public /info
fundingHistory (research/studies/is3_fc1c_fetch.py, 4 s interval, resumable, unit is3-fc1cfetch, oldest HL listings first, 139 coins). Deferred to 22:25; LV2 meanwhile.

## LV2 lowvol minus carry (think-through 21:4x UTC 11-26, before any run)
Source: LV1 diagnosis (findings lowvol): price-only spread positive (explore 0.17-0.31) but the high-vol short leg pays it back in funding (crowded shorts, RIVER/LAB squeezes). Not an InSilico rule.
Mechanism: the lottery story says the overpayers are LONGS of high-vol names. Where funding is negative, the crowd is already short: the short leg is not taking the lottery buyer's
 money, it is joining a crowded short that pays carry and gets squeezed. So the short leg should be the high-vol names where longs pay (funding >= 0), i.e. where the lottery buyer is visible.
What is not said / must be true: (1) excluding negative-funding shorts must beat RANDOM exclusion of the same share (otherwise it is just a smaller short leg); (2) dose: Q5's hedged
 return should rise monotonically with trailing funding tercile; (3) funding is persistent day to day, so trailing 7-d funding predicts the next day's funding mechanically: the test
 must also report price-only, so a 'win' that is only funding carry is named as carry (corr with the carry book).
Forms: a = rank weights, short candidates with trailing 7-d mean funding < 0 dropped, short leg re-scaled to dollar neutral; placebo = same count dropped at random (100 draws).
 b = rank on vol of (r - funding) instead of r. Explore bnall 1d 2020-01..2023-12, gross of trading costs, net of funding, BTC-beta hedged, top-30 and top-100.
 PASS (written now): pooled SR >= 0.5 AND >= 3 of 4 years > 0 AND above the 95th pct of the random-drop placebo (a). Confirm: bnall 2024+ was seen by LV1 (the diagnosis came from it),
 so a pass goes to HL (funding backfilled to 2023-05 by FC1C's fetch) as confirm, stated. Prior low: LV1 2021 -0.9 every form.
LV2 a done (is3_lv2.py, lv2_explore.txt): dropping f7<0 shorts = random drops (top30 29th pct, top100 76th), FAIL. Surprise, checked sign (w*f1 subtracted, longs pay +funding): in 2020-23 the
 negative-funding high-vol shorts are the best shorts on PRICE (mirror price-only 0.83/0.88, net 0.26); the crowded-short squeeze of LV1 is a 2024+ phenomenon (memecoin era), so the filter would be shaped on it.
LV2 b done: funding-adjusted vol ranks = price vol ranks (SR identical): no effect. c (HL) waits for the HL funding backfill (FC1C fetch).

## E2B execution clock at the CME break (21:4x UTC 11-26)
Think-through: E2 (PC) found a 1-h net-long drift in the CME break (17-18 NY = 22-23 UTC winter / 21-22 summer), small and fading (7.2 -> 2.1 -> 1.1 bp/unit). To use it a daily book must decide
 before the break (16/20 UTC anchor) and defer its sells past it. Unstated: (1) the anchor move may cost more signal than the tilt earns (anchor = start-day lottery on one clock),
 (2) the tilt is a 1-h long of half the turnover, so it is beta, judged against the same 3-h deferral at other hours; (3) the 2026 rate is the honest number, the trend is down.
E2B a done (is3_e2b.py, e2b_anchor.json): anchors 00..20 UTC SR 1.57-1.87 (16: 1.87, 20: 1.72, 00: 1.68): anchor moves cost nothing beyond +-0.15 SR phase noise. First run was a bug
 (resample offset ignored on tz-aware index: same prices, shifted funding, 5 junk registry lines tagged anchor @04..@20, ~21:45 UTC); fixed by shifting the index, known-answer assert on BTC.
E2B b done (e2b_defer.json): sells deferred 3 h from the 20 UTC anchor +5.3 bp/unit (t 1.05; 2025 -25, 2026 +5) = placebo deferrals at 08 (+6.5) / 04 (+4.3); deferring buys loses ~-6 (signal decay).
E2B c: HL 1h starts 2026-04-14 -> testable 2027-04-14. E2B CLOSED OPEN. Sceptic: tested on the book's own trades with the clock that a live book could use; flow@bn (the leg E2 liked most) could not be replayed.
FC1C think-through (21:5x UTC, before any number on the new window): gap = HL 3-d funding minus Binance 3-d funding on the same coin. Mechanism: HL is the venue where
 retail levers up without KYC; a coin whose HL longs pay much more than Binance longs is crowded on HL specifically (late, levered retail), and arbitrage capacity between the
 venues is limited (two margin accounts, X1c), so the gap persists while the crowd is wrong. Unstated: (1) the gap may be mechanical (HL premium sampling, interest floor), so it
 must beat the BN-funding-rank control cX; (2) the trapped side is HL longs: price should fall over days, not hours (7-d entry); (3) listing-age overlap: young coins carry big gaps
 (corr listing_short 0.49) -> form b uses it as a listing_short filter.
 PRE-REGISTERED (a, explore 2023-05-15..2024-07-01): PASS = c3s [entry] net > 0 AND t_price >= 2 AND short price leg higher in deciles 9-10 than in 1-5 (dose) AND c3s entry net
 > cX entry net. Only then ONE confirm 2025-07..2026-10 (never seen by any FC1 form). Prior low (PC: t 1.1-1.5 over 12 months).

## FF2 friday_follow market-relative / shorts only (think-through 21:5x UTC 11-26, before any run)
Source: findings friday_follow + FF1(a): Friday's >= 2-4% 24-h move continues into Saturday on the 82 survivors; on bn100 (survivorship-free) the WF fell to 0.78/avg 0.61 and the P&L
 was the long leg of the 82 (+1.11 of +1.55); outside the 82: +14 bp/week 2020-23, +0.8 bp 2024-26. Opposite of InSilico R21 (weekend fade).
Mechanism (if any): Friday-afternoon NY flow is the last institutional session before a thin weekend; a coin that moved on its own news (idiosyncratic) is not fully priced when
 desks go home, and weekend liquidity is too thin to finish the move until Saturday. That is about the coin's OWN move, not the market's: the absolute-move rule mixes it with
 market beta (on a +5% BTC Friday, every alt "moved"). So the excess move over the universe is the purer form; shorts only removes the survivor-long channel entirely.
Unstated: (1) who is trapped: weekend shorts against a Friday breakout; (2) hold relative to the universe (hedged), else it is a weekend beta bet; (3) Thursday/Saturday cuts must not show it.
Build: bn100 1h per-coin closes at cut T (hour ending Fri 12/15/17/20 NY, tranches), m = c(T)/c(T-24h)-1, U = mean m over the point-in-time top-30 (and top-100), x = m - U;
 follow sign(x) if |x| >= thr (2/3/4%), outcome = side * (r(T->T+24h) - U_fwd). Placebo cuts: Thu and Sat same hours. Week-clustered t (mean per cut-week). Simple returns.
PRE-REGISTERED (a, b; explore 2020-01..2023-12): PASS = thr 2% form gross >= +20 bp/event AND week-clustered t >= 2 AND every explore year > 0 AND above both placebo weekdays
 AND gross - 14 bp (FF1 cost/event) > 0. Prior low.
FF2 a done (is3_ff2.py, ff2_explore.json): excess-move follow on Friday = -3 bp (top30, t .6), dose flat; the same pipeline gives FF1's absolute +54/+73 bp, so Friday follow is the
 universe's weekend continuation, not idiosyncratic news. Thursday excess-follow +30 bp (t 2.1) is a placebo-day surprise, 2022 negative: noted, not chased (not his claim, would be a fresh hypothesis).
FF2 b done: shorts only hedged -5..-10 bp; unhedged + only via 2022. Unstated condition that would make it work -> d: trade the MARKET's Friday move (index-level timing).
FF2 d done (ff2d_explore.json): the MARKET's Friday move continues: universe follow +65 bp/24 h, t 3.06 (MDE 59), Thu +10, Sat -27; mostly up-Fridays (+111). 2020 -3 bp misses my item rule
 (every year > 0) but beats both placebo days every year (pass3 s3). Preregistered FF2d_market_friday_follow (rule + caveats: 2024-26 partly seen by FF1's decomposition) -> one confirm.
FF2 c/close: confirm (ff2d_confirm.json) +32 bp t 1.2, 2026 +0.6: FAIL. FF2 CLOSED OPEN. Sceptic: tested his weekend-continuation claim in the form that removes the survivor long; the market-level form was found by asking what the excess form left out.

## W3B Sunday fade, BTC+ETH only (think-through 21:5x UTC 11-26, before any run)
Source: W3 (R21 second pass): fading the Sunday 12->18 NY move for 24 h replicated on unseen coins but the WF was weak (pick 0.44) and ~all market-wide, a 2024+ effect; costs 5.1%/yr at 69x
 turnover on 100 coins. Mechanism: Sunday afternoon moves happen in the thinnest book of the week (no CME, Asia asleep); Monday's real liquidity reprices them. If it is market-wide,
 trading it on the two deepest coins keeps the effect and drops most of the cost. Unstated: (1) he fades only moves that look forced (thin volume), so dose by |move|; (2) Monday
 Asia open is when it reverts: 24 h holds through it; (3) placebo: the same clock on the other six days must not do it.
PRE-REGISTERED (a, explore 2020-02..2023-12): PASS = Sunday fade, |move| >= 1%, mean per Sunday (BTC+ETH, tranches 17/18/19 averaged) >= +15 bp AND t (per Sunday) >= 2 AND
 above the median of the six placebo weekdays in >= 3 of 4 years AND mean - 12 bp > 0. Prior low (W3 explore market bet t 0.6).
W3B a done (w3b_explore.json): Sunday fade on BTC+ETH <= 2023 = 0 or negative at every size; Saturday 12->18 NY fade +43 bp t 1.9 is a placebo-day surprise (with FF2: Fri up, Sat afternoon reverts?), not chased. W3B CLOSED OPEN.
W3S (data-mined, stated): Saturday 12->18 NY fade on BTC+ETH, +43 bp t 1.9 in W3B explore as a placebo cell (1 of 18, expected max t ~2 by chance). Mechanism = W3's thin-book weekend reversal on another thin afternoon. Pre-registered one confirm (W3S_sat_fade_btceth), frozen cell.
W3S done: confirm +1.8 bp t 0.07: chance cell. CLOSED OPEN (one form by construction).
FC1C data note (22:2x): HL paid funding 8-hourly until ~2023-06 (3 prints/day, per-print ~5-8x the hourly-era size = 8-h rates), hourly after; the panel's daily SUM of prints is right in both eras. 34/134 coins after chunk 1 (oldest listings, ~19 pages each); chunk 2 to ~22:58; files checked: monotone, no duplicate times.
FC1C fetch after chunk 2 (22:57): 77/134 coins. Remaining coins are 2023-Q4..2024-Q2 listings (short histories, est. ~40 min): one more chunk, same unit command as above
 (systemd-run --user --unit is3-fc1cfetch ... -m research.studies.is3_fc1c_fetch 42; reset-failed first), then FC1C a (is3_fc1c.py) and LV2 c (is3_lv2 --hlc).

## 00:4x UTC 11-27 insilico
FC1C fetch chunk 3 started 00:47 (deadline 24 min, to finish before the 01:15 nightly window). bnall 1d snapshot -> data/is3/fc1c_bnall_1d.pkl (00:48, last bar 11-21) so FC1C a
 can run inside the window without loading bnall. is3_lv2.py: the --hlc main block ran before form_c was defined (NameError); moved to the end.
LV2 c pre-stated (before the run): lowvol defaults on HL 1d through research.evaluate. FRAGILE if SR without the best 10 days < 0.3 OR SR before 2024-07 (the backfilled-funding
 window, unseen by the HL WF which started 2024-07) < 0; otherwise the HL blend leg stands. Insilico does not change lifecycle: a FRAGILE verdict goes to findings + backlog for research.
FC1C a done (01:12, is3_fc1c.py, fc1c_explore.json; 115/134 coins backfilled, the 19 missing are 2024-02+ listings): c3s top-10% gap short 7-d entry +39 bp net vs cX control +10, t_price 1.4,
 2023 -175 / 2024 +189, dose U-shaped (d1 +61, d4 +66, d5-7 < 0, d10 +76): FAIL (t, dose, one regime). With the PC window (t 1.1-1.5, 2024-07..2025-06) it is a weak 2024+ effect, not a crowding gradient.
FC1C b think-through: as a FILTER, the gap only has to separate GOOD from BAD shorts inside a book that already works (listing_short on HL, shorts of young perps). Mechanism: a young
 coin whose HL longs pay more than Binance longs is being bought by levered HL retail -> the short is against the trapped side; gap <= 0 means HL is not crowded -> the short is plain
 beta to new-listing decay. Unstated: (1) many young HL coins are not on Binance yet: gap undefined, the filter keeps them (report touched share); (2) a filter must beat random masks
 of the same share/persistence (F0), cutting names alone costs SR; (3) exit vs delay: use exit (apply) first. Explore = 2023-05-15..2024-07-01 (F0 'explore' re-pointed, stated),
 book listing_short HL 1d defaults. PASS = dSR > 0 at >= 95th pct of 200 random masks AND dSR > 0 in 2023 and 2024 halves. Prior low (a failed; filter is a weaker claim).
FC1C b done (is3_fc1c_b.py, fc1c_b_explore.json): exiting gap<=0 shorts in listing_short HL: dSR -0.13 (28th pct of random masks), FAIL. Dose REVERSED: shorts in the top gap tercile
 lose 106 bp next day (median +5) vs ~0 (median +27/+32) in low/mid: the HL-crowded young coin keeps rising short-term (the levered crowd is right for a while, or the gap marks a squeeze in progress).
FC1C d (added, data-mined from b's dose, stated): block shorts in the TOP gap tercile (edge fixed from the explore short-day gaps); F0 on explore first; confirm 2025-07..2026-10 only if explore passes.
FC1C d explore (fc1c_d_explore.json): SR 0.26 -> 1.00, dSR +0.74 at 99.5th pct of random masks, mdd -27.9% -> -15.6%, 2023 -0.18 -> 0.84, 2024 0.81 -> 1.19. Bug check: gap lagged 1 / 2 days
 still 0.88 / 0.82 (not look-ahead; funding day D = prints during D, weight at D pays D+1). Data-mined on the same sample -> pre-registered FC1Cd_block_high_gap_shorts, one confirm 2025-07..2026-10.
FC1C d confirm (fc1c_d_confirm.json): SR 1.34 -> 1.42, dSR +0.08 at 92nd pct (needs 95), mdd unchanged: FAIL. Same sign, a fraction of the explore effect (explore was the sample it was mined on).
LV2 c done (lv2_hlc.json): HL lowvol SR 0.70 (2023-03..), 2023 -0.01 / 2024 0.50 / 2025 2.36 / 2026 -0.11, w/o best 10 days 0.23 (69% of P&L), pre-2024-07 -0.04, pays funding 4-5%/yr: FRAGILE (both
 pre-stated clauses). Note 2023 funding coverage median 28 coins (partial). LV2 CLOSED OPEN; backlog line for research (nested selection with the longer funding history).
FC1C c (fspread tilt) needs the pair panel (loads Binance files) -> deferred to 03:35 (nightly window).
Next session (FC1C c, due 03:35): first one fetch chunk for the 19 remaining coins (reset-failed is3-fc1cfetch; same unit, deadline 15), then form c: 7-d gap rank as an entry/size tilt in fspread_hold@pair (pair panel, 1d).

## 04:5x UTC 11-27 insilico: FC1C c think-through (before any run)
Source: FC1 (findings funding_contra) form c = the HL-vs-BN gap is the only FC1 form with the right price sign; a/b/d failed as a standalone short and as a listing_short filter.
Here the gap is the SAME quantity fspread_hold@pair trades (14-d mean HL-BN funding spread, open at |s| > 0.1 ann., hold until it flips), so the only new information a 7-d gap can add
 is the SLOPE: is crowding building (|7d| >= |14d|, same sign) or fading (|7d| < |14d|) when a pair opens. Mechanism: a widening spread = HL longs still piling in -> funding keeps
 paying for the hold, and the premium convergence (~1/3 of fspread P&L) has not started; a fading spread = we arrive late, the pair flips soon, we pay 4 legs of costs for little carry.
Unstated: (1) entries only (exits stay the sign-flip rule, else it is a different book); (2) the gate must beat random entry gates of the same share/persistence (cutting entries alone
 changes the book); (3) a late entry may still earn the convergence leg, so the price and funding legs per trip are reported separately.
Explore = 2023-05-15..2024-07-01 (pair panel with the backfilled HL funding; fspread's WF never saw it). Book = fspread_hold@pair config params (lookback 14, enter 0.1), local copy
 with a gate hook, checked identical to the registered function. PRE-REGISTERED (c1 widening gate): PASS = dSR > 0 at >= 95th pct of 200 circular-shift random gates AND dSR > 0
 in 2023 and in 2024 AND trips opened in the top tercile of |7d|/|14d| earn more per trip than the bottom tercile. Then ONE confirm 2025-07..2026-10. Prior low (gap ~ s, slope noisy).
FC1C c done (is3_fc1c_c.py, fc1c_c_explore.json; local fsh copy asserted identical to the registered fspread_hold): widening gate SR 14.20 -> 14.65 (dSR +0.45, 97th pct of random gates)
 but ann 26.6 -> 25.0%, 2024 half down (11.49 -> 11.01), per-trip dose reversed (mid tercile best): FAIL. Surprise check: base SR 14 on 2023-05..2024-06 is real carry, the WF's in-sample folds were 7-10 too
 (OOS 1.26 = one -2.55 fold, 2025-10 crash); slots are full (9.7/10), trips 62-73 days, price legs cancel, so the slope cannot add carry, only shuffle slots. FC1C closing OPEN.
 Side fact for research: fspread_hold on the never-seen 2023-05..2024-06 window = 26.6%/yr net at gross 2.0, mdd -0.6% (replication of the X1b edge on unseen history, one-account margin).

## LD3 ladder fills: liquidity holes vs heavy-volume flushes (think-through 10:5x UTC 11-27, before any run)
Source: library N14 (Bouchaud-Farmer-Lillo 2008 §8.1-8.2), backlog LD3; no chat records (not an InSilico rule). Fill set = LD1 candidate table (k30 one-bar-late crossings, server top-20).
Mechanism: a jump is set by the gap next to the best quote, not by order size; a deep wick on LITTLE volume is a hole (transient), a deep move on HEAVY one-sided volume is a metaorder
 or forced flow (more permanent). Who pays: in a hole, whoever's market order walked an empty book; in a flush, the liquidated side keeps selling for longer -> our bid is early.
What is not said / must be true: (1) Amihud rises with |move| by construction and deeper fills bounce more (they are bought cheaper): split WITHIN move-depth (kreach) terciles,
 and also by relative volume alone (qv / coin's trailing 30-d median), else the "hole" effect is just depth. (2) The fill minute's volume is known only AFTER the fill: a skip rule is
 not live-implementable; the live form is an EXIT rule (flush fill -> sell at close of t+1, taker) or a second taker entry on holes at c[t+1]; so the decisive number is the
 return from c[t+1] to the exit, not from our quote. Form c re-stated accordingly (early exit vs random early exits of the same share). (3) Flushes are market-wide (many coins
 at once), holes idiosyncratic: report per-day clustering and the share of fills in multi-coin minutes. (4) Thin coins have more holes: control rank tercile.
Change my mind: hole half beats flush half from c[t+1] to t+61 by > 13 bp within each kreach tercile and every explore year, with a monotone quintile dose; else depth or nothing.
PRE-REGISTERED (a, explore 2021-01..2023-12, events = LD1 candidates with a 60-min per-coin lock, no slot rule; also the base-simulated taken fills reported):
 split by illiq = Amihud(fill minute, |ln(l/c_prev)|/qv) / coin's trailing 30-d median minute Amihud (daily medians, lagged 1 d). PASS = hole half minus flush half, simple return
 c[t+1] -> c[t+61], >= +13 bp AND day-clustered bootstrap p < 0.05 AND > 0 in 2021, 2022, 2023 AND > 0 in >= 2 of 3 kreach terciles AND quintile means rank-corr >= 0.6. Also
 reported: from the quote to t+61/241/1441, mean AND median, worst day. Prior medium-low (T1: the cascade is what pays the ladder, flushes may be exactly the good fills).
LD3 a done (is3_ld3.py, ld3_explore.json; 1047 events <=2023): hole half c[t+1]->t+61 +150 vs flush +66 bp (diff +84, p .002, dose rank-corr .9, every year +): PRE-REG PASS. Not entry depth (OLS illiq +166 bp se 49
 with d1/kreach). But from our QUOTE no gap (q61 +8): holes sit 72 bp lower at t+1 and return to the same level -> the resting ladder gains nothing; live form = a taker add-on at c[t+1]. Delay t+2 +73, t+5 +36.
LD3 b done: relvol/trade count/trade size weaker same sign (p .27-.56, 2023 <0); taker-sell share reversed (one-sided selling bounces MORE: the forced sellers pay, T1). FAIL.
LD3 c restated (form c "skip fills" is not live-implementable: the fill minute's volume is known after the fill): d = taker add-on at c[t+1] on hole fills (frozen threshold 0.9077), confirmT 2024-25, base = flush fills' add-on.
LD3 d confirm (ld3_d_confirm.json): hole add-on 2024-25 +46 vs flush +73 bp (diff -27, p .78, MDE 180; 2024 +95, 2025 -210): FAIL. LD3 CLOSED OPEN. Sceptic: tested N14 on the ladder's own fills, by
 Amihud and by volume alone, from the quote AND from t+1; the claim holds descriptively in 2021-23 but adds nothing to the resting ladder and the add-on did not replicate.

## T9B alpha-decay of the live books' trades (think-through 11:0x UTC 11-27, before any run)
Source: backlog T9b, library N8 (maxdama §7: plot each strategy's signed return from decision to +h; the curve says how much a late fill costs and whether a signal is
 crowded). No chat records. Books: main = blend(listing_short, lowvol, tsmom) on HL 4h; main_bn = blend(carry_trend, carry, xsmom)@bn + flow@bn(lb 3, cap .05) on BN 4h (the 82-coin
 bn set, survivor-biased: stated). Daily rebalances on a 4h grid; live fills land 4-10 min after the 04:00 close (fills table).
Who pays / mechanism: a daily signal built on multi-day features should have a FLAT early curve (alpha spread over days); flow (3-d taker imbalance, metaorder continuation)
 and anything with a reversal leg should front-load. If a curve is steep in the first hours, the 4-10 min live delay and a skipped hourly run cost real bp, and maker execution
 (T9) loses most there (adverse selection). Unstated: (1) part of every target change is vol-rescaling noise with no alpha: report bp per unit of |dw| AND the share of |dw|
 from sign changes / entries vs resizes; (2) funding over hours is tiny, price only, stated; (3) decision time = the 4h bar's CLOSE (index is open time, + 4h), price at D from the
 1h bar ending at D; known-answer check: h = 0 must give exactly 0 and the +4 h point must equal the 4h panel's next-bar return on the same Δw.
Change my mind: delay cost of 1 h >= 3 bp per unit turnover (≈ HL taker fee) in any book -> execution timing is worth a research item; < 1 bp everywhere -> late runs are harmless (close T9-timing).
T9B a/b done (is3_t9b.py, t9b_a.json): BN 2020-26 decay curves FLAT: 1 h late costs -0.5..+1.3 bp per unit turnover (xsmom the only CI>0), 4 h <= 1.2, alpha accrues over 24-48 h
 (tsmom +7/+10, xsmom +5/+10). HL and live-BN windows (7 months) too short (CI +-6 bp at +1h). xsmom first-hour alpha 2.4 (2021) -> 0.1 (2026). Late runs are harmless; T9-timing closed.
 Bug caught by the 4h known-answer check: fillna(0) on hold-NaN targets made fake changes (first run, numbers discarded).
T9B c done (t9b_c.json): live fills 11-13 min after the close; notional drift BN -3 / HL +11 bp but by side it is market direction (side-balanced -0.3 / +2.1 bp). T9B CLOSED DEAD (late runs cost ~nothing).

## X1C fspread_hold@pair robustness (think-through 11:0x UTC 11-27, before any run)
Source: backlog X1c + X1f; findings fspread_hold (X1b/X1c/X1d/X1e). No chat records. Book: lb 14, enter 0.1, max_pair .1, gross 2 (paper) / main@pair alloc 0.5 (gross 1.0, two accounts).
Mechanism: HL longs pay more funding than BN longs for the same coin; short HL / long BN collects the gap, plus ~1/3 from premium convergence. Who pays: levered HL retail longs.
Risks the backtest hides: (1) two accounts: each venue holds one direction, so a squeeze on a held alt drains the HL account while BN gains (11-12: -37% 1 d at gross 2);
 (2) basis excursions (HL mark vs BN mark) are small on average but a single listing/squeeze day can be large; (3) the edge is decaying (21 -> 1.9 %/yr net 2023 -> 2026):
 where is what is left? If it is only in BN 8h-interval coins (where BN funding is sticky and HL's hourly funding diverges) or in a few names, the book is a shrinking niche.
Unstated: margin need = the worst k-day adverse move of one account's legs before a transfer; at alloc 0.5 everything scales by 0.5 of the 11-12 numbers at gross 2 only if the
 book is the same; the 2023-05..2024-06 history (backfilled) adds the worst alt squeezes of 2024-Q1. Change my mind (b): if 2025-26 net is positive only in one interval bucket,
 the live book should be restricted to it (a research decision, written as a backlog line, not done here). Form c needs >= 30 live days (live since 11-12: 15) -> defer to 12-12.
X1C a done (is3_x1cp.py, x1cp_ab.json): at alloc 0.5 (1x per account) worst account HL -18/-27/-46% (1/3/7 d, 2024-11), BN -27/-39/-42% (2025-10-10); basis p99 32 bp, max 527 (TON). Daily re-split needed, weekly is not safe.
X1C b done: 2026 YTD the edge is in BN 8h-interval coins (+2.3% vs 4h +0.25%: 4h churns 2x and loses on price), but 2025 the 4h bucket was better (+3.5 vs +2.4): no restriction. Form c deferred to 12-12 (30 live days, X1f).

## T8R market regime -> live BN books (think-through 11:1x UTC 11-27, before any run)
Source: backlog T8 (trend/carry vs BTC vol regime or funding level); no chat records. Books: flow@bn (lb3 cap .05), blend@bn (carry_trend, carry, xsmom), xsmom; bnall 1d, explore 2021-23.
Mechanism: cross-sectional books earn from dispersion and persistent flows; in high-vol, one-factor markets (BTC crash/squeeze) correlations go to 1, dispersion is noise and the
 books pay costs for nothing; hot aggregate funding = crowded longs -> momentum longs are the crowd (crash risk), carry pays. Who pays: late momentum chasers / levered longs.
Unstated / must be true: (1) the state must be known at the close before trading (lag 1 d); (2) a state that only cuts exposure must beat random masks of the same share and
 persistence (F0), regime masks are very persistent, so the random masks are too; (3) the books are vol-targeted already: high-vol days get smaller weights, so the state view must
 be per unit of risk (SR per state), not raw return; (4) 2021-23 has 3 regimes only (bull, bear, chop): a state rule is close to a year dummy, so every year must agree.
Change my mind: SR in the worst state tercile <= 0 in all 3 explore years for a book with a dose (middle state between) -> one filter; anything else -> regimes are noise for these books.
T8R a/b done (is3_t8r.py, t8r_ab.json): pooled terciles are year dummies; within-year, flow weakens in high BTC vol (2.58/1.76/0.33, top tercile yrs 1.1/1.3/-2.1) and after strong BTC
 rallies (vs MA50 0.43, ret30 0.67); hot market funding is GOOD for blend (carry). No book x state has a bad state <= 0 every year: pre-stated bar not met.
PRE-REGISTERED (c, written before the run): the strongest dose = flow@bn x BTC 30-d vol. Causal rule: HALVE flow@bn (k 0.5) on days when BTC 30-d realized vol (lagged 1 d) is above the
 2/3 quantile of its own trailing 365 days. F0 judge, explore 2021-23, 200 random same-share same-persistence masks with the same halving. PASS = dSR > 0 at >= 95th pct AND dSR > 0 in
 2021, 2022 and 2023. Only then ONE confirmT. Prior low (a/b missed the bar; this is the closest cell, so selection is acknowledged).

## L6V range/HAR vol forecasts for vol targeting (think-through 11:0x UTC 11-27, before any run)
Source: library N6 (bencik-2014: Parkinson/GK ~5x more efficient than close-to-close; HAR on realized range forecasts best), backlog L6. No chat records. Not alpha: risk.
Mechanism: the books size by trailing close-to-close covariance (vol_target, 60 d) and per-coin ewm std; a noisy or slow vol estimate makes the book over-levered right after
 calm spells (when vol jumps) and under-levered after spikes. A better forecast = realized vol closer to the 25% target, smaller worst months, same SR.
Unstated / must be true: (1) Parkinson needs clean highs/lows: Binance wicks (one-tick liquidation spikes) inflate it on thin coins: report by liquidity tercile;
 (2) Parkinson is biased low vs close-to-close with drift/jumps: compare with and without a constant scale fitted on 2021-22; (3) the portfolio error in crashes is mostly the
 CORRELATION jump, which no per-coin variance fixes: form b measures exactly that (realized vs target); (4) HAR fitted pooled on 2021-22, scored on 2023 only (no in-sample scoring).
Change my mind: range/HAR beat cc60 QLIKE by >= 10% out-of-sample on the liquid two-thirds of coins -> form b; else the estimator is not the problem.
L6V a done (is3_l6v.py, l6v_a.json): 2023 OOS QLIKE HAR-Parkinson .524 / ewm20 .539 / cc60 .603 (what vol_target uses); HAR over-forecasts (log error .495 vs .459), ewm20 wins both metrics every year.
 Pass the pre-stated 10% bar (QLIKE) -> b: vol_target with ewm20 (and HAR) variances, correlations from 60 d.
L6V b done (l6v_b_explore.json): ewm20 variances cut quarterly vol tracking error vs cc60 by 23% (xsmom), 18% (tsmom), 9% (blend), SR same or better; HAR over-forecasts. Bar met by xsmom only ->
 PRE-REGISTERED L6V_ewm20_vt_xsmom (confirmT one run, TE cut >= 20% and SR loss <= .1); blend/tsmom reported descriptively on the same run.
L6V c confirm (l6v_b_confirmT.json): xsmom TE -12% (needed -20), SR 1.31 -> 1.10: FAIL. Same run: blend TE -22% (SR +.08), tsmom -12% (SR +.04). ewm20 tracks better in 6/6 cells, SR mixed. L6V CLOSED OPEN.
 Sceptic: tested the estimator where it is used (vol_target diagonal), on 3 books, out-of-sample; HAR as N6 says forecasts better by QLIKE but over-forecasts, which hurts a vol target.
T8R c done (t8r_c.json): halving flow in high BTC vol = random masks (dSR 0.00, 66th pct; 2022 -0.27). T8R CLOSED DEAD (6 states x 3 books; year dummies; vol targeting already does the job).

## LS1 listing_short on HL with the backfilled funding (think-through 11:1x UTC 11-27, before any run)
Source: backlog T2b(a), findings listing_short (HL OOS 0.89, "funding known for only 28% of HL short exposure"). No chat records. Book = HL main blend leg (listing_short defaults, HL 1d).
Mechanism: new perps are over-priced at listing (airdrop/unlock supply, retail hype) and decay ~linearly to d120 (T2b b). Who pays: the late long buyers. Risk: the SHORTS of a hyped
 new coin are the crowded side early on: if HL longs are short-squeezed and funding turns negative, the short PAYS funding, possibly as much as the decay earns in the first weeks.
Unstated: (1) the 2023-05..2024-06 window is new to HL funding (backfilled 11-26): the old WF counted zero funding there, so the comparison 'masked vs full funding' on the same
 weights isolates the funding hole exactly; (2) 8-hourly vs hourly funding era (pre/post 2023-06) is handled by the daily sums (FC1C note); (3) coins listed after 2024-07 always had funding.
PRE-STATED (a): FRAGILE if, with full funding, SR without the best 10 days < 0.3 OR SR before 2024-07 < 0 (the LV2c rule). Report funding paid %/yr by year next to price P&L.
Form c (fetch the missing coins): the fetch is already complete (134/134 coins with HL candles before 2024-06); c is a coverage check only.
LS1 a/b/c done (is3_ls1.py, ls1_a/b.json): listing_short HL with full funding SR 1.36 (masked 1.44), shorts pay 7-10%/yr in 2023/25/26, not FRAGILE (.82 w/o best 10, .78 pre-2024-07). Per event median
 listing pays the short (+2.2% by d90), mean -2.0% (squeezed tail); 2026 cohort -15% funding by d90 (n 8). Uncovered 5% = DOGE/INJ 2023-04 (old tokens new on HL). LS1 CLOSED OPEN (passes).

## LV3 lowvol by idiosyncratic vol (think-through 11:1x UTC 11-27, before any run)
Source: backlog LV1 (b); findings lowvol (LV1: 4 forms fail net of funding; price-only spread positive .17-.31 explore; LV2: excluding negative-funding shorts = random). No chat records.
Mechanism: the low-vol anomaly in equities is mostly an IDIOSYNCRATIC-vol effect (lottery demand for coins with big own-moves); total vol in crypto is mostly BTC beta x BTC vol,
 which the hedge removes anyway, so ranking on total vol mixes the lottery signal with beta. Who pays: lottery buyers of coins with big idiosyncratic swings.
Unstated: (1) idio vol is ~80-90% correlated with total vol cross-sectionally in alts: the double sort (idio within total-vol terciles) is the test of 'adds anything'; (2) high idio-vol
 names are also new listings / squeezes: funding matters (LV1's failure), report price-only AND net; (3) the beta estimate is noisy for young coins (min 20 d), they get beta 1.
PRE-STATED (a, explore 2021-01..2023-12, bnall 1d, top-30 and top-100, rank weights, legs 0.5/0.5, beta-hedged, next-day simple, net of funding, gross of costs): PASS = net SR >= 0.5
 AND 3/3 years > 0 AND > total-vol ranking's SR on the same universe, in at least one universe. Prior low (LV1: 2021 -0.9 every form).
LV3 a/b/c done (is3_lv3.py, lv3_ab.json): idio vol = total vol (rho .93); idio ranking SR -.32/-.04, double sort -.81/-.32, low-idio long leg = average coin. High-vol coins lose in the MEDIAN (-90 bp/d) not
 the MEAN (+11): pops pay the short back. LV3 CLOSED DEAD (7 forms with LV1).

## LSF listing_short squeezed-tail exit (think-through 11:2x UTC 11-27, before any run)
Source: LS1 b (HL: median listing pays the short +2.2% by d90, mean -2.0%: a squeezed minority; 2026 cohort -15%). No chat records. Book: listing_short (HL main blend leg).
Mechanism: a new coin whose perp funding goes deeply negative has a crowded short side (everyone shorts the new listing); spot holders/market makers squeeze it and funding
 transfers money to longs every 8 h / 1 h. Two readings: (1) squeeze in progress -> the short keeps losing price AND paying funding: exit; (2) funding extreme = capitulation of
 the longs is over, the crowd short is the peak -> holding pays the decay later. The state -> distribution view decides between them.
Unstated: (1) state at the close (trailing 3-d funding received by the short, known), outcome = next 7-d short P&L (price vs BTC + funding); (2) control for the past 3-d price move
 (a squeeze shows in both); (3) exits cost a round trip and the short may be re-entered later: the filter (b) is judged with the DELAY/exit transform vs random masks;
 (4) form a uses bnall 2021-23 ONLY: HL is kept clean as the held-out venue for c (I have seen only LS1's per-cohort means on HL, not this state view).
Change my mind: the lowest-funding quintile's next-7-d short P&L is below the others by > 100 bp with a monotone dose in every explore year -> exit rule; else hold everything.
LSF a done (is3_lsf.py, lsf_a.json, bnall 2021-23): REVERSED. Shorts paying heavy funding do fine afterwards (q0 +157 bp/7d); shorts RECEIVING high funding (crowded longs, pump in progress)
 lose on price (q3/q4 -328/-157 bp/7d, -1069/-2425 /30d) but in the MEAN only (medians +371/+415): a few pumps, mostly 2021 (2022 opposite). Same as FC1C b on HL (high-gap shorts lose next day).
PRE-REGISTERED (b, written before the run; data-mined from a, stated): EXIT listing_short shorts on days when the coin's trailing 3-d funding sum (known at the close) >= 0.0035 (explore
 80th pct, rounded), F0 'apply' transform side -1, bnall 1d explore 2021-23 vs 200 random masks. PASS = dSR > 0 at >= 95th pct AND dSR > 0 in 2021, 2022, 2023. Then c = ONE frozen run on HL
 listing_short (2023-05..2026-11, the live venue, never used to choose). FC1C d (block HL high-gap shorts) passed explore and failed confirm: prior low.

## FSM fspread_hold@pair with maker legs (think-through 11:2x UTC 11-27, before any run)
Source: findings T9 (maker DEAD for directional daily books: unfilled orders chase drift; "revisit for non-directional books (fspread)"), X1C b (2026: costs ~1.9% vs gross ~4%).
Mechanism: fspread's legs are opened for carry, not for direction: a pair entered a few hours later earns almost the same carry (trips last ~60-70 days), so the adverse selection
 that killed T9 (a resting order fills when price moves against the signal) should be small: the pair's price legs cancel. Who pays: nobody new; it is a cost cut.
Unstated: (1) fills are judged per leg on its own venue's hourly OHLC (5 bp trade-through, kripto.execution.maker_fills, the T9 model), maker fee 2 bp (BN; HL 1.5) vs taker 4.5;
 (2) a leg that fills while the other does not leaves a one-venue position for up to k hours: its drift is charged by the T9 fallback (drift to +k h + taker), so the unhedged
 interval is in the cost; (3) only 2026-04-15..2026-10-31 has hourly data on both venues (HL 1h since 04-14, bn100 1h to 10-31): ~6.5 months, few trips: descriptive, state n.
Change my mind: maker+fallback cuts fspread's 2026 cost by >= 30% at k = 4 h without a drift cost eating it -> backlog line for research (execution change for the pair venue).
LSF b done: exit shorts with hot funding (>= .0035/3d) = random masks (dSR +.02, 53rd pct; 2022 -.11). c skipped (HL held-out kept clean). LSF CLOSED OPEN (MDE 149 bp/7d).
FSM a/b/c done (is3_fsm.py, fsm_abc.json, fsm_b.json; 2026-04..10, ~35 events): maker legs for fspread lose: both-maker+fallback cost 3.4-3.6 vs taker 2.5 %/yr (unfilled legs drift 130-340 bp),
 maker-one-leg + hedge on fill -9..-11 bp per event: the move that fills one leg is against the other (same asset). FSM CLOSED DEAD.

## X1H fspread_hold churn / exit band (think-through 11:2x UTC 11-27, before any run)
Source: X1C b (2026: 4h-interval coins +0.25% net after 1.3% costs, churn 2x 8h coins), findings fspread_hold (trips ~60-70 d). No chat records.
Mechanism: the exit is 'the 14-d mean spread changes sign'. When the spread hovers near 0 (gap closing, 2025-26), a pair flips in and out: every flip = 4 taker legs (~35 bp of leg
 notional) for little carry. A wider exit band (hold until the spread is clearly the other way, -x) cuts flips, at the price of holding pairs that pay a small negative carry.
Unstated: (1) entry stays at |s| > .1; (2) the band changes WHEN slots free up, so it can block better new pairs: report slots used; (3) the costs are taker + volume-scaled slip on both venues.
PRE-STATED (b): variants x in {0.05, 0.10} (exit when s crosses -x in the trade's direction), explore 2023-05-15..2024-12-31; pick = higher net %/yr if it beats the live rule by >= 0.5 %/yr at
 gross 2 with SR not lower; then c = ONE run 2025-01..2026-11 (seen by the X1e WF: a second look, stated). Prior medium (cost arithmetic), but 2023-24 had a wide gap and little churn.
X1H a done (is3_x1h.py, x1h_a.json): trips < 14 d grew 7/6 -> 22/14 (2025/26) and lose .65/.76 %; median trip 90 -> 37 d; 4h-interval coins churn (median 16 d in 2025).
X1H b done (x1h_b.json): exit band on 2023-05..2024-12: cost 3.6 -> 2.9 %/yr but net 22.3 -> 21.0/21.7 (carry lost): FAIL; that window had no churn. d added: ONE second-look run of x .05/.10 on 2025-01..2026-11 (stated).
X1H d done (x1h_d.json): 2025-26 band x .05 +0.34 %/yr (SR 3.6 -> 4.3, costs 3.35 -> 1.95) < +0.5 bar: FAIL narrowly. X1H CLOSED OPEN; forward re-run of frozen x .05 on 2026-12..2027-05 noted.

## LVH lowvol: HL vs bnall (think-through 11:2x UTC 11-27, before any run)
Source: LV2c (HL lowvol SR .70 2023-03.., 2025 2.36, w/o best 10 days .23: FRAGILE), LV1/LV3 (bnall dead, 7 forms), the HL main book holds lowvol via the nested choice.
Question: the same rule (top-30 by volume, 30-d vol rank, beta-hedged, weekly tranches, 20% vol) works on HL and not on bnall. Either (i) the PERIOD (2023-26 vs bnall's 2020-23 explore),
 (ii) the UNIVERSE (HL's top-30 = HL-listed coins incl. HL-only memecoins/k-prefix, a different cross-section), or (iii) the VENUE's prices/funding (HL funding on the short leg).
Unstated: the strategy function itself (weekly tranches, vol target), not LV1's daily rank proxy, must be what is compared; the HL universe at each date = coins with an HL close that day.
Plan: a = HL decomposition (legs, price vs funding, coins, years); b = the SAME function on bnall 2023-03..2026-11 (full) and on bnall restricted point-in-time to HL-listed coins;
 c = if universe: which names; if period: the regime state reading. Descriptive (not registered); nothing changes the live book from here (the nested refit decides).
LVH a/b/c done (is3_lvh.py, lvh_ab.json, lvh_c.json): it is the UNIVERSE: same function same dates bnall SR .05, bnall restricted to HL-listed coins .90, HL .73. BN-only coins (17% of exposure,
 mostly shorts) lose -12.4 %/yr and pay -92 %/yr funding per unit as shorts (vs -6 % HL-listed). LVH CLOSED OPEN (explained); backlog: HL-listed universe filter for BN books' shorts.

## HLU1 HL-listed universe filter for BN books' shorts (think-through 11:3x UTC 11-27, before any run)
Source: LVH c. Mechanism: Binance lists many small caps HL does not; their perps are where crowded shorts get squeezed (thin float, -92 %/yr funding to shorts). HL's listing choice is a
 point-in-time quality screen. Who pays: the short side of BN-only names pays the longs (funding) and the squeezes. The BN books (flow, xsmom, blend) short the weakest names, which are
 disproportionately these. Unstated: (1) the filter must beat random masks blocking the same share of short exposure (F0); (2) HL listings are known that day (HL panel close notna);
 (3) HL panel starts 2023-03 -> explore 2023-04..2024-12, confirm 2025-01..2026-11 (new samples hlu_* in is3_lib); (4) flow and xsmom on bnall are survivor-free.
PRE-STATED (b): PASS = dSR > 0 at >= 95th pct of 200 random masks AND dSR > 0 in 2023 and 2024 (explore halves). At most 2 books to one confirm (c).
HLU1 a done (is3_hlu1.py, hlu1_a.json): REVERSED for the momentum/flow books: BN-only coins (16-20% of short exposure) are their BEST shorts in 2023-24 (+83..+135 %/unit-yr price, funding received);
 the lowvol tail (LVH) is a lowvol-specific selection (high-vol BN-only names, 2025-26). b/d run for the record in unit is3-hlu1 (expected to fail).
HLU1 b/d done (hlu1b.json, hlu1d.json): blocking BN-only shorts costs SR (-.31..-.69, = random), funding-extreme block (f7 < -.5) random (-.02..+.05). c skipped. HLU1 CLOSED DEAD (lowvol-specific tail).

## X1V fspread_hold@pair live vol vs backtest (think-through 18:4x UTC 11-27, before any run)
Source: backlog X1f, strategies.json note (live 4.2%/yr equity vol in 15 d vs backtest 1.4%). No chat records.
Three explanations: (i) mark noise (HL markPx vs BN markPrice: no economic risk), (ii) leg timing (legs traded at different times, basis moves between), (iii) real: the live days
 were volatile for the hedged book OR live holds different pairs. Test: replay the LIVE positions on research 00:00 closes (trade prices, both venues same instant): if replay vol ~ live,
 (i)/(ii) are out; then compare with the backtest's own returns on the same days and its 10-d vol distribution. Change my mind: replay vol < half live -> marks/timing.
X1V a/b/c done (is3_x1v.py, x1v_a.json, 10 days to panel end 11-21): live 3.14%/yr, replay of live positions 2.84 (corr .88), backtest's own 3.1 on the same days = 98th pct of its 10-d vol
 (median 1.0). Legs filled 2 s apart; residual live-replay $1.6/d. EXPLAINED by regime; no DSR recompute. Side fact: only 4.2 of 7.4 live pairs are the backtest's (live universe/path).

## BNH HL main book (blend_nested = listing_short + lowvol + tsmom) dependence on lowvol (think-through 18:5x UTC 11-27, before any run)
Source: LV2c (HL lowvol SR .70 from 2023-03; 2025 2.36, other years ~0; w/o best 10 days .23: FRAGILE), LVH (it works on HL because of the HL-listed universe). No chat records.
Question: is the HL main book's backtest (1.87 nested) carried by one lucky lowvol year, and did the nested selection pick lowvol only because of 2025?
Mechanism if real: low-vol anomaly = lottery demand; high-vol alts are overpriced by retail and bleed (short pays) except in pops. On HL the shorts are HL-listed (less squeezable).
Unstated: (1) the blend vol-targets the SUM, so a leg's contribution is not its stand-alone P&L: attribute with the blend's own scale k_t (stated approximation); (2) leave-one-out
 blends are new configs: logged via research.evaluate tag bnh (raises N by 3; descriptive, no promotion); (3) the nested choice is from an expanding window: truncate the panel at 2024-12-31
 to see what it would pick without 2025. Nothing changes live before the 2027-01-02 refit (M1 rule); the verdict is a flag for that refit.
Change my mind: lowvol share of blend P&L <= its 1/3 risk share outside 2025 AND the blend without it loses >= .3 SR in >= 2 years -> keep, not luck. Otherwise flag luck-driven.
BNH a/b/c done (is3_bnh.py, bnh_a/b/c.json): HL blend 1.34 with lowvol vs 1.30 without (listing_short carries: +102% of +178% P&L, tsmom +50, lowvol +26 of which +24 in 2025).
 lowvol = long majors / short alts (2023-24 longs pay, 2025 shorts pay, diffuse: top-5 coins 41%). Picked at the 2025-01-12 refit on prior-data SR .43 -> 2025 was OOS. KEEP; no dependence.

## L3S backtest slippage model vs live paper book walks (think-through 19:0x UTC 11-27, before any run)
Source: backlog L3 (library N3: impact ~ sqrt(size/ADV)). No chat records. kripto/backtest.slippage_model = 3*sqrt(50e6/ADV7) bp, clip 1.5..25, SIZE-INDEPENDENT, + taker fee.
Live paper fills walk the venue's live L2 (top 20 levels) at fill time: slip_bps = |px - mid|/mid (half-spread + depth). ~2,360 taker fills 11-09..11-27, $5-$400 orders.
Who pays: nobody; this is measurement. Unstated: (1) the walk is itself a model (snapshot, no latency, no queue), but at $10-400 the half-spread dominates and the snapshot is real;
 (2) the model's ADV is the panel's trailing 7-d USD volume at D-1 (what a backtest would use for day D); (3) ladder/maker fills and 'retired' liquidations are excluded/split.
Change my mind: median ratio model/walk within 0.5..2 in every venue x liquidity tier -> model OK; a tier where the model is > 2x off -> c quantifies the cost-line error.
L3S a/b/c done (is3_l3s.py, l3s_a/b/c.json, data/is3/l3s_fills.parquet): 2,363 live taker fills, walk median .7-.75 bp vs model 1.6 (BN) / 4.8 (HL). Shape matches (ADV slope -.58/-.46 vs -.5),
 level ~2x high; HL size slope +.2. Re-costed 2025-26: costs drop .65-2.2 %/yr (HL blend most, SR +.08). Model kept (conservative, never under-states). CLOSED OPEN (measured).

## X1U fspread_hold@pair on the live universe and a cold start (think-through 19:0x UTC 11-27, before any run)
Source: X1V side fact (4.2 of 7.4 live pairs = the backtest's). Live (kripto/venue_pair.py): universe = HL top-60 by 24-h notional AND BN top-60 (+ held), Binance funding from a cache
 that started 2026-09-13 (60 d before the first fetch, then grows), so the hysteresis path started ~09-27 and new coins start later. Research: every coin with funding on both, path since 2023.
Two differences: (i) UNIVERSE: live cannot see mid-cap pairs outside either top-60 (e.g. VVV: research's longest holding, not in live); research's top-20-by-volume filter is computed within
 the eligible set, so the live set is a stricter, more liquid subset; (ii) PATH: a cold start picks the |s| leaders of the day; the continuous run still holds older pairs whose spread is smaller
 but same-signed (hysteresis). Unstated: the carry of the pairs only research holds is the question; costs of the restart; whether holdings converge.
Change my mind: live-universe net %/yr within 1 %/yr of research in 2025-26 and paths converge in < 60 d -> no action; else the live book's expectation in STATUS/notes is the live-universe number.
X1U a/b/c done (is3_x1u.py, x1u_a/b/c.json): live-universe proxy (held legs kept) = research (4.2 vs 4.1 %/yr 2025-26, overlap 92-99 %); forcing exits on list drops would cost 1.8 %/yr (live doesn't).
 20 cold starts: overlap 50 % d0 -> 90 % d60, -0.3 % net once. Live replay from the 09-27 cache start matches 70 % of live pairs (continuous 54 %); funding inputs identical to the bp. CLOSED OPEN (explained).

## LSV listing_short sizing: new-coin vol under-estimated (think-through 19:0x UTC 11-27, before any run)
Source: backlog T2b (c); BNH (listing_short = the HL main book's edge). No chat records. Code fact: vol_target uses returns(panel).fillna(0) over 60 d, so a coin listed a days ago
 has 60-a zero returns in its window: its vol is estimated at ~sqrt(a/60) of the truth; listing_short holds only coins aged 2..61 d, so the ex-ante book vol is biased low and the scale
 goes UP until max_gross 1.5 binds. beta_to needs 20 d (young coins: NaN beta). Who pays: nobody; this is risk. A short in a 3-day-old coin is the riskiest position the book has (squeezes).
Unstated: (1) if max_gross binds nearly always, the vol target is inert and the 'fix' is a gross choice (then it is a sizing parameter, judged by realised vol, not SR); (2) a floor changes
 WHICH days are big (more gross when names are older), which could cut the squeeze tail; (3) explore bnall 2021-23 only; HL is the held-out venue.
Change my mind: realised book vol >= 1.5x target or gross at the cap > 50 % of days -> the estimate is broken and b's floors are worth testing; else the bias is harmless.
LSV a/b done (is3_lsv.py, lsv_a/b.json): zero-filled vol under-estimates new coins 4x (age 1-7 d) -> 0.9x (31-61); book vol 25-27 % vs 20 target, cap never binds. Floors on bnall 2021-23:
 fixed 150 % vol on target, worst-10 -4.7 -> -3.6 % but SR .18 -> -.01; own-days SR .35 but worse worst days: both FAIL. c skipped. CLOSED OPEN (harmless: main_scale fixes book vol).

## FST Binance 8-h funding settlement drift (think-through 19:1x UTC 11-27, before any run)
Source: backlog T13 (funding settlement seasonality); E2/E2B (execution clock of the BN daily books). No chat records.
Mechanism: funding is paid only by positions open AT 00/08/16 UTC. When the rate is large, the paying side (longs if positive) can close just before and reopen just after: price pressure
 against the payer in the last hour(s), reversal after. Arbitrageurs (basis traders) do the opposite, so any effect should scale with |rate| and shrink over the years.
Unstated: (1) the rate is mostly known before settlement (premium average): use the PREVIOUS print as the causal signal, the current print only as a check; (2) market-relative returns
 (minus the 82-coin equal-weight hour return) to remove clock effects; (3) placebo = the same coin's hour 4 h earlier (no settlement for 8-h coins); (4) only 0/8/16 settlements, coins on 4-h
 intervals that day excluded; (5) explore = 2021-23, coin half 0; at 1 h holding no taker trade survives (26 bp ladder): the only use is an execution tilt (c) or a maker timing rule.
Change my mind: pre-settlement return against the payer > placebo with a dose in |rate| in every explore year -> b/c; else DEAD/FEATURE with MDE.
FST a/b/c done (is3_fst.py, fst_a/b/c.json): no settlement drift (pre/post hour vs 4-h-earlier placebo diff -0.2/+0.0 bp, MDE 0.5; no dose; xs extremes 2-4 h = placebo, MDE 2-3.6).
 Mechanical deferral of payer-side opens past 08:00: flow@bn +0.23 %/yr (2026 .09), blend .11: 0.8 bp/moved unit vs ~5 bp drift noise. CLOSED DEAD.

## KSW kill switch -25 % from peak: false alarms vs power (think-through 19:1x UTC 11-27, before any run)
Source: config/risk.json kill_drawdown .25 (every book), design.md (flatten + halt until a review). No chat records. Not a signal: a risk-rule audit with a general criterion.
Question: at each main book's live sizing, how often does -25 % fire if the backtest edge is real (false alarm: it halts a good book, and in a real account a halt locks in the loss),
 and how fast does it stop a dead or broken book (power)? A stop that fires on a good book about as often as on a dead one is noise. The other stop is design §4's demotion (live 60-d SR < 0).
Unstated: (1) daily closes under-state intraday troughs (the live watcher marks every 20 s): report daily and add the worst intraday/close gap where the bn 1h panel allows; (2) block bootstrap
 (30-d blocks) keeps vol clustering; (3) main_bn = 0.5 flow@bn + 0.5 blend_nested@bn x main_scale 1.156, main = blend x .871, main@pair = fspread_hold x .5; the ladder sleeve is ignored.
Change my mind: P(kill | real edge, 2 y) > 10 % or P(kill | zero edge, 2 y) < 30 % -> the threshold is mis-set for its job -> backlog proposal (vol-scaled). Else keep and write the numbers.
KSW a/b/c done (is3_ksw.py, ksw_ab/c.json): -25 % kill: 2-y P(kill) real edge 11-13 %, zero edge 72-81 %, -0.5 SR 90-92 %; k x vol: 1.0 15/75-84, 1.25 4/50-65. Pair book: never (vol .8 %),
 its risk is per account. Backlog KS1 (vol-scaled kill 1.25 x target + per-account guard for main@pair), design change for a research session. CLOSED OPEN (measured).

## PBT fspread_hold@pair entry timing by the HL-BN basis (think-through 19:1x UTC 11-27, before any run)
Source: X1C a (|basis| on held pair-days p50 5 bp, p99 32). No chat records. A pair short HL / long BN (O = +1) gains price P&L if HL is rich at entry and the basis closes: P&L ~ -O x d(basis).
Who pays: whoever pushed one venue's price away (HL retail longs chasing, paying the funding that made s > 0): the same crowd that creates the carry may also make HL rich.
Unstated: (1) signed basis relative to the coin's own 30-d median (structural offsets: index definitions, kPEPE units); (2) daily closes at 00:00 vs live fills at 00:13: a basis that closes within
 minutes is not capturable: report d+1 and d+3 separately; (3) waiting costs carry (~1.6 bp/day per pair in 2026) and slots; (4) explore = entries 2023-05-15..2024-12-31.
Change my mind: trip price P&L rises monotonically with signed entry basis and the top-vs-bottom quintile gap > 20 bp per trip -> b; else DEAD-ish (basis too small vs carry).
PBT a done (pbt_a.json): 89 explore trips, signed entry basis quintiles -> trip price P&L -19.6 .. +11.0 bp/leg unit (Spearman .53; q4-q0 +36/+29 by year); half of it reverts on day 1.
 Reality check on 40 live pair trades: fill-minute basis vs the 00:00 close basis Spearman .57, median |diff| 4.0 bp = the median |basis| (4.5): the daily signal is only partly capturable.
PRE-STATED (b, unchanged from the queue): open an eligible pair only when sb >= 0 (signed basis >= its 30-d median) or after waiting k in {2, 5} days; explore 2023-05-15..2024-12-31;
 PASS = net >= live + 0.5 %/yr at gross 2, SR not lower, better in 2023 AND 2024. Upper bound (fills at the close basis).
PBT b/c done (pbt_b.json): wait <= 2 d -0.4 %/yr, <= 5 d +0.46 (2024 worse): FAIL. Diagnosis: ~1-1.5 bp of equity per improved trip, eaten by carry/slot changes, partly invisible at 00:13. CLOSED OPEN.

## HLI HL main book when listing_short is idle (think-through 19:2x UTC 11-27, before any run)
Source: BNH; 11-27 check (research and live listing_short both hold nothing; live = research, so not a pipeline fault). No chat records.
Mechanism: listing_short needs a stream of new HL perps with >= $1M 7-d volume; HL lists in waves (meme/airdrop seasons). When none qualify, the blend's sum is lowvol + tsmom only and
 the book-level vol target scales them UP to the full 25 %: the book becomes a different, weaker strategy (no_listing_short SR 1.06 in BNH) at full risk.
Unstated: (1) whether the full rescale is right (equal-risk would leave listing_short's share in cash); (2) the idle share is the forward-looking fact: if HL listings dry up, the headline
 SR is the wrong expectation; (3) the $1M floor may cut events in quiet months, but changing it is a research-session WF, not this item.
Change my mind: idle-day SR of the blend < 0.5 AND idle share rising in 2026 -> STATUS must quote the idle-spell expectation; cash-on-idle better than rescale -> backlog proposal.
HLI a/b/c done (is3_hli.py, hli_a/b.json): listing_short idle 21 % of 2026 days; qualifying HL listings 69/64/57/10 per year (2026 to Sep); $1M floor drops only 21 weaker events.
 Idle-day blend SR -1.8 (n.s.); cash-on-idle 1.39 vs 1.34 -> backlog HLI2. CLOSED OPEN (explained).

## TSH tsmom leg of the HL main book (think-through 19:2x UTC 11-27, before any run)
Source: BNH (tsmom +50 % of the HL blend's P&L, yearly .21/.05/.00/.24 attributed), nested log (tsmom kept at expanding SR .39, the 3rd pick). No chat records.
What it is: per-coin trend (7-56 d blend), top-20 by volume, NOT market-neutral: net exposure = the sum of the coins' trend signs, i.e. mostly a market-timing bet with alt beta.
Who pays: late trend-followers / forced sellers in crashes (crisis alpha) - if real it should pay in BTC's worst weeks (convexity) and hedge listing_short's squeeze days (alt rallies).
Unstated: (1) since HL listing flow fell (HLI), tsmom is half the HL book in idle spells; (2) a refit could drop it (3rd pick at .39): which strategy is 4th matters for the 2027-01-02 refit.
Change my mind: tsmom earns its P&L in BTC's worst/best weeks (convex) and is negatively correlated with listing_short on its worst days -> keep is well-motivated; if its P&L is net-long beta
 in bull months only, it is an alt-beta leg the book could get cheaper.
TSH a/b/c done (is3_tsh.py, tsh_ab/c.json): tsmom HL = convex alt-trend (BTC worst-20 weeks +3.1 %/wk, best +1.9, others -0.3), alts carry it, net exposure ~0, hedges listing_short's
 worst days (+0.5 vs -4.7 %). Nested pool 11-27: ls 1.36, lowvol .71, tsmom .50, xsmom_k .30. CLOSED OPEN (kept).

## F0C cash-on-idle vs random day masks (think-through 19:2x UTC 11-27, before any run)
Source: HLI a. Mechanism: when listing_short is empty, the vol target re-inflates lowvol + tsmom; leaving the third in cash keeps their risk constant. Any exposure cut on a book with a positive
 drift lowers return; on a book whose idle days are bad it helps: the F0 question is whether THOSE days are worse than random days. Idle days are clustered (spells), so circular shifts keep runs.
Unstated: on explore 2023-24 only ~48 idle days (low power: say so); the full-sample number was seen in HLI a.
PRE-STATED: PASS = dSR > 0 at >= 95th pct of 200 random masks (explore), then one confirm run on hlu_confirm after L.prereg.
F0C a done (F0C__hlu_explore.json): cash-on-idle dSR +.06 = 54th pct of random day masks: exposure effect. b skipped, HLI2 closed. CLOSED OPEN.

## BNB main_bn legs (think-through 19:2x UTC 11-27, before any run)
Source: L3S c (flow@bn 2025-26 SR .49, blend_nested@bn .73), KSW (mix SR 2.02 in-sample). No chat records. main_bn = 0.5 flow@bn + 0.5 blend_nested@bn (x main_scale 1.156), not re-vol-targeted:
 a leg's contribution is linear (0.5 x 1.156 x its weights). Question as BNH: which leg carries the alternative home of the $1,000, in which years; is flow's fade costs, funding or price?
Unstated: bnall 2021-23 is also where both legs were chosen (in-sample; flow params = WF fold choice): the by-year view is descriptive only; the 2025-26 numbers are the closest to forward.
Change my mind: if one leg carries > 80 % of 2024-26 P&L and the other is ~0 net of costs, STATUS should say main_bn is effectively one strategy.
BNB a/b/c done (is3_bnb.py, bnb_ab/c.json): main_bn mix SR 1.83 (2025 .59, 2026 1.16); legs 45/55 % of 2024-26 P&L; 2025-26 price ~0 (flow) / -10..-16 % (blend), funding +9..+23 % carries both.
 Nested bnall pool 11-21: carry_trend 1.33, carry 1.31, xsmom 1.25, tsmom 1.17. CLOSED OPEN. (bnall is refreshed weekly: ends 11-21, not a fault.)

## CRB carry legs of blend_nested@bn: funding received vs price lost (think-through 19:2x UTC 11-27, before any run)
Source: BNB b. Mechanism: carry shorts names whose longs pay most and longs names whose shorts pay; the payers are crowded for a reason (trend, squeeze, listing hype), so price moves
 against the carry book: it is paid to warehouse crowding risk. At the extremes (deeply negative funding = a crowded short being squeezed, or a runaway long) the price risk may exceed the carry.
Unstated: (1) funding is known (7-d trailing); the price loss is the cost; dose by |funding| decile per side; (2) the extreme decile may be where most funding comes from (removing it costs carry);
 (3) explore 2021-23 only for the filter (c), pre-stated now: drop coin-days in the top |7-d funding| decile of the top-30 universe, F0 'apply', 200 masks, dSR > 0 >= 95th pct and per year.
Change my mind: a clear dose (price loss/funding ratio > 1 in the top decile, < 1 elsewhere) in every year -> c is motivated; flat -> carry's price cost is uniform, no filter.

## FLD flow@bn signal decay (think-through 19:3x UTC 11-27, before any run)
Source: BNB b (flow's price P&L ~0 in 2025-26, +19..+38 %/unit-yr in 2021-24). No chat records. Signal: 3-d taker imbalance (2 x taker buy - volume)/volume, cross-sectional rank, top-30.
Mechanism claimed: split metaorders keep coming (continuation). Decay candidates: (i) more market makers/algos read the same public taker split (crowded), (ii) the edge moved to faster
 horizons (priced within the day), (iii) regime: 2025-26 alt bear + chop. Unstated: IC is the pre-cost test; long vs short leg; by liquidity tercile (the thin third may still work).
Change my mind: IC (next-day, market-relative) ~0 in 2025 AND 2026 in all terciles -> flag for the §4 retirement check; IC alive but P&L ~0 -> costs/sizing; one year only -> regime.
FLD a/b/c done (is3_fld.py, fld_ab.json): flow IC1 2021 .034 (t 2.4), then .005/-.009/.015/-.019/.010; liquid tercile +.04-.05 in 2022/24 only; longs paid in bull years only.
 Recent return = funding. Flagged for §4 live check. 3-d IC sign oddity in 2023 unresolved (not used). CLOSED OPEN.

## VRT venue routing of directional legs by funding (think-through 19:3x UTC 11-27, before any run)
Source: fspread_hold (HL short leg on 95 % of pair-days: HL longs pay more), TSH (HL tsmom longs pay 3.5-12 %/yr). Mechanism: HL retail is net long and pays more funding than Binance;
 a directional book that is long a coin can hold that long on Binance and its shorts on HL (where shorts receive more): same price exposure, better carry. Who pays: HL's crowded longs.
Unstated: (1) only coins on both venues can be routed (coverage); (2) the choice must be made from trailing funding (known), scored on realised; (3) costs: BN fee 5 vs HL 4.5 bp, basis at
 trade, extra trades when the best venue flips, and two accounts with no netting (margin, per-account drawdowns as in X1C); (4) the price series differ slightly (basis drift) - ignore in a,
 measure in b. Change my mind: routed saving >= 1 %/yr net of b's costs on the HL main book -> design backlog item.
VRT a/b/c done (is3_vrt.py, vrt_a.json): HL book funding -12.3 %/yr on HL vs -7.8 all-BN vs -3.5 routed; net of venue-switch costs +14 / +7.2 / +1.6 / -1.6 %/yr (2023..26): the gap closed. CLOSED OPEN.
CRB c done (crb_c.json, unit is3-crbc): dropping the top |funding| decile: carry dSR -.38 (1st pct of random), carry_trend -.15 (16th): FAIL. CLOSED OPEN: the extreme decile is the edge.

## LSB new-listing shorts on Binance (think-through 19:3x UTC 11-27, before any run)
Source: HLI (HL listings dried up in 2026), LVH/HLU1 (BN-only names). Mechanism: post-listing supply overhang (airdrops, unlocks, early holders selling to late longs), same as HL's listing_short.
Binance lists far more perps; if the decay holds there in 2025-26 it can replace HL's dry flow inside main_bn. Unstated: (1) BN-only listings are thinner and squeeze-prone (LVH: BN-only shorts
 pay -92 %/yr funding in lowvol) -> split by HL-listed at the time; (2) event P&L excludes funding here (bnall has funding; add it: shorts in new listings often pay); (3) equal-weight events,
 clustered by listing month. Change my mind: 2025-26 BN events mean > 0 AND median > 0 with funding -> backlog WF item.
LSB a/b/c done (is3_lsb.py, lsb_ab.json): BN listings 5.7/month in 2026 (HL ~1); event median +22..+41 % every year, mean squeezed (2021 -79 %, 2025 +4, 2026 +9 %); HL-listed vs BN-only no stable sign.
 Backlog LSB2 (research WF in main_bn). CLOSED OPEN.

## FLQ flow@bn on the most liquid names (think-through 19:3x UTC 11-27, before any run)
Source: FLD (liquid-tercile IC +.04/+.05 in 2022/2024, thin ~0). Mechanism: metaorder splitting by funds/algos is visible in the liquid majors' taker flow; in thin names taker flow is
 retail noise and pumps. Unstated: top-10 by volume ~ BTC/ETH/SOL/XRP/DOGE...: fewer names = more concentrated book (vol target scales up), beta hedge matters more; I saw the tercile ICs of
 2024-26 in FLD, so b is a weak confirm (stated). PRE-STATED (a): top_n 10 vs 30, lookback 3, cap .05, bnall 2021-23: PASS = SR higher pooled AND in 2 of 3 years.
FLQ a done (flq_a.json): flow top-10 SR .67 vs top-30 1.58 on 2021-23: FAIL. b skipped. CLOSED OPEN.

## LSP listing_short as a book on bnall (think-through 19:3x UTC 11-27, before any run)
Source: LSB; the 11-09 note (bnall WF 1.08 was BTC-leg P&L, corr BTC .63; SR .44 at band .005). Mechanism as LSB; the book shorts every qualifying listing equally and hedges with long BTC
 (beta 1 assumed for coins younger than 20 d). If new listings' beta > 1 and they fall with the market, the hedge leg's P&L carries the book in bull years: an artifact, not the decay.
Unstated: the split shorts vs BTC leg is the test; the squeeze tail (LSB: means crushed by a minority) shows as worst days; the 1/3-risk add to main_bn is descriptive only.
Change my mind: 2024-26 shorts-leg P&L > 0 every year net of costs and corr BTC < .3 -> LSB2 go; else LSB2 note why not.
LSP a/b/c done (is3_lsp.py, lsp_abc.json): bnall listing_short book SR .18 (2025 -.40, 2026 -.33); alt shorts lose in 2024-25, the BTC leg made 2023-24; squeezes (MARSCOIN) set the tail.
 LSB2 needs a squeeze control first. CLOSED OPEN.

## SQZ what predicts a listing short's squeeze (think-through 19:4x UTC 11-27, before any run)
Source: LSB/LSP. Who squeezes a new listing: a thin float (most supply locked), crowded shorts (perp opened before spot liquidity), and a narrative bid; market makers lift the book.
What should precede it: rising volume into a rising price (fuel), a price far above its post-listing low (momentum already turned), shorts paying (negative funding, but LSF: funding as an exit
 = random), young age (float thinnest), small dollar volume rank. State -> distribution: the next-7-d left tail of the short's P&L by feature quintile, dose curves, by explore year.
Unstated: equal-weight daily book: an exit on a squeeze signal costs the round trip and the decay of names that do NOT squeeze; judge in b against random masks.
Change my mind: a feature with a monotone left-tail dose (top quintile P(loss > 20 %) >= 2x bottom) in all 3 explore years -> b. Else SQZ OPEN, LSB2 stays parked.
SQZ a done (sqz_a.json): off_low (how far above its post-listing low) top quintile = the squeeze state: P(loss>20 %/7 d) 17 % vs 7-10 %, every explore year (1.7-1.9x the bottom, 2-2.5x the rest).
 Deviation, stated: my 2x-vs-bottom bar is missed narrowly (U-shape); I run b anyway because b was designed to take the best feature from a, and F0 + the held-out 2024-26/HL runs are the line.
PRE-STATED (b): block (exit / no entry) listing_short shorts whose off_low >= 0.433 (explore pooled 80th pct), F0 'apply', bnall explore 2021-23, 200 random masks;
 PASS = dSR > 0 at >= 95th pct AND dSR > 0 in 2021, 2022, 2023.
SQZ b done (sqz_b.json, unit is3-sqzb): off_low block dSR +.32 vs random median +.25 (60th pct): FAIL; c skipped. CLOSED OPEN; LSB2 parked.

## FRG funding regime vs the carry-earning books (think-through 19:4x UTC 11-27, before any run)
Source: BNB, CRB, VRT. Mechanism: carry income needs crowding (leveraged longs paying, or crowded shorts paying); crowding is a market regime (bull euphoria, meme seasons) that persists
 for months. If the state persists and the books' income follows it, their forward expectation should be quoted per regime, and a dry regime explains a weak live month without a bug.
Unstated: monthly sampling = few independent points (~70 months bnall, ~42 pair): descriptive, rank correlations, no rule. The state must be known at the month start.
Change my mind: rank corr(state_m, carry income_{m+1}) > .5 and AR(1) of income > .5 -> regime table goes to STATUS; else note.
FRG a/b/c done (is3_frg.py, frg_ab.json): next-month funding income vs market median funding: BN carry books rho -.42..-.48 (crowded shorts pay in low regimes), pair +.61; AR(1) .5-.66;
 BN net not forecastable. State now low (24th pct) -> pair book income ~.36 %/month. CLOSED OPEN.

## KSA per-venue-account drawdowns of main@pair (think-through 19:4x UTC 11-27, before any run)
Source: KSW, X1C a. The pair book is hedged across two accounts that cannot net: a rally loses on the HL short leg's account while the BN long leg's account gains; the losing account can hit
 margin trouble although the book is flat. The book-level -25 % kill never sees it. Unstated: account equity = half the capital each (alloc .5 -> 1.0x leverage per account); real transfers
 between venues take time and cost; the guard must not fire on ordinary alt rallies too often. Change my mind: P(account DD <= -50 % in 2 y) >= 5 % without transfers -> a transfer rule is
 required before funding main@pair; write it to KS1.
KSA a/b/c done (is3_ksa.py, ksa_abc.json): pair accounts without transfers: P(-50 % in 2 y) >= 90 %, historical path liquidates one; 'rebalance at 70 %' -> worst -29 %, 14 transfers/yr. KS1 updated. CLOSED OPEN.

## CRS carry's extreme-decile longs (think-through 19:4x UTC 11-27, before any run)
Source: CRB. These are coins whose shorts pay 1-2 %/day: a crowded short in a falling coin. The carry long collects the funding; it loses when the coin keeps falling (shorts were right:
 unlock/insider selling) and wins when shorts capitulate (squeeze). Unstated: the losers should be coins still in a fresh downtrend (close near the 30-d low, falling volume = no buyers),
 the winners those already off the lows with rising volume. Change my mind: a feature whose worst quintile has a next-7-d mean below -5 % with a dose in every explore year -> b.
CRS a done (crs_a.json): only 'funding fading' (f3/f7 bottom quintile) is same-signed every year (-5.2/-2.8/-2.6 % next 7 d vs ~+1 % others); my -5 % bar missed. Deviation, stated: b runs once
 anyway (as in SQZ) because b takes the best feature from a by design; F0 + 2024-26 are the line.
PRE-STATED (b): block carry LONGS in the top |7-d funding| decile when f3/f7 < 0.443 (explore 20th pct), side +1, carry on bnall explore 2021-23, 200 random masks (circular shifts of the
 mask per coin: on-share kept, but shifted blocks may land outside the decile: a weaker null, stated). PASS = dSR > 0 at >= 95th pct AND dSR > 0 in 2021, 2022, 2023.
CRS b done (crs_b.json, unit is3-crsb): dSR -.01, 36th pct: FAIL; c skipped. CLOSED OPEN.

## TFF tsmom HL longs vs extreme HL funding (think-through 19:5x UTC 11-27, before any run)
Source: TSH, VRT. A trend long in a coin whose HL longs pay heavy funding is a crowded long: either the trend continues (funding is the price of momentum) or the crowd is the top.
Unstated: funding paid is certain, the price edge is not; at the top quintile funding can be 50-100 %/yr. hlu_explore only (2023-04..2024-12); HL 2025-26 kept for c.
Change my mind: top-quintile longs' next-day price P&L < their funding paid in both explore years, with a dose -> b.
TFF a done (tff_a.json): tsmom HL top-funding longs: price +87/+33 vs funding -25/-24 bp/unit-day (2023/24): trend pays for funding; b/c skipped. CLOSED OPEN.

## PAC live per-venue account equity of the pair books (think-through 19:5x UTC 11-27, before any run)
Source: KSA. The paper ledger keeps one equity per pair book; real money would sit in two accounts. Reconstruct each venue's P&L from fills (positions), funding rows (per leg) and daily
 closes from the live caches (venue_pair.live_panel: the same closes the book trades on). Note already: funding per venue since 11-12 = HL legs -$39, BN legs +$59 (both venues' funding
 negative in Nov: the BN longs receive, the HL shorts pay; FRG: low-median regime). Change my mind: live divergence outside KSA's 15-d distribution -> a model error to fix first.
PAC a/b/c done (is3_pac.py, pac_a.json): live shadow pair accounts +28 / -27 % by 11-24 (book +$9); at alloc .5 ~ +/-14 % = 12.5th pct of KSA's 13-d range; 70 % transfer due by 11-20. KS1 spec. CLOSED OPEN.

## OVL the three main books together (think-through 19:5x UTC 11-27, before any run)
Source: KSW, BNB, BNH. If the owner funds more than one home, what matters is whether the books share bets: main (HL listing shorts + lowvol + tsmom) and main_bn (flow + carry/xsmom) both
 short weak alts and both hold carry; main@pair is hedged. Unstated: backtest correlations understate crash co-movement (look at the worst days); coin overlap by same-sign gross.
Change my mind: corr(main, main_bn) > .5 or most of the worst days shared -> say in STATUS that two homes are one bet.
OVL a/b/c done (is3_ovl.py, ovl_ab.json): main / main_bn / pair corr .05-.08, worst days not shared; main+main_bn SR 2.07 mdd -10.5 % vs alone 1.28/-19.8, 1.74/-13.4. CLOSED OPEN.

## HLD HL listing drought vs a data blind spot (think-through 19:5x UTC 11-27, before any run)
Source: HLI. Our HL universe comes from metaAndAssetCtxs = the main perp dex. If HL's new listings in 2026 went to builder-deployed dexes (HIP-3) or the main dex listed many coins that
 never reached $1M, listing_short is blind or starved, not facing a dry market. (a) uses only files on disk; (b) needs a few public info calls. Change my mind: main-dex listings per month
 fell like the qualifying ones -> drought on the main dex; builder dexes with >= $1M coins -> blind spot.
HLD a done (inline, hld_a.json): no coverage gap (179 main-dex coins all have files); main-dex listings 54/59/51/8 per year (2026: 8, 7 reached $1M): the main-dex drought is real. b (builder dexes) next session.
HLD b plan: public HL info endpoint only, kripto.hl.HL (min_interval 3 s): perpDexs once, then metaAndAssetCtxs per builder dex (dex=<name>); count perps and 24-h notional volume. Read-only, no keys.
HLD b/c done (is3_hld.py, hld_b.json, 11 public info calls): builder dexes = stock/index perps (xyz $4.1B/day), no new crypto tokens: the HL crypto listing drought is real. CLOSED OPEN.

## XST blend_nested@bn 3rd slot: xsmom vs tsmom (think-through 19:5x UTC 11-27, before any run)
Source: BNB c (pool 11-21: xsmom 1.25, tsmom 1.17), TSH (tsmom convex on HL). Descriptive only: the nested rule decides the refit. Question: what changes in main_bn's risk if the rule swaps
 them: tsmom (directional trend, convex) vs xsmom (market-neutral momentum). Change my mind: n/a (verdict note only).
XST a/b/c done (is3_xst.py, xst_ab.json): tsmom convex (BTC worst weeks +2.4 %/wk) and hedges carry's worst days; blend with tsmom SR 1.40 / mdd -19.9 vs xsmom 1.28 / -16.7 (2023-26). CLOSED OPEN.
FLB a/b/c done (flb_ab.json): known-answer tests pass; 2023 3-d IC vs daily lags = rank-of-sum vs sum-of-ranks (fat tail), not a bug. CLOSED OPEN.

## LSW listing shorts weighted by inverse own-days vol (think-through 00:5x UTC 11-28, before any run)
Source: LSP (bnall equal-weight book SR .18; squeezes like MARSCOIN set the tail), SQZ (blocking the squeeze state = random), LSV (zero-filled vol under-estimates young coins 4x). No chat records.
Mechanism: equal weights give a 300 %-vol micro-float the same short as a 90 %-vol name; the squeeze tail is a few very volatile names. Inverse-vol puts the risk budget where the decay is
 steadier. Unstated: (1) the decay may live IN the volatile names (high vol = overhang being sold), then inverse-vol cuts the edge with the tail; (2) vol is only known after 3 own returns:
 before that the name keeps relative weight 1 (stated choice); (3) the weighting changes the mix, the book-level vol target rescales gross, so the test is SR, not size.
Placebo: the same relative weights permuted across the day's eligible names (keeps concentration, breaks the vol link). Explore bnall 2021-23; HL is the held-out venue.
Change my mind: SR above equal weight in 2021, 2022 and 2023 AND >= 95th pct of 200 permutations -> b.
LSW a done (is3_lsw.py, lsw_a.json): replication of listing_short exact; inverse own-days vol SR .24 vs .18, years +.23/+.26/-.25, 73rd pct of 200 permutations; worst-10 mean -4.56 vs -4.67 %:
 FAIL. The tail is not in the already-volatile names. b skipped; c: listing shorts stay HL-only (LSB2 parked; 3 squeeze controls failed: SQZ, LSV, LSW). CLOSED OPEN.

## PRB partial rebalancing of the HL main book (think-through 01:0x UTC 11-28, before any run)
Source: mandate (costs bind on HL), T1c (EMA of the tsmom signal: DEAD). Mechanism (Garleanu-Pedersen aim portfolio): when the target moves a little every day (vol-target rescaling, tsmom
 drift, beta-hedge noise), trading the full gap pays the spread on noise that later reverses; trading a fraction lam of the gap cuts turnover more than it cuts signal, IF the signal's
 alpha decays slower than the noise (T9B: daily books' alpha accrues over 24-48 h, so a 1-2 day lag costs little). Unstated: (1) listing_short entries are events: lam<1 delays the entry
 and the early decay (LS1: days 1-14 carry the most) may be lost: that is the risk to watch per leg; (2) the band .005 already filters tiny trades: the gain must beat the band, not zero;
 (3) a smaller turnover lowers the realised exposure a bit: compare net SR, not return. Explore HL 2023-03..2024-12; 2025-26 held out. Live book = blend(listing_short, lowvol, tsmom).
Change my mind: a lam<1 with net SR >= lam=1 in 2023 AND 2024 -> b.
PRB a done (is3_prb.py, prb_a.json): lam .33 net SR .87/.93 vs .87/.75 (2023/24), costs 11.1 -> 5.7 %/yr, pre-cost SR 1.21 -> 1.11. PRE-STATED (b): lam .33, ONE run HL 2025-26; PASS = net SR >= lam 1 pooled AND 2025.
PRB b PASS (prb_b.json): HL 2025-26 lam .33 net 1.94 vs 1.86, costs 7.0 -> 3.4 %/yr. c (prb_c/prb_d.json): bnall fast books lose (blend_bn 2.10 -> 1.84, flow 1.60 -> 1.34); HL band .01: better 2024-26,
 worse 2023; band .05 ($200) worse every year. Mechanism holds: pays only where alpha decays slower than target noise (HL legs) and the band is small. CLOSED OPEN -> backlog PRB2 (shadow variant).

## HBL HL listing_short: shorts vs BTC hedge leg, young-coin beta (think-through 01:0x UTC 11-28, before any run)
Source: LSP (on bnall the 2023-24 profit was the BTC hedge leg), BNH/HLI (listing_short = the HL main book's edge). beta_to needs 20 d, so coins younger than 20 d are hedged at beta 1.
Mechanism: the HL main book's claim is 'new listings decay vs BTC'. If the book's P&L is mostly the long BTC leg in up years, it is a disguised long-BTC bet and its SR is regime luck.
Unstated: (1) new listings may have beta > 1 (thin, retail) -> hedge too small -> the short legs lose in rallies and the book is net short the market; or beta < 1 (idiosyncratic) -> the
 BTC leg is over-sized and long the market; (2) the leg split must include funding per leg (HL shorts in new listings often RECEIVE funding). Change my mind: BTC leg >= half the net in
 any year -> say in findings/STATUS that the HL edge is partly beta; pooled young beta outside 1 +/- .3 -> c.
HBL a/b done (is3_hbl.py, hbl_a/b.json): leg split exact; corr BTC ~0, 2024 profit = alts lagging a BTC rally. Young-coin beta 1.3-1.46 both venues (down 1.5-1.6). PRE-STATED (c): young beta 1.35 frozen, ONE run HL 2025-26, PASS = |corr| not larger AND SR >= beta-1 SR - .10, both books.
HBL c PASS (hbl_c.json): young beta 1.35, HL 2025-26: listing_short 1.71 vs 1.77 SR, corr +.01 vs -.04; blend 1.79 vs 1.86, corr -.07 vs -.09. Small; the beta-1 SR edge = net-short beta in a falling
 BTC year. CLOSED OPEN -> backlog HBL2 (apply as a risk fix in a research session, not as an SR gain). Note: LSP's 'BTC leg made 2023-24' is a leg-accounting artifact of a hedged spread.

## PRL per-leg costs of the HL main book, partial rebalancing on the slow legs only (think-through 01:0x UTC 11-28, before any run)
Source: PRB (whole-book lam .33: costs halved, pre-cost SR -0.1 on explore). Unstated in PRB: the listing leg is an event book (enter at day 2, exit at day 61): lam .33 delays both, and the
 decay is front-loaded (LS1 b); tsmom/lowvol targets drift slowly, so their trades are mostly noise. Who pays the noise: our spread. Per-leg contributions = the book's final weights split by
 each leg's share before the vol-target scalar (exact if scheduled() is a row scalar: checked in code). Standalone leg costs ignore netting between legs: report the netting share.
Change my mind: slow-legs-only lam .33 net SR >= whole-book lam .33 in 2023 AND 2024 -> c.
PRL a done (is3_prl.py, prl_a.json): split exact; tsmom pays 3-8 %/yr of costs (turnover 35-64x), listing 2-4, lowvol 1-4; book 5-14 %/yr.
PRL b PASS (prl_b.json): slow-legs lam .33 .95/1.01 vs whole .87/.93 vs lam1 .87/.75; pre-cost 1.25. PRE-STATED (c): ONE run HL 2025-26, PASS = slow33 >= whole33 and >= lam1 pooled, >= lam1 each year.
PRL c PASS (prl_c.json): HL 2025-26 slow33 2.10 vs whole33 1.94 vs lam1 1.86, costs 7.0 -> 4.0 %/yr. Stress (prl_s.json): causality 0; band .01 >= lam1 3/4 (2023 tie .84/.86); 2x cost
 better every year; $200 band .05 worse 3/4. CLOSED OPEN (best of the session) -> backlog PRB2 rewritten: engine option per leg, $1,000 HL main shadow variant.

## HBM young-coin beta in the Binance main books (think-through 01:0x UTC 11-28, before any run)
Source: HBL (young beta 1.3-1.46; hedge_beta fills a NaN 20-d beta with 1.0). The BN books (flow, carry, carry_trend, xsmom) pick from a liquid universe (min_days 30 in universe()), so
 most held coins have a beta; the fill matters only for names < 20 d in a book that does not require history (flow? carry?). Unstated: if the share is tiny the question is closed.
Cached panel only (data/is3/fc1c_bnall_1d.pkl, ends 11-21; nightly window). Change my mind: >= 3 % of gross in NaN-beta coins in some year -> b.
HBM a done (is3_hbm.py, hbm_a.json): BN books' gross in NaN-beta coins <= 0.2 %: irrelevant; HBL2 = listing_short only. CLOSED OPEN.

## PRN per-leg partial rebalancing on the Binance blend (think-through 01:1x UTC 11-28, before any run)
Source: PRL, PRB c. Whole-book lam .33 hurt the BN blend (pre-cost loss > cost saving) because some legs are fast. Carry (funding persists for weeks) and carry_trend should be slow; xsmom
 (lb 28, every 3 d tranches) medium. Unstated: carry's target jumps when funding flips sign (a real signal change, not noise): partial rebalancing delays that exit while paying funding.
Cached bnall only (nightly window). Leg chosen by turnover rule from a before b runs. Change my mind: b net SR >= lam 1 in 2021, 2022, 2023 -> c.
PRN a done (prn_a.json): BN turnover ct 42-74x, carry 36-51, xsmom 18-33; rule picks carry_trend only for b (stated before b).
PRN b FAIL (prn_b.json): ct lam .33 4.09/.01/1.98 vs 4.19/-.13/2.02; cost saving = signal loss. CLOSED OPEN: PRL is HL-specific (tsmom/lowvol turnover is noise there).

## TSB per-leg no-trade band vs partial rebalancing (think-through 01:1x UTC 11-28, before any run)
Source: PRL. A band (trade the full gap only when it exceeds 0.02 per coin) is the textbook alternative to lam: it ignores small noise entirely but jumps fully on big changes. Engine-wise both
 need the slow legs' held weights per coin. Unstated: a 0.02 band at leg level (the legs are ~1/3 of the book) is ~6 % of a leg's typical coin weight; it may freeze small coins' weights for
 weeks (staleness). Not tuning: one pre-stated band; if it loses to lam, lam is the form to build.
TSB a FAIL (tsb_a.json): band .02 1.00/.92 vs slow33 .95/1.01; sub-$10 trades 11 % vs 56 %. c: build lam, band = fallback. CLOSED OPEN.

## VTS vol-target scalar hysteresis (think-through 01:2x UTC 11-28, before any run)
Source: PRB/PRL. vol_target() rescales every row so ex-ante vol = target; the trailing 60-d covariance moves every day, so every position is resized every day by a few %: pure noise
 trades (the scalar carries no alpha). Hysteresis: keep the held scalar until the new one differs by > 10 %. Applied to EVERY vol_target call (component legs and the outer blend), as an
 engine change would. Unstated: (1) after a vol shock the scalar must fall fast (risk): a 10 % threshold still reacts within a day to big moves; (2) the band .005 already skips some of
 these trades; (3) a = the turnover the rule removes (descriptive), b = SR/vol verdict. Change my mind: net SR >= daily in every explore year for HL blend, BN blend, flow, and realised vol
 within 10 % -> c.
VTS a/b FAIL (is3_vts.py, vts_a.json): scalar hysteresis 10 % removes no turnover (+1 %) in HL blend, BN blend, flow; SR diffs noise. CLOSED OPEN.

## SML the $200 HL account (think-through 01:3x UTC 11-28, before any run)
Source: owner 11-10 ($200 twins), PRB/PRL d. At $200 the $10 minimum order = band .05: a coin's weight changes only in 5 % steps. Legs with many small positions (lowvol, tsmom across
 ~20 coins at 1/3 of the book) are mostly frozen or skipped; listing_short (few names, larger weights) survives. Unstated: a frozen leg is not neutral: it holds stale positions (old trend,
 old low-vol picks). Leg contributions = the book's own (is3_prl.legs), each run alone at band .05 (ignores netting, stated). Change my mind: a leg <= 0 net at .05 in 2023 and 2024 -> b.
SML a done (sml_a.json): at band .05 98-100 % of leg changes are skipped (frozen legs, lottery-like years: listing 2025 .02 vs 2.17); lowvol <= 0 in 2023/24 -> b: blend(listing_short, tsmom) at .05.
SML b FAIL (sml_b.json): 2-leg 1.83/1.10 vs 3-leg 1.91/1.00 at .05. CLOSED OPEN: $200 = frozen legs, path lottery; live small: twin is the only evidence.

## PRD dose-response of PRL (think-through 01:4x UTC 11-28, before any run)
Source: PRL. lam .33 came from a 3-point grid; a real noise-filter effect should be a plateau (any lam .25-.5 helps; very small lam starts to lose signal); a knife-edge means luck.
 Descriptive only: no new choice; the held-out years are shown but were already seen (PRB b, PRL c). Change my mind: every lam in [.25,.5] >= lam 1 in all four years -> robust.
PRD a/b/c done (is3_prd.py, prd_ab.json): lam .15-.75 all >= lam1 in 2023-26 (plateau); tsmom-only = cost, lowvol-only = pre-cost gain; both best. CLOSED OPEN; PRB2 lam .33 both legs.

## TSN tsmom HL turnover sources (think-through 01:5x UTC 11-28, before any run)
Source: PRL a (tsmom 35-64x/yr), T1c (EMA signal smoothing halved turnover but HL SR 1.11 -> .34: DEAD) vs PRD (partial rebalancing of tsmom costs no SR). Turnover sources: the trend signal
 (4 lookbacks, tanh: slow), per-coin vol (ann_vol, daily), the gross normalisation (sum |raw| = 1: one coin's change resizes all), and universe churn (top 20 by volume: names enter/exit
 at full size). Unstated: universe churn trades whole positions on rank noise (rank 20 <-> 21): a likely big part. Monthly freezes are causal (first value of the month, held).
 d first-suspects a bug/data difference in T1c vs PRL before any conclusion.
TSN a/d done (is3_tsn.py, tsn_ad.json): tsmom turnover = signal drift (monthly hold -73 %), not vol/universe. T1c fails to replicate: EMA3 .59, lam .21 .75 vs base .46 (2023-26). PRE-STATED (b): book = listing full + lowvol lam .33 + tsmom with monthly-held signal (lam 1), HL explore 2023-24 vs PRL slow33; PASS = >= in both years.
TSN b FAIL (tsn_b.json): monthly signal 1.49/.89 vs slow33 .95/1.01. CLOSED OPEN; T1c smoothing relabelled OPEN (no replication on 2023-26).

## CPB per-coin band .02 on the fast Binance books (think-through 02:0x UTC 11-28, before any run)
Source: PRB c/PRN (lam delays real signal changes on fast books: cost saving = signal loss), TSB (band form). A band ignores small changes (noise: flow's 3-d imbalance wobbles, vol rescaling)
 but executes big ones at once (sign flips, new extremes), so it should lose less signal than lam on fast books. Unstated: a held weight that never crosses the band goes stale (positions
 kept on old signals); flow has ~30 names at cap .05 = weights ~.03-.05: a .02 band is ~half a position, i.e. coarse. One pre-stated band, no grid. Cached bnall (window 01:15-03:30).
CPB a FAIL (is3_cpb.py, cpb_a.json): band .02 flow 1.28 vs 1.60, blend_bn 1.23 vs 2.10 (2021 halves). CLOSED OPEN: BN fast books' turnover is signal under both filters.

## CMB PRB2 + HBL2 together; live min-order rule (think-through 02:1x UTC 11-28, before any run)
Source: PRL/PRD, HBL, TSB c. Two changes to one book can interact (the beta fix moves the BTC leg, which is in no slow leg: lam does not touch it here since the BTC hedge sits inside
 listing_short's contribution). The bigger risk is execution: live skips orders < $10, so lam's many small steps may never execute; the rule 'trade when the gap clears $10' turns lam into
 a hybrid lam+band. Unstated: the gap is measured against the HELD weight (which drifts with price), so stale small gaps eventually trade. All years already seen: descriptive + a spec rule.
CMB a/b/c/d done (is3_cmb*.py, cmb_ab/d.json): PRL + HBL additive. Min-order $10 at $1,000: lam1 .85/.65/2.02/1.59, slow33 .78/.98/2.17/1.81, band02 .99/.94/1.66/1.57.
 Spec rule met 2/4 -> written fallback (band) is not better live (d): DEVIATION stated, spec stays lam .33 + $10 accumulation. CLOSED OPEN.

## PRX frozen replication of PRL on Binance (think-through 02:2x UTC 11-28, before any run)
Source: PRL/PRD. If slow-leg partial rebalancing works because tsmom/lowvol targets carry daily noise, the same legs on another venue's instruments should show it; if it is an HL-panel
 artifact (few coins, 2023-26 regime), it will not. Frozen: lam .33, the same legs, band .005, no change. bnall universe differs (tsmom top 20 by volume, listing events many more).
 PASS (a) = net SR >= lam 1 in 2 of 3 years and pooled 2021-23; b = 2024-26 the same way; c = where it lives.
PRX a/b/c done (is3_prx.py, prx_abc.json): frozen PRL on bnall 3-leg book: 2021-23 .73 vs .81 (FAIL), 2024-26 .52 vs .43; bnall tsmom lam .33 = lam 1 (1.29/1.30). Not a general law: HL-specific
 (HL tsmom noisier). PRB2 prior lowered to medium; forward days decide. CLOSED OPEN.

## HTN why HL tsmom turns over ~100x (think-through 02:3x UTC 11-28, before any run)
Source: PRX, TSN. tsmom weight = tanh trend / ann_vol, normalised to gross 1 over the top-20-by-volume universe. On HL the top 20 reach thin, high-vol coins whose trend signal and vol both
 swing daily, and the gross normalisation spreads each coin's swing over all weights. bnall's top 20 are deep majors. Unstated: if turnover concentrates in the high-vol tercile, PRB2's gain
 is a property of the coin set (lasting while HL lists thin coins), else a panel accident. a is descriptive; b uses HL listing dates on bnall.
HTN a/c done (is3_htn.py, htn_a.json): tsmom turnover HL 105x = bnall 100x; cost per unit HL 22/11/8/10 bp vs BN 6 bp. PRL's gain = cost-per-turnover effect (explains PRX). CLOSED OPEN.
HTN d (htn_d.json, after close): at the fills-fitted cost (slip x .5, L3S) slow33 >= lam1 every year 1.09/1.06/2.41/1.81 vs 1.09/.85/2.23/1.56: PRL's gain survives realistic costs.

## HLF HL main book funding drag (think-through 02:4x UTC 11-28, before any run)
Source: PRB/PRL summaries (book funding -5..-16 %/yr), HBL a. HL funding is mostly positive (longs pay) in up markets: every long leg pays (BTC hedge, tsmom longs, lowvol longs), shorts
 receive except crowded-short listings. Unstated: the BTC hedge pays funding for no alpha (pure risk control): a cheaper hedge instrument would be a free saving if it tracks.
 a = per-leg table (longs vs shorts), price P&L next to it.
HLF a done (is3_hlf.py, hlf_a.json): BTC hedge longs pay 1.6-8.9 %/yr funding (largest steady payer), listing alt shorts pay 3-5 % in 3 of 4 years. b (cheaper hedge: ETH / top-5 basket) next session.
HLF b/c (hlf_b.json): ETH hedge no cheaper (-5.8/-6.9 vs -4.0/-7.3 %), SR worse. CLOSED OPEN: funding drag is market-wide on one venue.

## HLE HL listing events: fresh tokens vs coins already on Binance (think-through 02:5x UTC 11-28, before any run)
Source: HLI/HLD, LSB. The decay story (airdrop/unlock overhang, early holders selling to late retail) is about FRESH tokens. A coin that has traded on Binance for a year and then lists on HL
 has no new float; its HL listing is a venue event: maybe a small HL premium (HL longs arrive) that arbitrage closes in days. Unstated: established coins' 'decay' would be beta + funding;
 fresh tokens should carry the edge. If so, the 2026 drought removed the edge itself, not just events. Event P&L: short coin, long BTC (beta 1), d2..d61 closes, HL funding on the short.
HLE a/b/c done (is3_hle.py, hle_ab.json): HL events by Binance history: >= 60 d n 42 mean +1 % (t .13; 2023 -13 %), < 60 d n 35 +29 % (t 2.4), fresh n 88 +25 % (t 2.1). The edge = new float;
 2026 drought removed it. Filter idea -> backlog HLE2 (held-out on bnall needed). CLOSED OPEN.

## HLX held-out for HLE on Binance (think-through 03:0x UTC 11-28, before any run)
Source: HLE. Same mechanism in mirror: a coin that traded on HL >= 60 d before its Binance perp listing has no new float at the Binance event. Frozen split and windows as HLE; only 2023-04+
 Binance listings can have HL history (HL data starts 2023). Unstated: Binance often lists coins that have spot/other-venue history too: 'not established on HL' is a noisy proxy for new float.
PASS pre-stated in the queue (established mean & median < others, established median <= +5 %).
HLX a/b/c done (is3_hlx*.py, hlx_ab/bh.json): bnall listings of coins on HL >= 60 d: n 10, buy-hold median -5 % win .30 vs new +36 % win .77; replicates HLE (both measures). Measure note: the
 daily-rebalanced short carries vol drag (~19 % over 60 d): LSB's medians are buy-hold. HLE2 -> one pre-registered WF. CLOSED OPEN.

## HLB book-level effect of the HLE skip rule (think-through 03:1x UTC 11-28, before any run)
Source: HLE/HLX. Event means can mislead at book level: the book equal-weights the names held each day, vol-targets and beta-hedges; dropping established coins concentrates the book in
 fewer, more volatile fresh names (squeeze tail up) and adds idle days. Mask = coin-days where the coin had >= 60 d of trading on the other venue at its listing date (fixed per event).
 F0 'apply' semantics (blocked shorts -> 0), weights renormalise? No: listing_short equal-weights by n eligible; implemented by removing the coins from eligibility before weighting (closer to
 what the rule would be live). bnall = held-out venue for the rule (book level).
HLB a/b/c done (is3_hlb.py, hlb_abc.json): skip rule at book level: HL listing_short 1.21 vs 1.37 pooled, blend worse 3/4, bnall no effect (10 coins). Event contrast != book gain. HLE2 downgraded. CLOSED OPEN.

## HFR HL main book funding drag vs regime (think-through 03:2x UTC 11-28, before any run)
Source: HLF, FRG. The book is net long-ish in funding terms (BTC hedges, trend longs) and pays when HL longs are crowded (bull months). If the drag persists month to month and follows the
 market's funding level, the forward expectation should be quoted per regime. Monthly = ~44 points: descriptive. Change my mind: AR(1) > .4 and rank corr > .4 -> regime note in STATUS.
HFR a/b/c done (is3_hfr.py, hfr_abc.json): drag -0.95 %/month, AR(1) .19; rank corr(state, next drag) +.47: low funding -> more drag (book net short alts). Now 23rd pct -> ~-1.4 %/month. CLOSED OPEN.

## LVS HL lowvol leg by side (think-through 02:5x UTC 11-28 real clock, before any run)
Source: HLF a (lowvol short alts price -16/-33/+28/+14 %/yr; long alts +14/+17/-1/-8; BTC hedge long +8/+20/-1/-7), LV2 (FRAGILE, one year deep). lowvol = rank(-vol) demeaned
 over top 30, beta-hedged to BTC: the short side holds high-beta names, so the hedge is a BTC LONG; the leg is long (low-vol alts + BTC) vs short high-vol alts. Unstated: it is a
 beta-mismatch bet in disguise: if the hedge beta (trailing) underestimates high-vol names' up-market beta, it loses in bull years (2024) and wins in alt bear years (2025-26).
 Then 'lowvol on HL' = short high-vol alts' idiosyncratic decay (listing overhang, same source as listing_short) and the yearly sign follows alt-season. a = per side price/funding/costs
 + corr of each side's daily P&L to BTC and to the alt index; c judges. b: are the losing shorts the coins already falling (crowded shorts squeeze) -> trailing 30-d return quintiles.
LVS a done (is3_lvs.py, lvs_a.json): each side is a market bet (corr to BTC +.73..+.93 long, -.63..-.71 short); they cancel to leg corr ~0. Price spread +6/+5/+26/-1 %/yr, long side pays funding
 1-8 %; leg net -1/0/+22/-7. 2025's whole return = the high-vol short side (+28 %). So: a small positive spread most years, one big year from high-vol alts collapsing.
LVS b done (lvs_b.json): short candidates by trailing-30-d quintile (2023-24): mean fwd +3/+9/+15/+12/+8 %, medians all -1..-5 %: no dose, inverted-U; already-falling names keep falling. The leg's
 losses are right-tail squeezes spread over every state (21-30 % of candidates +20 % in 30 d): no crowding filter here.

## HSQ SQZ's squeeze state on HL listing shorts (think-through 02:5x UTC 11-28, before any run)
Source: SQZ (bnall 2021-23: top off_low quintile P(7-d short loss > 20 %) 17 % vs 7-10 %, every year; blocking it = random), HLE (HL edge = new float). Mechanism: a coin far above its
 post-listing low has trapped shorts (who sold the decay story) and momentum longs; the squeeze is the forced cover. Unstated: on HL the shorts are retail-sized and HL has no spot
 market to borrow-and-sell into, so squeezes may be sharper; but HL lists after Binance often, when the post-listing low is already old. Frozen edges from bnall 2021-23 (verified
 from the cached panel), no refit on HL. Replicates if top quintile P(loss > 20 %) >= 1.5x the bottom-3 pooled and in >= 2 of 3 full years. Description only (SQZ F0 failed as a filter).
HSQ a/b done (is3_hsq.py, hsq_ab.json): SQZ replicates on HL (frozen edges): far-above-low top quintile P(7-d short loss > 20 %) 14.3 vs 9.3 % bottom 3 (2023/25/26 yes, 2024 no: q1 19 %).
 Same quintile has the HIGHEST median short return (+8 %): the squeeze tail rides on the strongest decay, so blocking it throws the edge away (consistent with SQZ F0). By group: risk ratio
 highest in established coins (14 vs 3-6 %), fresh 17 vs 10-12 %.

## TLQ HL tsmom cost by liquidity (think-through 02:5x UTC 11-28, before any run)
Source: HTN (HL tsmom 105x turnover; cost/unit 8-22 bp vs BN 6 bp), PRB/PRL (tsmom > half the HL book's cost). tsmom weights = trend/vol over HL's top 20 by volume: ranks 15-20 are thin,
 high-vol coins whose 1/vol weight is small but whose signal flips often and whose slippage is near the 25 bp cap. Unstated: the thin end may carry the trend (new coins trend hardest) AND
 the cost; a cost cut that removes the trend is no saving. a = per rank tercile (1-7 / 8-14 / 15-20, point-in-time 30-d dollar-volume rank) gross, funding, cost per unit held, by year.
 b = ONE stated variant top_n 10 (no grid), explore 2023-24 then confirm 2025-26 by prereg. c = is it the same saving as PRB2 (lam .33)?
TLQ a done (is3_tlq.py, tlq_a.json): tsmom by liquidity tier: tier1 net +11/+6/-4/+10 %/yr, tier2 ~0/0/+4/+12, tier3 (ranks 15-20) +3/-5/-3/-2 with ~0 price edge after 2023 at 10-27 bp/unit.
 Dose in liquidity. a saw 2025-26 (descriptive), so b's confirm is weakened: say so; b variant (top 10) was stated before a.
TLQ b/conf (tlq_b/conf.json): tsmom top 10 in the HL blend: explore 1.08/1.17 vs .87/.75; prereg TLQ_top10 confirm 2025 2.17 vs 2.19 (FAIL by .02 as written), 2026 1.99 vs 1.47, pooled 2.09 vs 1.85,
 costs lower every year. Strict rule failed; a tie in 2025, so no claim; backlog as a research-session WF candidate with the caveat that a saw 2025-26.

## HFX BTC hedge (and long alts) funding on Binance instead of HL (think-through 02:5x UTC 11-28, before any run)
Source: HLF (BTC hedge longs pay 1.6-8.9 %/yr of book on HL; ETH no cheaper), X1 (HL-BN funding spread is the fspread_hold edge). HL funding on BTC 2024 = 24 %/yr vs Binance 12 %:
 HL longs are more crowded (retail, no spot). Moving the long-only hedge leg to Binance saves the spread times the held weight. Unstated: the spread is exactly what fspread_hold@pair
 harvests, so the HL book's BTC hedge on BN and main@pair would partly be the same trade; and a two-account book needs per-account guards (KS1) and margin on both venues (idle cash).
 Price tracking: HL BTC vs BN BTC daily close diff should be bp-level. a = BTC; b = long alts with a BN twin; c = verdict. Uses cached bnall pickle (to 11-21) -> no nightly-window issue.
HFX a/b/c (is3_hfx.py, hfx_ab.json): BTC funding HL 24 vs BN 12 %/yr (2024); longs on BN would save +3.3/+8.7/+3.8/+2.2 %/yr of book; shorts belong on HL. Blocked by two-account risk (KS1). CLOSED OPEN.

## TLX held-out for TLQ on Binance (think-through 02:5x UTC 11-28, before any run)
Source: TLQ. If thin top-20 names trend worse (noisier, squeezes, listing churn), bnall's thin tier should show lower price P&L per unit gross than its liquid tier in most years, even
 though costs there are low (6 bp). If not, TLQ's gain is HL-specific (HL's thin end = recent listings with decaying float, which trend down and bounce). Unstated: bnall's top 20 by
 volume is mostly majors + a rotating hype name: tier3 there is the hype slot. Frozen tiers, frozen top 10; cached bnall (to 11-21), standalone tsmom defaults, band .005.
TLX a/b/c (is3_tlx.py, tlx_ab.json): bnall thin tier trends as well (tier3 < tier1 in 2/6 years); top 10 worse 5/7 years. TLQ HL-specific; TLQ2 low-medium. CLOSED OPEN.

## LVQ HL lowvol by side x liquidity tier (think-through 02:5x UTC 11-28, before any run)
Source: LVS (2025 = short side +28 %), LVH, TLQ (HL thin tier = fresh listings). High-vol names on HL are mostly the thin, young ones, i.e. listing_short's population after day 61:
 if lowvol's 2025 short gain sits in the thin tier, lowvol is partly a second listing-decay leg (overlap with listing_short, same 2026 drought risk). Unstated: breadth: one year carried
 by a handful of coins is luck-shaped. a = side x tier (ranks 1-10/11-20/21-30 of top 30) by year; b = top-5 coins' share of 2025 short price P&L; c = note for the refit.
LVQ a/b/c (is3_lvq.py, lvq_ab.json): 2025 short gain in tiers 2-3, broad (83 coins, top-5 33 %); corr with listing_short .27-.57. CLOSED OPEN.

## HFY main_bn's shorts on HL (think-through 02:5x UTC 11-28, before any run)
Source: HFX (HL longs pay ~2x; HL shorts receive more 3 of 4 years). main_bn = .5 flow@bn + .5 blend(carry_trend, carry, xsmom). Carry shorts high-funding names: on HL those names'
 funding is usually higher still (crowded HL longs), so the short gains. Unstated: HL slippage on thinner HL books is higher (8-22 bp vs 6), and flow turns over fast: the saving
 may be eaten by costs on the fast leg; carry is slow. a = book total; b = per leg + HL cost difference; c = with HFX: is the 'longs on BN, shorts on HL' split general?
HFY a/b/c (is3_hfy.py, hfy_ab.json): main_bn shorts on HL: funding +0.2..+1.6 %/yr < HL extra cost; net negative every year. Sign bug in the first run caught (fixed, noted). CLOSED DEAD.

## ERC HL blend legs: equal-risk-contribution weights (think-through 03:0x UTC 11-28, before any run)
Source: LVQ (lowvol vs listing_short corr .27-.57). The blend scales each leg to the same standalone vol (unit_vol) and sums 1/3 each: with two legs sharing a factor, that factor
 carries more than 2/3 of book risk. ERC equalises each leg's contribution to book variance. Unstated: with 3 legs and 90-d windows the covariance is noisy, and correlations flip with
 regimes (2024 .28 vs 2025 .57): ERC may chase last quarter. ERC is a general method with no tuned parameter except the window (90 d, monthly: the conventional choice, stated now).
 Implementation: leg multipliers m_i on the leg weights (fin from is3_prl.legs, already book-scaled), renormalised so the book's ex-ante vol under ERC equals the equal-weight book's
 (so the comparison is not a leverage change); multipliers from data up to the prior month end.
ERC a (is3_erc.py, erc_a.json): listing_short = 47-56 % of book variance, ls+lowvol 72-84 %; tsmom near-uncorrelated (diversifier). ERC fixed point checked on a known 3x3 (contributions 1/3 each).
ERC b/c (erc_b.json): ERC explore 1.13/.48 vs .87/.75: FAIL; flat-leg bug in run 1 fixed. CLOSED OPEN: the book needs another uncorrelated leg, not reweighting.

## NPC nested selection with a correlation cap (think-through 03:0x UTC 11-28, before any run)
Source: ERC (risk concentrated, reweighting fails), LVQ. H4 picks the top 3 by Sharpe; when two winners share a factor the book is a two-bet book. A cap makes the third slot go to the
 best different bet. Unstated: a lower-Sharpe uncorrelated leg can still dilute (if its Sharpe is ~0 the book loses); correlations on daily P&L understate tail co-movement (squeezes hit
 both short-alt legs on the same days). Prereg NPC_cap04 (0.4 stated before any run, greedy, hold fewer). Venues: HL (OOS 2024-26) + cached bnall 2021-26 (window-safe).
NPC a/b (is3_npc.py, npc_hl.json): HL capped 1.27 vs 1.21 pooled (2/3 years); binding corr ls-lowvol .41 = right at the cap (fragile). bnall in unit is3-npc -> data/is3/npc_bnall.log.

## HFZ per-account swings of a longs-on-BN / shorts-on-HL split (think-through 03:0x UTC 11-28, before any run)
Source: HFX, KSA. The whole book is ~beta-neutral, but each account alone is a directional bet: the HL account short ~1x alts, the BN account long BTC + low-vol alts. An alt rally that
 the book shrugs off is a large loss in the HL account; margin there can run out before the BN gain can be moved (transfers are manual-ish, minutes to hours, not intraday-free).
 Unstated: the transfer rule IS the risk control; how often it must fire decides whether this is operable for a small account. a = 7-d per-account returns; b = transfers under a
 stated 25 % deviation rule (no tuning) and own-account kill breaches; c = go/no-go.
NPC c (npc_bnall.json): bnall capped 1.72 vs 1.52 (5/6 years >=). Prereg PASS both venues; 2026 inside; CLOSED OPEN -> backlog NPC2 before the 2027-01-02 refit.
HFZ a/b/c (is3_hfz.py, hfz_ab.json): shorts account vol 109 %, worst 7-d -57 %; 122 transfers / 3.5 y. HFX2 -> low. CLOSED OPEN.

## FTL a fourth HL leg (think-through 03:0x UTC 11-28, before any run)
Source: ERC, NPC. NPC's cap swaps lowvol for xsmom_k / resrev / xsmom on HL. If those have ~0 standalone edge on HL, the capped rule "wins" by removing a one-year leg (LVS), not by adding
 a bet: that would still be fine at the refit but the reason matters for what to expect. Unstated: xsmom on HL is momentum across a thin, listing-heavy universe = partly the same
 short-new-coins factor (losers are fresh listings). a = pool SR by year + corr to the short-alt factor; b = the swap candidates in detail; c = verdict.
FTL a/b/c (is3_ftl.py, ftl_a.json): only listing_short 4/4; xsmom_k factor-free 3/4 (weak); NPC2 needs 2-leg baseline. CLOSED OPEN.

## ASR alt-season state vs the short-alt factor (think-through 03:0x UTC 11-28, before any run)
Source: ERC, LVS, R28. Both HL short legs are short alts vs BTC: an alt season (alts outrunning BTC) is their worst state, and alt seasons are trends (they persist for weeks), so a
 trailing alt-minus-BTC return should predict the factor's next month. Against: listing_short's edge is idiosyncratic decay that may continue in alt seasons (fresh float still sells),
 and the hedge is beta-scaled. Unstated: who is trapped: in an alt season retail longs pile into new listings, so listing shorts get squeezed first (HSQ: tail rides on decay).
 State = trailing 30-d (equal-weight alt index return - BTC return), known at the close. Edges from HL 2023-26 (a), frozen for bnall (b). Overlap: 30-d windows daily = ~30x overlap.
ASR a/b (is3_asr.py, asr_a/b.json): no dose HL (+.08) or bnall (+.04); c skipped. CLOSED OPEN.

## FTB FTL on Binance (think-through 03:0x UTC 11-28, before any run)
Source: NPC, FTL. On bnall the standard choice is carry_trend + carry + xsmom; carry and carry_trend are both funding-sorted (likely corr > .4), so the cap drops carry for tsmom /
 xsmom_k. Expect: tsmom on bnall is a strong, factor-free leg (bnall tsmom SR 1.3: PRX), so the BN cap gain should be real diversification, not dilution. a/b/c as queued.
FTB a/b/c (is3_ftb.py, ftb_a.json): bnall cap drops carry (.49 w carry_trend) for tsmom (6/6). CLOSED OPEN.

## FSO do the owner's books net the HL BTC funding drag? (think-through 03:1x UTC 11-28, before any run)
Source: HFX/HFZ, X1. fspread_hold@pair shorts the venue whose longs pay more (HL, mostly) and longs the other: if it holds BTC (or the HL book's long alts), then HL main (long BTC on HL)
 + main@pair (short BTC on HL, long BTC on BN) together = the HFX structure across two books, without a split of the HL book. Unstated: fspread_hold picks the WIDEST spreads among top-20
 pairs, likely thin alts, not BTC; and the books are separate accounts (no netting of margin), so only the funding P&L nets, not the risk. a = which coins it holds; b = aggregate
 funding vs separate; c = verdict. Runs after 03:30 (pair panel reads bn files the nightly job refreshes).
FSO a/b/c (is3_fso.py, fso_ab.json): pair book offsets 10-30 % of HL long funding; complementary. CLOSED OPEN.

## NPS NPC robustness (think-through 03:3x UTC 11-28, before any run)
Source: NPC, FTL. If the cap works because duplicated factors are wasted risk, nearby caps (.3, .5) should give similar results; if only .4 works, it is a knife-edge (HL ls-lowvol .41).
 Top 2 without a cap = 'hold fewer legs' baseline: if it matches cap .4, the gain is from concentration on the best two, not diversification. cap 1.0 top 2 = plain top 2. Reported, not chosen.
NPS a/b/c (npc_*_cap*.json, nps_bnall.log): cap .5 inert, .3 loses both venues, top 2 = standard: knife-edge. NPC2 -> low. CLOSED OPEN.

## T9D post-only fills for PRB2's slow legs (think-through 10:5x UTC 11-28, before any run)
Source: backlog T9c (library N15 gueant §7.2: a trading curve + envelope; child orders need not hit the curve every slice), PRB2 (tsmom+lowvol trade lam .33 of the gap a day), T9 (DEAD as a
 general fix: 5 bp trade-through in 4 h, taker fallback raised costs ~20 % via ~150 bp drift chasing; skip-unfilled cut costs 65-80 % but cost Sharpe: the filled half is the bad half for trend legs).
New angle: under lam .33 an unfilled order is not a missed trade, it is a lag: the gap stays and tomorrow's order covers part of it. So the T9 failure (chase or lose the signal) may not apply
 to a book that already lags on purpose. Unstated: who fills a resting buy at the close? Sellers pushing price down = adverse for a trend long (tsmom wants up-movers); for lowvol (low-beta,
 slow), fills are closer to noise. Fill model strict: a later 1h bar must trade THROUGH the level (low < L for buys, high > L for sells), no queue credit. BN-82 1h, legs built on BN-82 1d,
 explore <= 2023 only. a = fill fractions 1h/4h/24h at 0 / -2 bp by leg and side; b = adverse selection and net saving; c = envelope. Change my mind: 24h fill < 70 % or filled-minus-unfilled
 24h signed return < -5 bp (eats the 5 bp taker saving).
T9D b (t9d_b.json): fills are not adversely selected (filled r24 = all); the cost is the 0.3-4 % unfilled runaways (+450..700 bp/24h) that must be chased. BN net save q0 +2.5 bp/unit
 (.75 %/yr), q5 ~0, q10 -5: worthless on BN. The lever scales with the taker slip avoided: on HL (8-22 bp) the arithmetic is ~10 bp/unit, but untestable here (HL 1h too short). c = envelope (no chase inside 1x step).
T9D c (t9d_c.json): BN slow sub-book: post-only cuts costs 2.18 -> .65 %/yr, but missed runaways give it back: +.9 %/yr at q0, 0 at q5, -1.6 at q10 (envelope in between). Below bar on BN.
 Unstated condition that would make it work: taker cost much larger than the selection loss, i.e. HL thin names (slip 8-22 bp). Selection loss scales with volatility, saving with cost. add-form d (HL 7.5 months).

## LSX LSB2 precheck: legs, stress, sizing (think-through 10:5x UTC 11-28, before any run)
Source: backlog LSB2, LSB/LSP/LSW (no chat records). Already known: lsp_abc.json book corr BTC .00 every year (the 11-09 corr .63 is gone: that was an older listing_short version), alt shorts
 -44/+41/+9/-12/-7/+2 % by year 2021-26, LSW: 3 squeeze controls failed (SQZ, LSV, LSW). Event view (LSB): median +22..+41 % every year, mean crushed by a minority.
Unstated, what a trader shorting fresh listings must be doing: a hard buy-stop (no one holds a short through a 3x), a cap on concurrent names (margin), and staggered entry. A stop on a daily
 close path is a real, operable squeeze control that LSW/SQZ did not test (they tested predictors and weights, not exits on own P&L). Daily closes understate the gap: the stop fills at the
 close that crosses it (worse than the level). a = event split short-alone vs BTC-alone per year (d2->d61) + day-clustered t; b = drop worst 10, path stops at -50/-100 %, top-3 share; c = 5 concurrent.
Change my mind: a stop that lifts the event mean above 0 in >= 5 of 7 years with the median kept -> c sizing GO candidate; else LSB2 stays parked with this reason.
LSX a (is3_lsx.py, lsx_a.json): 678 bnall events: alt-leg median +20..37 % every year, net mean 4.5 % pooled, t_month .01; book corr BTC .00 (11-09 'BTC-leg' finding obsolete).
LSX b (lsx_b.json): path stops -100/-50/-30 % lift the pooled mean to 7-8 % and t to 1-2, but vs a same-size random-exit placebo the gain is all 2021 and negative in 2020, 2024-26. FAIL.
LSX c (lsx_c.json): 5/10-slot books SR -.08/-.16 (ruinous tail at 1/5 equity per name), .30/.42 with stop100 (2021-only lift); 2025-26 <= .5 everywhere. NO-GO. CLOSED OPEN: LSB2 parked (4 squeeze controls failed).

## E2C flow@bn decision anchor 00 vs 16/20 UTC (think-through 11:0x UTC 11-28, before any run)
Source: backlog E2b, E2 (CME-break buy-first/sell-after: flow +7.2/+2.1/+1.1 bp/unit by year 2024-26, fading), E2B (blend_nested's anchor costs nothing, but its 3-h sell deferral = placebo
 deferrals at other hours: not adopted; flow@bn untestable then: no hourly taker split). New: metrics_full has 5-min taker buy/sell ratio for 605 coins since 2021-12 (100 % coverage):
 hourly taker buy ~ qv x mean(r/(1+r)) (equal 5-min weights inside the hour: an approximation; validated at the 00 anchor against the true daily tbqv before any anchor is read).
Mechanism for an anchor cost: flow is a 3-day imbalance; its alpha decays within 24-48 h (T9B), so a 16 UTC anchor uses a window 8 h fresher than 04:03 live trading but the US session flow lands
 differently. Unstated: E2's saving is a 1-h net long over the break, i.e. a drift bet, not a cost cut; E2B showed such deferrals are generic. Explore 2022-23 (Dec 2021 = warm-up), then 2024-26.
Change my mind: approx-00 SR within .15 of true-00 AND 16/20 anchors >= 00 - .15 in every explore year -> b/c; an anchor loss > .15 in 2 of 2 explore years -> DEAD at current size.
E2C a (is3_e2c.py, e2c_a.json): approximate hourly taker split from metrics_full (xs rank corr .83 vs true daily; SR .63 vs .78 at 00). flow@bn anchors 00..20: 00 worst (.63), 16 = 1.05
 and >= 00 in 5/5 years; phase spread .47 SR. Anchor move costs nothing. b: the break execution itself (buys at the break hour, sells deferred) on flow's trades at the 16/20 anchors, with placebo hours.
E2C b (e2c_b.json): break sell deferral +2.8/+2.2 bp/unit (t ~1), 2024-only, rank 19-20 of 23 placebo hours; delay to the break free. DEAD at its size (~.2 %/yr).
E2C c (e2c_c.json): 6-anchor average flow@bn SR 1.16 vs 00 .63 (pair corr .55; sqrt(6/3.75) x .90 = 1.14 predicted): phase diversification, not a fit. CLOSED OPEN -> backlog FPD.

## FPT flow@bn anchors on the TRUE hourly taker split (think-through 11:1x UTC 11-28, before any run)
Source: E2C (approx split from 5-min taker ratios: anchors .63-1.10, avg6 1.16). The approximation weights 5-min ratios equally inside an hour; a burst minute carries most of an hour's
 volume, so the approx imbalance is noisier, and noise differs by hour of day (US hours bursty): the phase spread itself could be partly approximation noise. If the true split shrinks the
 anchor spread and the pair corr rises (> .8), the avg6 lift shrinks with it (sqrt(6/(1+5 rho))). Unstated: E2B's blend anchors spread .3 SR on true data: some phase noise is real.
 Data: same public archive files as bn100, column 10 kept, only coins ever in the point-in-time top 40 (flow uses top 30). Known answer: 24 hourly tbqv sum == daily tbqv.
Change my mind: as queued (c). 

## PDX phase diversification of the Binance daily legs (think-through 11:1x UTC 11-28, before any run)
Source: E2C c (flow avg6 1.16 vs 00 .63), E2B a (blend anchors 1.57-1.87 on bn100, 'phase noise +-.15'), the 2026-11-10 staggering of every_days > 1 schedules (same argument, adopted).
Mechanism: a daily book sampled at one hour carries the noise of that hour's prices (signal and fills both): 6 anchors are 6 noisy draws of the same bet; their average keeps the bet and
 cuts the timing noise, by sqrt(6/(1+5 rho)). Slow signals (carry: funding averages over days) should be phase-stable (rho ~ .95, no gain); fast ones (flow 3-d, xsmom short lookbacks) noisy.
Unstated: (1) the gain is free only if the 6 sub-books net their trades (one account), else costs x ~1; (2) live trades at 04:03 on the 00 bar, so live's phase is ~04; (3) rho from the same
 sample that measures SR: the predicted lift is a check of arithmetic, not evidence. Change my mind: a leg with rho > .9 that still gains > .2 SR from avg6 = a bug (the arithmetic cannot do it).
PDX a/b/c (is3_pdx.py, pdx_ab.json naive, pdx_x.json exact): the naive avg6 lift (x1.22-1.27 on every leg, = sqrt(6/(1+5 rho)) exactly) was an ARTEFACT: averaging daily returns whose windows are shifted
 4-20 h smooths them. On one hourly clock rho .95 and avg6 = mean single (blend 1.54 vs 1.58). CLOSED DEAD. E2C c's flow 1.16 used the same flawed alignment: re-check in unit is3-pdxf.
 Peak RAM of pdx x was 2.19 GB (over the 2 GB rule): the flow re-check runs in a unit with MemoryMax 1800M and fewer columns.

## T5D OI building on a 3-day fall as a SHORT-side filter (think-through 11:2x UTC 11-28, before any run)
Source: T5b (2023: losers with rising OI bounce, IC +.032), T5c (long-side filter failed confirm, sign flipped after 2024). Data: the Binance metrics archive starts 2021-12-01 for every coin
 but BTC, so explore = 2021-12..2022-12 only (one bear year; the queue's '2021-22' is in practice 2022). Mechanism: OI rising while price falls = new shorts piling in (or longs averaging down);
 if new shorts are late, they are the fuel of a short squeeze (bounce); our books' shorts in those names sit next to them. Unstated: in a bear trend (2022) new shorts are RIGHT more often
 (continuation), so 2022 may show the opposite of 2023: that is the T5c regime flip again. Outcome = the short's next-day P&L, market-relative (minus the universe's equal-weight mean), plus funding.
Change my mind: top OI-build tercile short P&L below the bottom tercile by >= 10 bp/day with a dose (quintiles monotone-ish) in 2022 -> b; else the filter has no explore support.
T5D a/c/d (is3_t5x.py, t5x_a_<yyyy-mm>.json, t5x_d.json): short-side OI-build spread by year +12/-18/+22/-35/-25 bp (2022-26), |t| <= 1.34, shuffle null 14-88th pct, no dose. d: books' own shorts mixed sign (only 2026 favours a filter). b skipped. CLOSED DEAD (F3: 3 forms).

## T9F post-only execution for flow@bn (think-through 11:2x UTC 11-28, before any run)
Source: T9D (PRB2 slow legs: 99 % fill at the touch, the unfilled 1-4 % are runaways that cost back most of the saving; BN +.9 %/yr at q0, 0 at q5), T9 r2 (BN-82 tsmom/xsmom post-only lost
 SR), flow@bn never tested on Binance. flow is a 3-day taker-imbalance continuation signal: its trades chase recent flow, so a resting buy fills when price dips against the flow, i.e. when
 the signal is momentarily wrong; the unfilled are where the flow continues hardest. Unstated: turnover 175x/yr means the saving per unit (~3 bp + slip) is multiplied 5x vs the slow legs,
 but the runaway cost scales with the signal's own 24-h alpha (T9B: flow's alpha accrues within 24-48 h), so the ratio, not the turnover, decides. Change my mind: as queued (c).
T9F a/b/c (is3_t9f.py, t9f_ab.json, t9f_b2.json): BN daily books: fills free, unfilled runaways +4-7 %/24h; post-only at the close +2..5 %/yr at q0 but <= 0 at 5 bp stress; resting k=10 bp below
 (filled there) +2-3 %/yr for flow/carry/carry_trend at 3 bp extra stress, xsmom 0. Written bar fails everywhere; post-hoc cells not confirmed. CLOSED OPEN -> backlog T9G (live fills decide).
 Note for T9D: its q-stress gave no price improvement (fills at the close), so its HL/BN numbers are the conservative side of this model.

## T9K rest-below depth dose (think-through 11:3x UTC 11-28, before any run)
Source: T9F. Resting a buy k bp below the close earns k on fills and loses the runaways; daily alt ranges (3-8 %) mean fills barely fall until k is a sizeable share of the range, so the
 curve should rise then fall; the peak sits where the marginal lost fill (a runaway, +4-7 %) outweighs k x fills. Checked, no timing bias: the added piece earns C1/L - 1 with
 L = C0 (1 - k) wherever inside the day it fills = drift + k, which is what the sim books. Unstated: a deep resting order is a free option given to faster traders (it fills on news
 gaps first); the 3 bp extra stress is the only guard here. Rule for c, stated
 now: the smallest k within 80 % of the explore peak. Bias of deep k is upward, so c prefers small k.
T9K a/b/c (is3_t9f k/kp, t9k_a.json, t9k_placebo_flow.json, t9k_b.json): rest-below gain grows with k (flow +10.6 at k100) but the matched placebo shows fee = the lever (+8-9 %/yr), level k paid
 back by selection ~1:1; HL slow legs below placebo. Frozen for T9G: flow k 50, carry_trend k 20. CLOSED OPEN.

## LSH listing shorts, hourly squeeze stop (think-through 11:3x UTC 11-28, before any run)
Source: LSX (daily stops lose to a random-exit placebo outside 2021; the stop pays a ~25 % gap beyond its level on daily closes). Question: is the failure the gap (fixable by an hourly
 exit) or the selection (stopped names would have decayed later anyway)? If the gap: hourly stops cut the beyond-level loss to a few % and beat the placebo in most years. If selection:
 hourly stops trigger MORE often on intraday wicks that later revert, and lose more. Unstated: squeezes on fresh listings often wick and retrace within hours (thin books), so finer stops
 may be worse. Change my mind: hourly stop beats placebo in >= 5 of 7 years.
LSH a/b (is3_lsh.py, lsh_ab.json): hourly stops: gap beyond -9 % (daily -30 %) but more stop-outs on retracing squeezes; mean unchanged; vs placebo 4/7 years (2021 only). c skipped. CLOSED OPEN.

## T9L live precheck of the rest-below fill model (think-through 11:4x UTC 11-28, before any run)
Source: T9K. The backtest says 90 % of flow's daily orders would fill 50 bp below within 24 h (k50 + 3 bp), with the unfilled being runaways. Live orders (Nov 2026, ~390 fills over 18 days,
 low-vol market?) test whether that fill share holds on this month's ranges; the live slip_bps tells whether the backtest's taker cost (fee 5 + slip model) is what live pays. Unstated:
 18 days is one regime; fills are clustered by day (~20 per day), so the effective n is ~18: only a gross contradiction (fill share < 70 %) would count. 4h bars are coarser than 1h:
 the 24 h window = the 6 bars opening after the fill (conservative: the bar containing the fill is excluded).
T9L a/b/c (is3_t9l.py, t9l_ab.json): live Nov orders of flow@bn: k50 fill 88 % (bt 90 %), filled -264 / unfilled +543 bp at 24 h (selection as predicted), live slip 1.1 bp. CLOSED OPEN.
T9C a/b (prereg T9C_flow_k50 / _carry_trend_k20, t9c_confirm.json): FAIL both: vs taker +8.7 / +2.5 %/yr pooled 2024-26 but <= random fee-only fills (-0.2 / -0.95); flow 2026 -1.0. CLOSED OPEN.
FLL a/b/c (is3_fll.py, fll_a.json; first recorded under the id FLD, which collided with the closed FLD item of 11-2x: repaired the same session, old item and is3_fld.py restored from git; no think-through was written before this run, a lapse): shadow:flow@bn -9 % / 19 d = 3-5th pct of backtest 19-day windows; price loss (fees -$4, funding +$2); same-days replay -13.6 % (corr .83): no implementation gap. CLOSED OPEN.

## FHM flow on HL prices at maker fees (think-through 11:4x UTC 11-28, before any run)
Source: L2b (Binance taker flow continuation transfers to HL prices, +19 %/yr gross, killed by 17-50 %/yr HL taker costs), T9C (OOS the maker fee is the lever). Mechanism: Binance's
 taker imbalance leads HL (deeper venue leads); HL thin books make taker execution expensive, but a resting order on HL costs 1.5 bp. Unstated: (1) the random-fill placebo is an UPPER
 bound (real fills are selected against us ~1:1 with any improvement, T9K/T9C); (2) HL queues on thin names are short, so fills are likelier but adverse selection by faster HL
 makers may be worse; (3) HL perps list fast: the hlx universe is the HL coins with Binance flow. Frozen config (live flow@bn), no grid. Change my mind: as queued (c).
FHM a/c (is3_fhm.py, fhm_a.json): flow on HL at maker fees: selection-free upper bound SR .39 (-.79/.79/.50/.65), taker ~0, corr HL book .06. b skipped. CLOSED OPEN.

## MBL main_bn's first 19 live days (think-through 11:4x UTC 11-28, before any run)
Source: FLL (shadow:flow@bn -9 % = flow's own loss, replay -13.6 %). main_bn = .5 flow@bn + .5 blend_nested@bn (+ the ladder sleeve). If the blend half also matches its replay, the book's
 -9 % is the strategies, not the plumbing; if the blend half diverges, it is an implementation gap (universe, timing, sleeve). Unstated: the two halves can both be fine and the book still
 look worse than the mean of its shadows (sleeve fills, rounding at $1,000, min orders). Change my mind: replay corr < .7 or live < replay by > 3 % -> a fault to chase.
MBL a/b/c (is3_mbl.py, mbl_c.json): main_bn -9.1 % / 19 d = 1.8-3.0th pct of its mix's 19-day windows, price-driven, both halves down, flow replay worse than live. Not a fault. CLOSED OPEN. Tool gap -> backlog LVB.
PDX-lesson audit (11:5x): grep of research/studies + kripto/research.py for multi-anchor / phase averaging: only is3_e2c c and is3_pdx ab averaged shifted daily windows (both corrected);
 strategies.scheduled(phase=None) averages POSITIONS of staggered schedules on one daily grid (returns on one clock): correct by construction; research.py phase spread reports phases separately.
HANDOFF (11:56 UTC 11-28): unit is3-fpt chunk 2 downloading the rest of the true 1h taker split (1463 coin-months, ends ~12:21) -> data/is3/k1h_tb. FPT next (due 12:45): first
 `python -m research.studies.is3_fpt check` (known answer: 24 x hourly tbqv == daily tbqv; if coin-months are left, run `dl` again in a unit), then b in a unit (MemoryMax 1800M: is3_pdx xf
 peaked 2.19 GB unrestricted): `systemd-run ... python -c "from research.studies import is3_fpt as F; F.form_b()"` -> fpt_b_a.json + fpt_b_xf.json; c verdict by the queued rule.
 Open threads: T9G (live maker shadow for flow@bn, LOW-MEDIUM after T9C), LVB (live_vs_backtest for main books), FPD (low).

## FPT true hourly taker split (think-through 12:5x UTC 11-28, before b)
Source: E2C a/c (approx split from 5-min metrics ratios, rank corr .83 vs true daily), PDX xf (approx split, exact one-clock avg6 .86 vs mean single .81, rho .88, singles .52-1.01).
Question: is flow@bn's anchor spread (00 .52 worst, 16 1.01) a property of the signal (e.g. the 00 UTC anchor trades into the Asia open / funding stamp) or noise from the approximation?
With the true split the approx noise is gone; if the spread stays (.5 SR range) at rho ~.9, it is one sub-book's luck over 5 years (SE of SR on 5 y ~ .45), not diversifiable: avg6 can't lift
 much when rho is .9 (max lift sqrt(6/(1+5*.9)) = 1.04x). Prediction: avg6 - mean single < .1 -> FPD closes. Unstated: live flow@bn trades the 00 anchor; if 00 stays the worst by a lot in
 every year, a cheaper fix is just moving the anchor (but choosing the best of 6 in-sample is selection: a 6-way max of SR with SE .45 is worth ~ +.5 by luck alone), so no anchor switch on this.
a done: 439 coins, known answer passes (p99 rel err ~1e-16), 8 coin-months have no archive.

## LVB main-book live vs backtest (think-through 13:0x UTC 11-28, before any code)
Source: MBL (main_bn -9.1 % / 19 d checked only leg by leg), paper.run_books: main target = main_scale x sum(alloc_i x last saved target_i), then apply_risk, rebalanced whenever any
 entry has a fresh row. A replay of exactly that on the live panel is the main book's own check. Unstated pitfalls: (1) allocs and main_scale CHANGED during the period (PRB2 11-28,
 main_scale 11-27, ladder sleeve 11-27): current config replays are valid only after the last change (--since), earlier days carry a config gap I must not read as a fault; (2) the ladder sleeve
 trades inside main_bn's account: its P&L is in live equity but not in the replay (report sleeve fills separately); (3) $1,000 with 5 % caps: min orders bind more than in a $2,000 shadow (band).
Change my mind (MBL rule): corr < .7 or live < replay by > 3 % on post-change days, sleeve excluded -> chase a fault.
FPT b/c (is3_fpt.py, fpt_check.json, fpt_b_a.json, fpt_b_xf.json): true split known answer exact; one-clock singles .42-.90 (mean .705), avg6 .74, rho .91: lift +.035, bounded x1.04 by rho.
 FPD closed (no staggering of flow@bn), no anchor switch (00 -.19 vs mean = .4 SE). CLOSED OPEN.

## T9P maker at the touch, live Nov orders of flow@bn (think-through 13:2x UTC 11-28, before any run)
Source: T9C (depth adds nothing OOS; the fee saving is the only robust part), T9L (k50 live fill 88 %). At k = 0 a resting order sits at the decision mid: it fills on any trade-through,
 so the fill share should be ~95 %+, and the unfilled are the orders where price ran away immediately (flow continuing hardest). Saving per filled unit = 5 - 2 bp fee + live slip 1.1 = ~4 bp;
 cost = the unfilled share x their 24-h runaway (or, carried, the next day's re-decision). Unstated: (1) live bars are 4 h and I exclude the bar containing the order: a k0 order that would fill
 within minutes is counted only if price comes back in hours 4-24 -> fill share is UNDERSTATED, the runaway cost OVERSTATED (conservative); (2) queue position: at the touch we are behind the
 queue, a trade-through of q bp is the proxy; (3) selection: fills happen when price moves against the signal, measured as the signed move decision -> 24 h on filled vs unfilled.
Change my mind: as queued (c): net >= +2 bp/unit at q3 and fill >= 85 %.
LVB a/b/c (scripts.live_vs_backtest --main, tests/test_lvb_main.py, is3_lvb.py, lvb_b.json): main corr .95; main_bn since 11-18 corr .95, live -3.2 vs replay -5.1. small:main_bn corr -.02 on the $5 band,
 .79 and -0.60 = -0.60 with per-symbol minima: holds 3/31 targets, 10 % of the 57 % target gross (BTC target $36 < $50). The $200 BN twin is not main_bn at $200. CLOSED OPEN -> SMB.
T9P a/b/c (is3_t9p.py, t9p_ab.json, t9p_b.json): at-touch k0 on 4h bars -32 bp/unit (an exclusion artefact: hand-checked BTC 11-21 fills 2 min later); on HL 1-min paths 99.9 % fill,
 median 1 min, net +3.97 bp/unit vs live taker, 14/14 days. PASS by the stated rule -> T9G frozen k0/q3/carry. CLOSED OPEN.

## SMQ $200 Binance with per-symbol minima (think-through 13:0x UTC 11-28, before any run)
Source: LVB (small:main_bn holds 3/31 targets, 10 % of target gross; BTC target $36 < $50). main_bn's mix is ~57 % gross over ~30 names = ~2 % per name = $4 at $200: below $5 for most names,
 so a truncated $200 book holds only its largest weights (BTC hedge? capped alts). Expect: SR falls a lot and the book is mostly cash; the band-only small_acct says little changes (it skips
 trades < $5 but lets every position be opened by a bigger move). Unstated: a $200 trader would not hold 30 names; he'd hold the few strongest. That is form c (top-N re-scaled), a different book,
 judged only descriptively. Account kept at a constant $200 (no compounding; re-funded) so the minimum binds the same way every year. Change my mind: truncated $200 SR within 80 % of $1,000 ->
 the $200 BN account is fine and only STATUS needs a deployed-gross note.
SMQ a/b/c/d (is3_smq.py, smq_abc.json, smq_d.json): main_bn mix $1,000 1.75 (vol 23.5); $200 band 1.71; $200 per-symbol minima 1.70 at gross .45, deployed .47/.58/.65/.62/.39/.19 by year (2026: 2.6 names).
 Legs alone die at $200 (flow .19). Top-N vol-matched: N4 1.56 / deployed 2026 .47: deployment only. First run of a forgot the .5 allocs (gross 1.6, vol 47 %): caught by the vol, rerun. CLOSED OPEN.

## T9Q maker at the touch on HL's own live fills (think-through 13:1x UTC 11-28, before any run)
Source: T9P (BN orders on HL-proxy minute paths: 99.9 % fill, +4 bp/unit). Here venue = path = HL, so no proxy. HL saving per filled unit = 4.5 - 1.5 = 3 bp + live slip (HL thin books:
 slip larger than BN's 1.1 bp, so the saving should be bigger on thin names). Unstated: (1) HL queues on thin names are short but a trade-through by q on a thin name can be one small print
 (the 1-min low is a single trade): q 5-10 bp guards; (2) HL fills from the slow legs (PRB2 lam .33) are small partial steps: many tiny orders, maybe below the $10 minimum when maker-split;
 (3) adverse selection again lives only in the unfilled tail. Change my mind: as queued (c).
T9Q a/b/c (is3_t9q.py, t9q_ab.json): HL books' own fills on HL 1-min paths: 99.8 % fill at q5, median 1 min; main +3.89 bp/unit (40 orders, 13/13 d), all books +2.61 (one thin-name runaway +583 bp).
 ~+1.2 %/yr at main's turnover: real, small. T9c frozen k0/q5/carry. CLOSED OPEN.

## SMH $200 HL main book (think-through 13:1x UTC 11-28, before any run)
Source: LVB/SMQ. Live: small:main holds ONLY BTC ($31, 16 % gross) vs main 26 names / 67 % gross: its -4 % is BTC's November fall, not the strategy. HL main = blend(listing_short, lowvol, tsmom,
 slow_lam .33) x main_scale .871, ~26 names at ~2.6 % each = $5 at $200 < $10 HL minimum: only BTC (the beta hedge, big weight) clears it. Expect the backtest deployed share to be
 tiny for all years with many names; unstated: the slow legs (lam .33) make trades even smaller (partial steps), so with the band model even more is skipped.
SMH a/b/c (is3_smh.py, smh_a.json, smh_b.json): HL $200 holds 2-3.6 names (BTC + 1-2) of 27-144, deployed .41-.57; live = BTC only ($31). SR 1.12 is BTC timing. CLOSED OPEN -> SMB (both venues).
SMR a/b/c (kripto/research.py small_minima / min_weight / small_acct_min + small_deployed, tests, is3_smr.py, smr_b.json): known answer exact (diff 0.0). Docs + standing lesson. CLOSED FEATURE.
 Left for a research session (SMB): STATUS $200 rows with deployed share; re-quote candidates' small_acct_min when their WFs are next re-run (no extra registry lines today).

## SMD a $200-able book (think-through 13:1x UTC 11-28, before any run)
Source: SMQ d (BN top-N vol-matched: N4 1.56, deployed 2026 .47), SMH (HL $200 = BTC + 1-2). A $200 trader with a 25 % vol target has ~$120-170 of gross: at $10 per name that is <= 12-17 names,
 and with BTC as the hedge leg taking a big share, fewer. Unstated: he would not truncate (drop everything small) but ROUND: place the minimum on a name the model wants at >= half the minimum,
 accepting over-weighting the weakest names; that keeps breadth (the source of a x-sec book's SR) at the price of tracking. Over-weighting raises gross, so the vol is capped at the $1,000 book's.
Change my mind: as queued (c). Prior: low for HL (the blend's tsmom/lowvol legs are broad; few-name versions lose breadth), medium for round-to-min.
SMD a/b/c (is3_smd.py, smd_a.json, smd_b.json, smd_track.json): top-N fails (3.7 names); round-to-minimum PASSES: HL 1.21-1.23 vs 1.58, deployed .61/.72, corr .78; BN 1.50 vs 1.77, .83/.75, corr .91.
 BN band bug ($10 -> $5) caught by comparing with SMQ. CLOSED OPEN -> backlog SMX (small: twins trade round-to-min).

## SMY round-to-min on the live small twins (think-through 13:2x UTC 11-28, before any run)
Source: SMD (history: round-to-min tracks .78 HL / .91 BN). Live since 11-18 is 10 days: a replay of what small:main / small:main_bn WOULD have held with the rule, compared with the live
 big sibling (main / main_bn) day by day. Unstated: (1) at $200 a minimum-sized position is 5 % (HL $10) or 2.5 % (BN $5), BTC 25 % on BN ($50): rounding BTC up to $50 when the target is $25-49 doubles
 the BTC leg; (2) names hovering near half the minimum enter and leave at full minimum size: churn at 4.5-5 bp per crossing; the $10 trade band does not stop a crossing (it is a 5 % jump);
 (3) 10 days, effective n ~10: only a gross failure (corr < .5) would count against SMX.
SMY a/b/c (is3_smy.py, is3_smd churn, smy_a.json, smy_b.json): truncation replay = live small twins exactly (known answer); round-min live corr .94 HL / .87 BN; churn 13/15 % of gross;
 hysteresis worse (1.01/1.39). SMX spec frozen: round-to-min at half the minimum, no hysteresis. CLOSED OPEN.

## T9R pair book at the touch, leg risk (think-through 13:2x UTC 11-28, before any run)
Source: T9P/T9Q. The pair book is long one venue, short the other in the same coin. Both legs rest at the decision price; on one price path a buy fills on a dip, a sell on a rise. If both fill
 at the same level, the gap between them costs nothing (each leg's entry is the level; the open leg's P&L over the gap is zero when the other fills at that level). The cost is a leg that NEVER
 fills in 24 h: the filled leg is then unhedged and, by construction, on the wrong side of a one-way move (the hedge failed to fill because price ran in the direction that hurts the filled leg).
 Unstated: the pair book's edge is funding spread (bp/day), tiny next to a 1 % directional move, so even rare one-leg cases can eat the saving; the fallback (taker at the end) caps it.
 BN leg judged on the HL path (same coin; basis few bp; q 5 bp).
T9R a/b/c (is3_t9r.py, t9r_ab.json): pair legs at the touch: 97.8 % of pairs both filled, gap median 5 / p90 124 min, 1 one-leg pair -306 bp; net +3.06 bp/leg unit. Gap clause fails: pair stays taker. CLOSED OPEN.

## MBT main_bn turnover gap (think-through 13:2x UTC 11-28, before any run)
LVB b: since 11-18 main_bn live turn 1.40 vs replay 2.12; shadow:flow@bn 4.74 vs 5.13 (close). main_bn = .5 flow + .5 blend_nested@bn; blend_nested@bn's shadow only started 11-26.
Suspects: (1) the 11-26 mix change: before 11-26 main_bn traded a different second leg; the replay uses today's (blend_nested@bn since 11-18): a config gap, not a fault: test by splitting
 days before/after 11-26; (2) netting: flow and blend opposite on a coin -> live nets, replay nets too (same); (3) per-symbol minimum at $1,000 (BTC $50 = 5 %): replay now has it;
 (4) the 'due' logic: main rebalances only on a fresh row or alloc change. Expect (1) to explain most of it.
MBT a/b/c (is3_mbt.py, mbt_ab.json): main_bn turnover gap = the 11-26 mix change (before .62 vs 1.45, after .35 vs .40); no skipped rebalance; tool prints the last config change. CLOSED DEAD (no fault).
SMP a/b/c (is3_smp.py, smp_a.json, smp_b.json, kripto/venue_pair.whole_pairs + tests): live small:main@pair held GRAM@bn / ZEC@bn unhedged (27 % of gross). FIXED: pairs whole or nothing.
 History $200: per-leg truncation SR 1.32, whole 6.57, round-up both 7.33 ($1,000 7.34). CLOSED OPEN.
TWC a/b/c (scripts/twin_check.py + health WARN + tests, twc_ab.json): first run found the 2 known orphans + 2 new faults (pair INIT resized on BN only; small DOGE kept the wrong side after
 a below-minimum flip); fixed: venue_pair.whole_pair_trades, paper.rebalance closes on a below-min flip. CLOSED FEATURE.
LVP a/b/c (live_vs_backtest venue pair, lvp_ab.json): shadow pair corr .82 (lag test .03/.82/-.11), live +0.88 vs +0.67 %, funding .97 vs 1.05 %. main@pair 1 day. CLOSED OPEN.

## T6P T6b precheck (13:3x UTC 11-28): data integrity + power, no returns looked at
T6P a/b (is3_t6p.py, t6p_ab.json): 453/453 hours, 0 gaps, 38 accounts/snapshot but only 14 % day-to-day overlap (3812 accounts in 19 d); 177 coins/day with >= 3 accounts; x sd .70, AC .70.
 MDE daily rank IC: 14 d .135, 28 d .096, 60 d .065. PRE-REGISTRATION T6b (written before any return is joined): signal x(coin, day) = mean over the day's hourly snapshots of
 sum(sign(szi) x positionValue) / sum(positionValue) over accounts holding the coin, coins with >= 3 accounts; outcome = next UTC day's simple return on HL (close to close), ranked
 cross-sectionally; statistic = mean daily Spearman IC, t from day-clustered (one IC per day) with Newey-West 3 lags. EXPLORE = 2026-11-10 .. 2026-12-07 (28 d): look, choose sign,
 at most 2 variants (level x, and per-account change dx over 1 d on accounts present both days). CONFIRM = 2026-12-08 .. 2027-02-05 (60 d), untouched until then: PASS = same sign as
 explore, t >= 2, and IC >= .03. Fade vs follow is decided on explore only.
T6P c: pre-registration above, copied to backlog T6b. CLOSED.

## FLX flow@bn decay (think-through 13:3x UTC 11-28, before any run)
Source: SMQ b (flow alone SR by year 2.66/-.01/2.02/1.07/.47/.22 at main weight), FLL (live = 3-5th pct of backtest 19-d windows). Decay mechanisms: (1) crowding (taker-flow
 continuation is a known signal; more market makers lean on it); (2) the universe grew 113 -> 532 names: the 5 % cap spreads the book over more, thinner names where costs eat the edge;
 (3) a regime (2023 was a trend year for alts). Unstated: 2021 and 2023 dominate the average; a 'decay' test with 6 yearly points has no power: slope t over monthly returns with HAC is
 the minimum. Change my mind: monthly-return slope HAC t <= -2 AND IC by year falling in 2025-26 vs 2021-24 -> real decay; else 'weak recent years' consistent with noise.
FLX a/b/c (is3_flx.py, flx_ab.json): flow slope HAC t -1.0 (blend -1.34): no significant decay; but 2025-26 flow = funding 18.9/15.4 %/yr + price +4.7/-1.6 (2023-24 price 33-35): the price
 edge is ~0 for 2 years, flow is now a carry book overlapping blend. No clause met, no lifecycle change. CLOSED OPEN -> backlog FLX2.
SXR a/b/c (sxr_a.json, sxr_b.json): live $200 twins deployed 0-.90 of their shadow (carry@bn 0, flow@bn .15, blend_nested .21); round-to-min would give .79-1.09 for all entries. carry_trend@bn gap -> TWV d. CLOSED OPEN.
CTG a/b/c (ctg_ab.json): small:carry_trend@bn: BTC target $56.40 = 58 % of its gross, Binance step .001 BTC > $56 -> floored to 0; the rest < $5. No fault; SMX rounds to max(min, one step). CLOSED OPEN.
SMA a/b/c (kripto/research.round_to_min, small_acct_round, tests, is3_sma.py, sma_b.json): known answer exact. CLOSED FEATURE.
FLP a/b/c (is3_flp.py, flp_ab.json): main_bn mix .5 flow 1.75 vs blend alone 1.66 vs .25 flow 1.80 (2025-26 .86/.98/.99); funding overlap per coin .85. FLX2 pre-registered (+.1 OOS SR keep bar). CLOSED OPEN.

## SMXB build SMX (14:5x UTC 11-28)
SMXB a/b: built round-to-min for the live small: twins (paper.round_targets_to_min, effective_min = minimum rounded up to whole steps; venue_pair.round_pairs_to_min); 222 pass, trader 14:50 exit 0.
 Not capped by max_gross after rounding (worst case at $200: every name at the minimum; HL 20 x $10 = 1.0x, far below max_gross). Form c after the 11-29 00:00 rebalances (deferred 01:30).

## SMXR dry-run of SMX before its first live rebalance (think-through 15:0x UTC 11-28, before any run)
Source: SMXB (code shipped 14:50), SXR (would-be deployed .79-1.09), CTG (BN BTC step). Question: what will each small: twin hold at the 11-29 00:00 bar, and does any rounded target
 break a risk cap? Unstated by the spec: (1) apply_risk caps weights BEFORE rounding, so rounding can push one name past max_asset_weight .35: BN BTC one step ~$90 = .45 of $200;
 a small trader with a 35 % per-name cap would simply not hold BTC there; (2) rounding raises gross most for books with many tiny weights (flow@bn ~500 names x $2-3 -> up to N x $5);
 (3) the first rebalance is a transition: every rounded name is opened at once, one-off fees. Method: copy state/paper.db to /tmp, re-run run_books there with the latest saved targets,
 live marks (one HL + one BN public request) and the shipped rebalance with mark fills; read positions. Change my mind: any small book > max_gross or a name > .35 -> fix in code (general rule).
SMXR a/b/c (is3_smxr.py, smxr_ab.json): dry-run of shipped SMX: deployed .00-.84 -> .62-1.36 of the sibling; no cap breach (max w .30 = BN BTC one step $59); transition fees $0.34 total.
 Open: small:main_bn gross x1.36 its sibling (over-weighting the weakest names) -> watch vol in SMXB c / 30 d. CLOSED OPEN.

## TLQP TLQ2 precheck (think-through 15:1x UTC 11-28, before any run)
Source: TLQ (top10 in the lam1 blend: 2026 1.99 vs 1.47, 2025 tie), TLQ c (explore years with slow .33: 1.20 vs PRB2's own number), TLX (Binance held-out fails: HL-specific).
 Form a would repeat TLQ b/conf: skipped. New: (d) top10 inside the SHIPPED main config (blend_nested slow_lam .33): does top10 still add once PRB2 already cut the slow legs' turnover?
 TLQ said they overlap by half. (c) phase: HL daily bars close at 00:00 UTC; if top10's 2026 gain sits on one anchor it is noise. Unstated: thin HL names are fresh listings
 (decaying float, squeezes): top_n 10 removes them from tsmom but listing_short still trades them, so the book keeps that exposure through the other leg.
 Change my mind: top10 >= top20 with slow .33 in >= 3 of 4 years AND on >= 3 of 4 anchors -> the WF is worth its DSR count; else TLQ2 drops to low.
TLQP d/b (is3_tlqp.py, tlqp_d.json): in the shipped slow-.33 main, tsmom top10 vs top20 1.63 vs 1.49 pooled 2023-26 (3/4 years, 2025 -.10), 2x cost 1.43 vs 1.28; known answer lam1 = TLQ.
 Overlap with PRB2 ~full (top10 lam1 1.61 ~ top10 slow 1.63). a skipped (dup TLQ), c skipped (HL hourly 228 d: listing ages/lookbacks broken). CLOSED OPEN -> TLQ2 WF = shipped vs top10 slow .33.

## SMV rounded twins' gross/vol tail (think-through 15:1x UTC 11-28, before any run)
Source: SMXR (today small:main_bn gross x1.36 its sibling), SMD b (full-sample vol equal: HL 24.9 vs 24.3 %, BN 23.4 vs 23.5; mean deployed .62-.89). Rounding adds gross when many
 targets sit between half the minimum and the minimum (each is pushed up by up to x2) and removes it below half; on average they cancel, but on a day with a wide, flat target book
 (BN: flow spreads 5 % caps over hundreds of names) the push-ups dominate. Unstated: what a $200 trader fears is not the mean but a stretch of weeks at 1.5x the risk he chose.
 Change my mind: p90 of the 60-d rolling vol ratio > 1.25 on either venue -> a general gross cap; else no change.
SMV a/b/c (is3_smv.py, smv_ab.json): rounded-$200 vs $1,000 gross p90 .95 HL / 1.01 BN (>1.25 on 1 day each); 60-d vol ratio p90 1.20/1.19 (bar 1.25), yearly peaks HL 2024 1.53, BN 2025 1.31.
 The tail is concentration (few minimum-sized names), not gross: no cap. CLOSED DEAD (no fault).

## PRBF power of the PRB2-F forward judge (think-through 16:5x UTC 11-28, before any run)
Source: PRB2 WF (slow .33 OOS 1.82 vs 1.45; costs 8.6 -> 5.5 %/yr full period), backlog PRB2-F (KEEP if slow fees+slippage/day <= 75 % of lam1's AND t(slow - lam1 daily P&L) > -1 at >= 30 d).
 The two shadows hold the same names most days, so the difference series is far less noisy than either book; but the slow legs lag, so the difference is autocorrelated (t needs HAC).
 Expect: mean gain ~ (1.62-1.33) x 25 % vol ~ 7 %/yr = ~2 bp/day against a diff sd of maybe 30-60 bp/day -> MDE at 90 d ~ 6-12 bp/day: the P&L clause cannot confirm, only catch a disaster.
 The cost clause is the one with power: costs are deterministic given turnover, but turnover itself swings with regime (trend reversals make both trade), so the 30-d ratio has a spread.
 Unstated: live slippage is the thin-book spread, not the model's; the ratio is self-normalising (same names, same spreads), so model error mostly cancels. Change my mind: if >= 20 %
 of 30-d windows fail the 75 % cost clause in backtest, the clause is a coin flip and needs a longer window (restated, no gate change).
PRBF a/b/c (is3_prbf.py, prbf_ab.json): slow vs lam1 corr .976, diff sd 31.9 bp/d, mean +1.39 bp/d (+5.1 %/yr, HAC t 1.57, + in all 4 years); MDE 7.1 bp at 90 d = 5x the gain.
 Cost ratio .655, fails <= .75 by chance 23/18/13 % at 30/60/90 d. Backlog PRB2-F restated: 30 d disaster check, verdict at 90 d. CLOSED OPEN.

## FLXF FLX2 precheck (think-through 16:5x UTC 11-28, before any run)
Source: FLX (2025-26 flow gross = funding 18.9/15.4 %/yr + price +4.7/-1.6), FLP (funding overlap with blend per coin .85). Mechanism: 3-d taker-buy imbalance is highest where
 crowds chase (longs pile in -> funding high); flow is LONG those (continuation), so it should PAY funding, not receive it. That FLX found funding income means flow is often short the
 crowded names or long the negative-funding ones: i.e. late in the move the imbalance has turned (sellers absorbing) while funding still lags. Unstated: the trader he imitates
 never looks at funding; a funding-neutral flow tests whether the flow information has price content of its own. Frozen (iii) = residualise the score on trailing 7-d mean funding.
 Change my mind: if (iii)'s price part is ~0 in 2021-24 too, flow's 'price edge' was always partly funding-correlated price drift, and FLX2's 'flow-without-funding' arm is moot.
LV1S: closed as a duplicate of LV2 (funding filter = random drops) / LVH (universe) before any run; the refill had read the stale backlog LV1 line, not findings. Backlog LV1 corrected.
FLXF a/b/c/d (is3_flxf.py, flxf_abc.json, flxf_mix.json): flow@bn gross 50 % on the funding-receiving side (+10..26 %/yr funding, small price); paying side = the price edge (2021/23/24), ~0/-7 in 2025/26.
 Frozen (iii) resid_f7: SR .77 (vs 1.06), corr blend .17 (vs .40), price 2025/26 +12/+3; .5/.5 mix with blend 1.75 = 1.75 (blend alone 1.66). Paying-only dead (.09). CLOSED OPEN -> FLX2 arm (iii).
