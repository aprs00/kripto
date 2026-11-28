# InSilico third pass: the full test programme

Owner, 2026-11-22: *"test everything out ... write up a thorough plan to fully test everything ... on the server in few iterations so
that we do not use up our entire token limits ... run this stuff every 12 hours ... when i say thorough test, i mean it!"*
State lives in `research/insilico_queue.json` (tool: `python -m scripts.insilico_queue status|show <id>`), evidence in `research/is3/`.

## 1. What went wrong before (audit 2026-11-22)
Pass 1: one literal form per rule. Pass 2: a good plan of which about half was run; the rest was dropped without a word and families were
still called dead. His main method (bars built on distance, "real fucking edge", tg:103–107) was never tested and not even catalogued; his own
indicator guides never became rules; nothing was tested as a filter or in combination, although he says he never trades one signal alone.
So now: every planned form is a queue entry, the tool refuses a verdict while one has no outcome, a skipped form is not a failed one, and
DEAD needs three forms with evidence files. 35 items, 137 forms at the start; items and forms may be added (`add-form`, S1), never removed.

## 2. How every form is tested (`research/studies/is3_lib.py`; the same battery for all)
| # | test | what it protects against |
|---|---|---|
| 1 | null check on sign-flipped data (real volatility and volume, coin-toss direction; 20 copies) | look-ahead and biased measurement: must earn ≈ 0 |
| 2 | causality check (cut the future off, earlier events must not change) | look-ahead |
| 3 | matched baseline: same coin, same size of past move (or placebo level, same distance) | "dips bounce anyway", "any level is revisited" |
| 4 | day-block bootstrap: mean, 95% CI, p, p against baseline | 50 coins on one crash day counted as 50 facts |
| 5 | minimum detectable effect (80% power) | calling "not significant" a failure when the test could not have seen it |
| 6 | ex-top-3-days, per year, per side, share of coins positive | a few lucky days, one regime, one coin |
| 7 | cost ladder 0 / 8 / 13 / 26 / 80 bp round trip (80 = crash fills), maker and taker, own volume-scaled cost, 1–5 min delay where intraday | edges that exist only on paper |
| 8 | dose-response: 3+ strengths of the signal | thresholds picked by luck: a real effect grows with the signal |
| 9 | held-out time (2024–25) and held-out coins, pre-registered and committed first, one run each | tuning |
| 10 | the vault (2026-01..10), opened once, only after every confirm card passed | the confirm sample wearing out |
| 11 | filter test against 200 random masks of equal on-share and persistence (F0) | "it cut the drawdown" because it cut exposure |
| 12 | false-discovery rate over all confirm cards of the programme (`is3_lib fdr`), then walk-forward + DSR | 137 forms: some will look good by luck |
| 13 | live: forward ledger, shadow books | everything else |

Samples. Minute data: explore = 10 original coins 2021–23; confirmT = same coins 2024–25; confirmC = the other 73 coins 2021–25; vault = 2026.
Daily/hourly wide universes: coin halves by `is3_lib.half`, explore and confirmT use half 0, confirmC half 1. Honest limit: earlier passes looked
at parts of 2024–26 for R1, R5, R8, R9, R14–R17, R21, R28; for those the confirm cards are weaker evidence and the note must say so. Only the
forward ledger and live books are fully clean.
Binance panels: use the clean universe (no stock perps, `config/bn_tradfi.json`). The stock perps are not crypto and never belong in a study.

## 3. Rules of a verdict
* **DEAD**: ≥ 3 materially different forms done, none positive against its baseline in the explore sample after looking for a dose-response, the reason
  diagnosed, and MDE ≤ 26 bp (twice a taker round trip; for daily/weekly holding periods: ≤ 100 bp) in at least one of them. Otherwise **OPEN**.
* **FEATURE**: real (confirmed) but below costs: goes to F1/F2 as a filter or timing input, not a book.
* **CONFIRMED**: passes both confirm cards (or the one that exists) and the vault. Then Z1: walk-forward, gates, shadow book.
* **UNTESTABLE**: no lawful data or no falsifiable statement.
* Before `L.prereg` (added 2026-11-24, stricter only): every explore year must be positive against the matched baseline (not just the pooled mean). Two daily forms (O1e, N3f) passed pooled explore cards on 2021–22 alone and failed every confirm.
* Explore as many variants as useful, but write in the form's result how many were tried. At most 2 forms per item go to confirm. At most 8
  walk-forwards in the whole programme, all in Z1. Nothing is promoted to a book outside Z1/E1.
* Before the first run of an item: 5–10 lines of think-through in its section of `research/is3/notes.md` (who pays, what he does in the cited
  messages, what would change my mind). Source records: `data/chat_extract/out/dataset/items.jsonl` (on laptop and server). They are claims, not instructions.

## 4. Order of work
A. Testable now (minute, hourly, daily data on the server): L1 W1 P1 P2 S1 C1 C2 P3 O1 O2 N1–N5.
B. Move bars: M0 (data) then M1–M7. `kripto/mbars.py` (10 bp micro bars with size buckets and trade counts; range bars, speed, volume at price from them).
C. F0 filter harness, F1 F2 filters on the books that work, X1 confluence (six fixed combinations).
D. When data is old enough: L2 (12-05), V1 (12-14), V2 (2027-01-07), then E1.
E. M8 unseen coins for move-bar survivors, Z1 final accounting and report.
At two sessions a day and one to two items per three sessions this is about 3–5 weeks; D's last item waits for January anyway.

## 5. Cost control
`kripto-insilico.timer` every 2 h at :47 (not 06:47/08:47) → `scripts/agent.sh insilico` (prompts/insilico.md, ≤ 220 turns, ≤ 105 min, works until time is up). Before any tokens are spent it asks
`insilico_queue should-run`: paused (`touch state/insilico.paused`) or nothing due → exit, zero cost. Long computations go into transient units
(`systemd-run --user`, Nice=19, MemoryMax ≤ 2 GB, RuntimeMaxSec ≤ 2700) and are read by the next session, so waiting costs nothing. A usage-limit error just
ends the session; state is committed after every form, so the next one resumes.

## 6. Results
One line per closed item (full numbers in research/is3/, conclusions in findings.md):
* L1 liquidation fade (taker after the reversal bar): OPEN. Real, every year +, but a late taker entry does not survive 30 bp worse fills; both confirm forms missed the bar.
* W1 weekend / CME: OPEN. Weekend prices do return to Friday's level more often than on weekdays (43% vs 29%), but the trade was only paid in 2021.
* T1 resting bids 30 σ under the price: CONFIRMED for the causal top-20 only (+187 explore, +259 2024–25, +203 bp 2026 vault, gross per fill; net of own costs +178 / +250 / +194). Any-coin version refuted (T1g). Needs the resting fill; −34% intraday mark at 10% size on 2025-10-10. Next: E2.
* E2 ladder book: OPEN until live fills prove the fill model. WF OOS 1.94, gate passed, live since 11-23; worst minute mark −17% at 5%/order, so size cut to 2.9% (−50% on a 17-fill batch stays above the 25% kill); loss caps useless; not crash-correlated with the main_bn mix.
* S1 sources re-read: closed as a reading item. 33 forms added, 11 corrected; 11 rules had been flattened when first coded (R1 R3 R4 R7 R14 R18 R19 R23 R24 R29 R30). New evidence source: 107 dated 2020 levels (T2e).
* S2 every picture and video opened by eye: closed as a reading item. 253 images, 21 video sheets, 140 truncated records; 0 of the stored descriptions contradicted. 6 forms added or sharpened (M2f, C2g, P1g, M3e, M4a, M1c), 2 data-collection items (backlog W2, L1p).
* T2 forensics of his own examples: OPEN. His capitulation days look like any big down day (all-buckets-negative is the base rate on 54% of them); unseen analogs = matched down days; his 85 dated 2020–21 levels do worse than distance-matched placebo lines (−28 bp at 60 min, p .03) and are not touched more often. Underpowered (MDE 353 / 42 bp).
* T3 context model after a climax: DEAD. The 'spring' (how much of the fall comes back in 3 min) does not predict bounce strength; a strong spring means the bounce is already used up (−11 bp vs matched, p .02). A ridge model on 22 features has real OOS skill (IC +0.075) but it only rediscovers 'fade dumps, ride pumps' and bets bigger on volatile events.
* T4 exits as decisions: OPEN (MDE rule), practically settled: on the live ladder fills every 'take it and run' exit loses to the 61-min timer (−3 to −94 bp; 3 of 4 p < .01). The live book keeps its timer.
* T5 1-min bounces/continuations by context: OPEN. Ordinary shocks are noise (+2 bp, no context helps); absorption bars do not bounce (claim reversed); up-spikes >= 8σ with breadth continue (confirmed on coins p .009, not on time p .075, tail-driven).
* P1 gap fill: DEAD. The reverse is true: the next day/hour trades more where the prior traded most (+2.5 / +1.2 pp vs mirror) and avoids its thin zones; valleys, LVNs, delta gaps = placebo.
* P2 balance laws, session profiles, poor lows, fat nodes: DEAD (12 forms). Real balance/IB edges, naked POCs and single prints are broken or skipped slightly MORE than placebo levels; 80% rule = random walk (pass-2 bias corrected).
* C1 calendar: OPEN (MDE rule), practically nothing: 0 of 176 cells survive FDR; FOMC / first-of-month / turn-of-month +60..+220 bp/day at p .05-.07 but below their MDEs; lunar flips sign.
* C2 time of day: OPEN only for the Friday 16–20 NY window (+21 bp, MDE 38, goes to FF1); kill zones, filler give-back, illiquid-hour fades, same-clock persistence, Monday TWAP: dead.
* P3 naked / composite POCs: DEAD. Not magnets (touched less than mirror levels), no first-touch reaction beyond a generic bounce (+16 bp vs matched mirror, p .09, anti-dose in node fatness).
* O1 oscillators: DEAD. RSI adds nothing beyond the past return; 'back to 50' is followed by trend resumption, not reversal; the ladder-by-RSI filter passed explore and failed confirmT (2021 artifact).
* O2 his own indicators (VZO, Hull, Leledc, camarilla, Fisher, channels, Crayons H/invalidation): DEAD. None adds to the past return; VZO alert end and invalidations are wrong-way. Feature idea: a failed new high weakens trend continuation (F2).
* N1 round numbers: DEAD. Hundy roll, overshoot-and-return and first-touch reactions = placebo levels (round levels, if anything, are run through slightly more).
* N3 tape behaviour: OPEN (as features only). Absorption passed explore and failed both confirms; shrinking swings / failed new highs mark a tiring trend (for F2), never a reversal trade; the rest nothing.
* N4 lead-lag: DEAD. Thin coins do not lead BTC, decoupling is no canary; dumps are sharper than pumps at >= 8 sigma (true; the ladder's raw material).
* M1 rotation momentum on move bars (R3): DEAD. One-voiced flow runs (all size groups green) carry +2 bp vs within-day matched bars (1/7 of costs, anti-dose); the strong-looking reversal after one-voiced bars is torn-book bounce.
* N2 spot vs perp delta (R13): OPEN. Spot-led rallies earn what same-size rallies earn and spot delta adds nothing to perp flow (MDE 19 bp); his narrow "negative perp delta = spot hedges" case points his way (+62 bp/1 d, p .22) on too few events.
* M2 order velocity x10 (R7): OPEN. Count jumps/drops of 5-20x are everyday noise at his bar size; the one survivor (a burst on a slow down bar at the 24 h low) replicated in direction but 85% of it is three crash days, i.e. the liquidation fade.
* M3 mousetrap / absorption / trapped cohorts (R4, R10, R12, R35): DEAD. Every version equals its placebo or matched baseline; large sellers below a level are informed, not trapped.
* F1 filters for flow / xsmom: OPEN (nothing usable). 8 forms; the one explore pass (1-day short block after cascade days) failed its 2024–25 confirm; value location, round numbers, poor extremes, size breadth = random masks.
* F2 filters for tsmom / blend / listing shorts: OPEN (nothing usable). No execution-hour tilt (trading later than the close costs +1..+13 bp per unit traded); volume-on-rally, value location, failed-new-high trims = random masks or worse; flat into FOMC passed explore, failed its 2024–25 confirm; only blend-only 'no new shorts after a flush' cells pass explore (the F1g family).
* M4 capitulation (R1, R2) with adaptive buckets, in trends, pitstops: OPEN (MDE rule only). Every form at or below its matched baseline, the strongest cells the opposite sign: one-voiced selling continues.
* M5 range -> impulse -> range retest (R19) on range bars with a queue-volume fill ladder and placebo levels: DEAD. 6 forms, MDE 1-9 bp: the old range high, the range's VAH/POC, his A target and average-candle target, thin coins = placebo levels at every fill rung; queue fills are adversely selected; strong-pressure retests are worse (his skip rule), the rest still loses.
* M6 trend systems on move bars (R33): DEAD. Range / TR / zigzag / P&F / volume / delta bars as the clock: +3-7 bp/trade more than hourly tsmom at matched turnover (intraday continuation after a range-bar close), 1/3-1/2 of a taker round trip, gone at low turnover; double reversals at a level = single ones.
* M7 delta at price / exact profiles (R10, R14-R16): DEAD. Exact aggTrade profiles: outlier delta cells, absorption at the POC and stacked footprint imbalances = placebo / neutral zones; the exact-POC first touch beats its mirror by ~10 bp (as P3), below costs, spent within 5 min.
* M8 survivors of M1-M6 on unseen coins: UNTESTABLE (nothing survived; M2b failed confirmT). The unseen-coin micro-bar sample stays unspent.
* X1 confluence: DEAD. Six pairs of his signals (sweep at a prior low, capitulation at a POC, single print + absorption, Sunday empty move vs collar, pinned RSI + node break, velocity climax at a round number) each equal their placebo or single-signal baseline; the Sunday pair points the other way (continuation).
* LD2 ladder flush-batch control (from LD1, not an InSilico rule): OPEN. A cap on open positions is a size effect (tail no better than a return-matched base, 74th pct of random thinning); the inventory skew k=30(1+0.5 n_open) has better SR in 5 of 6 years (explore +0.39, confirm +0.12 < pre-set +0.2) and cannot see a flush batch from a flat book. Live ladder unchanged.
* E2B execution clock at the CME break (from E2): OPEN. Deciding blend_nested@bn at 16/20 UTC instead of 00 costs nothing (anchor SR 1.57-1.87 = phase noise), but deferring its sells over the break (+5.3 bp/unit, t 1.05) is matched by 3-h deferrals at other anchors; not adopted. HL hourly too short until 2027-04-14.
* FF2 friday_follow without the survivor long (from FF1): OPEN. No coin-specific part (excess move -3 bp, shorts-only hedged negative); the effect is the alt universe's own Friday move continuing into Saturday (explore +65 bp t 3.1 vs Thu/Sat placebo), confirm +32 bp t 1.2 and ~0 in 2026: fading, below the bar.
* W3B Sunday fade as a BTC+ETH-only overlay (from W3): OPEN. 2020-23 the two deep coins show no Sunday fade (-13 bp per Sunday, t -0.3); W3's effect is an alt / 2024+ one, so the cheap overlay has no explore support.
* W3S Saturday fade on BTC+ETH (data-mined in W3B): OPEN by vocabulary, effectively chance: explore placebo cell +43 bp t 1.9 -> preregistered confirm +1.8 bp t 0.07.
* LV2 lowvol minus carry (from LV1): OPEN. Excluding negative-funding shorts = random exclusion in 2020-23 (the crowded-short squeeze is a 2024+ thing); funding-adjusted ranks change nothing. HL leg check: SR 0.70 since 2023, all from 2025, 0.23 without its best 10 days: fragile.
* FC1C HL-vs-Binance funding gap as crowding (from FC1): OPEN. With HL funding backfilled to 2023-05 the gap short is weak and one-regime (t 1.4), as a listing_short filter it points the wrong way and its data-mined reverse misses the confirm (92nd pct), and its slope adds nothing to fspread_hold (slot-bound, all carry). The gap is worth harvesting as carry, not reading as a price signal. Side fact: fspread_hold replicates on the unseen 2023-05..2024-06 window (SR 14, 26.6%/yr at gross 2.0).
* LD3 ladder fills in liquidity holes vs flushes (library N14): OPEN. 2021-23: hole fills (high fill-minute Amihud) bounce +84 bp more from t+1 (dose, not depth), but from the ladder's own quote there is no gap; the taker add-on at t+1 reversed on 2024-25 (-27 bp, MDE 180). Nothing for the live ladder.
* T9B alpha-decay of the live books' trades (library N8): DEAD as a cost. Daily-book curves are flat for hours (1 h late <= 1.3 bp per unit turnover on BN 2020-26, alpha accrues over 24-48 h); live fills 11-13 min late, side-balanced drift ~0-2 bp. Late runs are harmless.
* L6V range/HAR vol forecasts for vol targeting (library N6): OPEN. ewm20 per-coin variances beat the 60-d sample (QLIKE -10%) and track the vol target 9-23% better in 6/6 book x sample cells, but the pre-registered xsmom confirm failed (TE -12%, SR -0.21); HAR over-forecasts. Small consistent risk gain, a design question for research.
* T8R market regime -> live BN books (backlog T8): DEAD. 6 states x 3 books on bnall 2021-23: pooled terciles are year dummies, within-year doses flip by year, the best causal filter (halve flow in high BTC vol) = random masks. The books are vol-targeted already.
* LS1 listing_short HL with the backfilled funding (T2b a): OPEN, check passed. Coverage 56% -> 95%; SR 1.44 -> 1.36, the shorts pay 7-10%/yr funding in 3 of 4 years but not fragile (.82 without the best 10 days); per event the median listing pays the short, a squeezed tail costs the mean; 2026 cohort worse (-15% funding by d90).
* LV3 lowvol by idiosyncratic vol (LV1 b): DEAD. Idio vol = total vol in alts (rho .93); idio ranking, idio-beyond-total and the low-idio long leg all fail 2021-23. High-vol coins lose in the median (-90 bp/day hedged) but not in the mean: the right tail pays the short back.
* LSF listing_short squeezed-tail exit (from LS1): OPEN. Reversed on bnall 2021-23: shorts paying heavy funding do fine; shorts receiving high funding (pumps) lose in the mean only (2021); the reversed exit rule = random masks. HL held-out not spent.
* FSM fspread_hold with maker legs (T9 revisit): DEAD. For a same-asset pair the move that fills one leg is against the other: both-maker costs more than taker, maker-one-leg + hedge loses 9-11 bp per event.
* X1H fspread_hold churn / exit band (from X1C): OPEN. Short trips (< 14 d) appeared in 2025-26 and lose ~0.7 %/yr; a wider exit band halves turnover but loses carry: +0.34 %/yr in 2025-26 (SR 3.6 -> 4.3), worse in 2023-24; under the +0.5 bar. Forward re-check of the frozen x .05 in 2027.
* LVH lowvol HL vs bnall: OPEN (explained). The universe, not the venue or period: bnall restricted to HL-listed coins SR .90 vs full bnall .05 (same dates); Binance-only small caps as shorts pay -92 %/yr funding per unit and lose -12 %/yr. New question: HL-listed universe filter for BN books' short legs.
* HLU1 HL-listed universe filter for BN books' shorts (from LVH): DEAD. BN-only names are the momentum/flow books' best shorts (2023-24); blocking them or extreme-funding shorts = random masks or worse. The lowvol squeeze tail is lowvol-specific.
* X1V fspread_hold@pair live vol vs backtest: OPEN (explained). The 10 live days were a high-vol window for the hedged book (98th pct; the backtest's own vol 3.1 %/yr there too); mark definitions and leg timing are minor. Live holds different pairs from the backtest (4 of 7 overlap).
* BNH HL main book dependence on lowvol: OPEN (kept). Without lowvol the HL blend is SR 1.30 vs 1.34; lowvol was chosen out-of-sample in Jan 2025 and then paid in 2025; listing_short carries the book.
* L3S slippage model vs live book walks: OPEN (measured). The backtest's slippage is about twice what 2,363 live paper fills paid walking the real order books, with the right shape; costs are conservative by 0.6-2.2 %/yr. Kept.
* X1U pair book on the live universe / cold start: OPEN (explained). Same return as research when held legs are kept; the live pairs differ because the live path started in late September; a restart costs ~0.3 % once and converges in two months.
* LSV listing_short vol estimate for new coins: OPEN (harmless). New coins' risk is under-estimated about 4x in their first week, so the book runs ~1.3x its vol target; fixing it lowers the Sharpe because the youngest names pay most; the monthly main_scale already corrects the vol.
* FST Binance funding settlement drift: DEAD. Prices do not move against the paying side around 00/08/16 UTC (0.5 bp detectable); deferring payer-side buys past the settlement would save only 0.1-0.2 %/yr.
* KSW kill switch: OPEN (measured). The -25 % stop would halt a good main book about 1 time in 8 over two years and a dead one 3 times in 4; it should scale with the vol target (proposal KS1 for a research session), and the pair book needs a per-account guard.
* PBT pair entry timing by the price basis: OPEN. A pair opened when the shorted venue is rich makes ~30 bp more per leg than one opened when it is cheap, but waiting for a good basis adds under 0.5 %/yr and is only partly visible at the live trade minute.
* HLI HL book with listing_short idle: OPEN (explained). Hyperliquid now lists about one qualifying coin a month (five in 2025), so the HL book's main leg was empty on 21 % of 2026 days; the book then runs on its two weaker legs. Leaving that third in cash looked slightly better, but random day masks do the same (F0C): it is only less exposure.
* TSH tsmom leg of the HL book: OPEN (kept). It is a trend leg on altcoins that pays in crashes and big rallies and bleeds slowly in between, and it hedges the listing shorts' squeeze days.
* BNB main_bn legs: OPEN. Both halves contribute about equally, but in 2025-26 all of the Binance book's profit is funding received; the price part is flat or losing.
* FLD flow@bn signal: OPEN (decayed). The taker-flow signal predicted the next day in 2021 but has been close to zero since (except the most liquid coins in 2022 and 2024); the book's recent profit is funding. Flagged for the live retirement check.
* VRT venue routing by funding: OPEN. Holding the HL book's longs on Binance would have saved 7-14 %/yr in 2023-24, but the funding gap between the venues has closed (about zero net in 2025-26).
* CRB carry legs by funding level: OPEN. The Binance carry book earns its funding almost entirely from the most extreme names (crowded shorts paying 1-2 % a day); cutting them is worse than random: that risk is what it is paid for.
* LSB Binance listing shorts: OPEN. The typical new Binance perp still falls 20-40 % against BTC in its first two months every year, and Binance lists about five a month in 2026 (HL: one); a few squeezes set the average. Backlog LSB2 for a walk-forward inside the Binance book.
* LSP Binance listing shorts as a book: OPEN. Shorting every new Binance listing equally loses to a few squeezes (Sharpe 0.18, negative in 2025-26; the 2023-24 profit came from the BTC hedge). LSB2 waits for a squeeze control.
* SQZ squeeze predictors for listing shorts: OPEN. Listings that already trade far above their post-listing low are twice as likely to squeeze, but skipping them does no better than skipping random shorts.
* FRG funding regime: OPEN. When the market's typical funding rate is low (as now) the pair book earns less and the Binance carry book collects more funding next month, but the Binance book's net return does not follow.
* KSA the pair book's two accounts: OPEN. Held in two separate accounts with no transfers, one of them would almost surely lose half its money within two years (the other gains the same); moving money between them whenever one falls below 70 % of the other (about 14 times a year) keeps the worst account at -29 %.
* CRS carry's crowded-short longs: OPEN. The ones whose funding is fading tend to keep falling a little, but skipping them changes nothing at the book level.
* TFF HL trend longs with expensive funding: OPEN. Even the trend longs paying ~95 %/yr funding earned more than that in price in 2023-24: no filter.
* PAC live pair accounts: OPEN. In its first two weeks the live pair book's Binance side lost 27 % and its Hyperliquid side gained 28 % (about half that at the real-account size): normal for the backtest, and a money transfer between the accounts would already have been needed.
* OVL the three main books together: OPEN. They are nearly uncorrelated (0.05-0.08) and do not share their worst days; holding the HL and Binance books side by side would have roughly halved the drawdown in the backtest.
* HLD HL listing drought: OPEN (explained). Hyperliquid listed 51 new crypto perps in 2025 and 8 in 2026; its growth went to stock and index perps on builder exchanges, which this project does not trade. Our data is complete.
* XST Binance blend's third leg (xsmom vs tsmom): OPEN. Trend (tsmom) would hedge the carry legs' bad days better and earn a little more, with slightly deeper drawdowns; the refit rule decides.
* FLB plumbing check of an IC oddity: OPEN (verified). The tools pass planted-signal tests; the odd number was a real effect of a few large moves, not a bug.
* FLQ flow on the 10 most liquid coins: OPEN. Worse than the live 30-coin version (Sharpe 0.67 vs 1.58 in 2021-23); flow@bn stays flagged.
* LSW Binance listing shorts weighted by inverse volatility: OPEN. A small Sharpe gain (0.24 vs 0.18) that random reweightings match, worse in 2023; the squeeze losses come from names that did not look volatile beforehand. Listing shorts stay on Hyperliquid only.
* PRB partial rebalancing of the Hyperliquid main book (trade a third of the gap to target each day): OPEN, promising. It halves trading costs and beat full rebalancing on unseen 2025-26 data (Sharpe 1.94 vs 1.86), but only for this slow book at $1,000; it hurts the fast Binance books and the $200 account.
* HBL where the Hyperliquid listing-short profit comes from: OPEN. The book really is market-neutral (the 2024 'profit from the BTC leg' is just how a hedged pair books its gains). New coins move about 1.35x Bitcoin, not 1x, so the hedge is slightly too small; correcting it costs a little Sharpe (1.71 vs 1.77 on 2025-26) but removes a hidden short-market bet.
* PRL partial rebalancing of only the slow parts of the Hyperliquid main book (trend and low-volatility legs move a third of the way each day, listing shorts trade in full): OPEN, the most promising cost saving so far. On unseen 2025-26 data Sharpe 2.10 vs 1.86, trading costs 7.0 -> 4.0 %/yr, and it holds at double costs and at the $1,000 minimum-order band; it does not work for the $200 account.
* HBM the same hedge question for the Binance books: OPEN (no exposure). They almost never hold coins too new to have a measured beta (under 0.2 % of positions).
* PRN the same partial rebalancing on the Binance blend: OPEN (does not transfer). The cost saved is matched by signal lost; there the trading is real signal.
* TSB a fixed no-trade band on the same legs instead: OPEN (weaker). It saves less and lost in 2024, but it produces far fewer orders below the $10 minimum, so it is the fallback if the partial version runs into minimum-order problems live.
* VTS resize positions less often when the volatility estimate wobbles: OPEN (nothing there). It removes no trading at all; the costs come from the strategies' own position changes.
* SML what works in the $200 Hyperliquid account: OPEN. At $200 the $10 minimum order freezes almost every position change, so yearly results there are mostly luck; no simpler book could be shown to be better. The live $200 twin is the evidence that counts.
* PRD how sensitive that cost saving is to its one setting: OPEN, robust. Any rebalancing speed between 15 % and 75 % a day beats full rebalancing in all four years, and both legs contribute.
* TSN where the trend leg's trading comes from: OPEN. It is the trend signal's own day-to-day drift. An older result saying that smoothing it destroys the edge does not hold on today's data, so that idea is reopened.
* CPB a no-trade band for the fast Binance books: OPEN (fails). Skipping small changes costs them far more signal than it saves; their trading is the signal.
* CMB the two Hyperliquid fixes together, under real minimum-order limits: OPEN. They add up without interfering. With the $10 minimum order at $1,000 the partial-rebalancing version still wins in 3 of 4 years (2023 is the weak one) and beats the band alternative.
* PRX the same cost saving tested on Binance coins it was never tuned on: OPEN, it does not carry over (Sharpe 0.73 vs 0.81 in 2021-23, a little better in 2024-26). The Hyperliquid gain may be real but is specific to that venue; only the forward paper record can confirm it.
* HTN why the cost saving works on Hyperliquid but not on Binance: OPEN, explained. The trend leg trades just as much on both venues, but each trade costs 8-22 bp on Hyperliquid's thinner coins against about 6 bp on Binance, so trading less pays off only where trading is expensive.
* HLF the funding cost of the Hyperliquid main book: OPEN. The Bitcoin hedge pays 2-9 %/yr in funding, but hedging with Ether costs as much and works worse; on a single venue there is no cheaper hedge.
* HLE which Hyperliquid listings fall: OPEN. Only genuinely new tokens decay (about +25 % for the short over 60 days). Coins that already traded on Binance for months do not fall when Hyperliquid lists them (about +1 %). The 2026 drought removed exactly the tokens that carry the edge.
* HLX the same test on Binance listings: OPEN, it replicates. Coins that had already traded on Hyperliquid for months did not fall after their Binance listing (median -5 %, only 10 cases), while genuinely new tokens did (median +36 % for the short). Listing decay is about newly released supply.
* HLB using that as a filter in the actual book: OPEN, it does not help. Dropping the established coins lowers the Hyperliquid listing book's Sharpe (1.21 vs 1.37) and the main book's in 3 of 4 years. The finding explains the 2026 drought but is not a trading rule.
* HFR when the Hyperliquid book pays the most funding: OPEN. It pays more in months when market funding is low (it is mostly short altcoins, and crowded shorts pay then). Funding is low now, so expect about 1.4 % a month of funding cost, against a 0.95 % average.
* LVS the Hyperliquid low-volatility leg by side: OPEN. Its two sides are opposite bets on the market that cancel out. The small price edge is paid away in funding in most years; all of its return came in 2025, when the most volatile altcoins collapsed. Nothing in the shorts' recent returns warns of their losses.
* HSQ the squeeze warning sign on Hyperliquid listings: OPEN. Coins held short while far above their post-listing low lose more than 20 % in a week more often (14 % vs 9 %), as on Binance. But the same coins also decay the most on a typical day, so avoiding them would throw away as much as it saves.
* TLQ the Hyperliquid trend leg's thinnest coins: OPEN. The six least-traded coins in the trend leg's top 20 lost money in 3 of 4 years once costs were counted. Trading only the top 10 did better in 2023, 2024 and 2026 and cost less, but in 2025 it was 0.02 Sharpe short of the default, so the pre-written test failed. It goes to a research session as a candidate, not as a result.
* HFX moving the Hyperliquid book's long positions to Binance: OPEN. Long positions pay much more funding on Hyperliquid (BTC: 24 % a year in 2024 against 12 % on Binance). Holding the longs on Binance would have saved 2 to 9 % of the book a year (about 2 % in 2026). But it needs two accounts, each carrying one-sided risk, so it waits for the per-account risk rule (KS1).
* TLX the same test on Binance: OPEN, it does not replicate. On Binance the less-traded coins in the trend leg trend just as well, and trading only the top 10 did worse in 5 of 7 years. The Hyperliquid result is about its thin coins being fresh listings, not a general rule.
* LVQ where the low-volatility leg's 2025 gain came from: OPEN. It came from shorting many thinly traded, volatile altcoins at once (83 coins, the top five only a third of the gain), not from a few lucky picks. It moves with the listing leg (correlation 0.3 to 0.6), so the Hyperliquid book's three legs are closer to two bets.
* HFY the reverse, the Binance book's shorts held on Hyperliquid: DEAD. Shorts there do earn slightly more funding, but Hyperliquid's thinner order books cost more than that every year. Only one direction helps: Hyperliquid's long positions moved to Binance.
* ERC weighting the Hyperliquid legs by their risk: OPEN. Three quarters of the book's risk sits in its two altcoin-short legs. Reweighting them by recent risk helped in 2023 but hurt in 2024, so equal weights stay. What the book needs is a genuinely different fourth bet.
