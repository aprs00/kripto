# InSilico rule catalogue (mined 2026-11-11 from data/chat_extract, 936 records)

One trader (InSilico / Viscosity Solutions / @insiliconot), BitMEX/Bybit era, 2020-11 → 2025-10. Everything below is **the
author's claim**, turned into a definition that can be proven wrong. Source ids: `tg:<n>` Telegram message, `wa:<hh.mm.ss>`
WhatsApp image (file time), `tpl` decoded Exocharts templates. Two records flagged `exploit_advocacy_do_not_use` were skipped;
the three `describes_manipulation_*` records are used only as descriptions (R11, R39).

Score = testability on our data (0–3) × fit for a $1,000/$200 account (0–3) × author's emphasis (0–3).
**Tested 2026-11-11/12: R1, R4, R19, R21 dead; R5 open (tail events); R22–R24 nothing tradable. Verdicts and numbers: research/findings.md.**
**Audit 2026-11-22:** R3 and R14 are OPEN (their own forms were not run); R7, R13, R18, R26, R29, R30 never tested; second-pass skips listed in backlog IS3.
Status: **PRE-REG** = in research/batches/2026-11-11-insilico.json · **DESC** = descriptive table only (no walk-forward) ·
**BACKLOG** · **NO DATA** · **NOTE** (context, not a rule). Verdicts go to research/findings.md, not here.

## Data map
| need | have | gap → what to collect |
|---|---|---|
| trade-level taker flow by trade size | Binance USDT-M aggTrades, public archive 2020→ (scripts/aggtrades.py → data/bn/tsize, 5-min × 12 size bins) | HL: nothing historical → W1 websocket collector must keep trade SIZE per print, not only buy/sell sums |
| 1-min OHLCV + trade count + taker buy | Binance 1m klines 2021→ (data/bn/klines_1m) | – |
| range ("rotation") bars, trades per bar | not built | second aggTrades pass or W1: emit fixed-% range bars with trade count and size-bucket delta (R3, R7) |
| liquidation prints | none (Binance stopped the public history) | Binance public WS `!forceOrder@arr` (read-only, allowed by HARD RULE 1) + HL positions already collected (T6a) |
| order-book history (pulls/lifts, depth) | HL L2 top-10 hourly since 2026-11-09 | not backfillable; a 1-s L2 stream is the only way (R11); low priority: latency caveat R39c |
| volume-at-price profiles (POC, value area, single prints) | derivable from 1m klines (approx.) or exactly from aggTrades (price not kept in the 5-min buckets) | add price bins to the aggTrades pass if R14–R18 are promoted |
| tweets with timestamps, options (IV, GEX), equities | none | not collected: X terms forbid scraping (HARD RULE 2); options/equities outside the venue set |

## A. Order flow / tape
| id | rule (entry / exit as the author gives it) | author's parameters | data | sources | score | status |
|---|---|---|---|---|---|---|
| R1 | **Daily TSize capitulation.** Split a day's market orders into size groups; if the net delta is negative in EVERY group at the daily close → local bottom, buy. Not symmetric: all-positive does not mark a top. Use closed days only ("it fixes on close"). | 6–7 groups; BitMEX 2021 edges 31k/57k/111k/155k/250k/255k USD; 2022: 12k/34k/63k/118k/156k/301k; examples 53.5k (Sep 21), 45.5k (Sep 21), 40.5k (Jan 22), each rebounded 4–8% in 1–3 days | aggTrades | wa:18.10.55, 18.10.55 (1), 18.10.56, 18.10.57, tg:283 | 3×3×3=27 | PRE-REG `tsize_capit` |
| R2 | **Capitulation inside a trend.** In an uptrend, the pullback day that "spins more delta than at any other point", one-sided, is likely the bottom. | Jul 20 2021: −48M/−20M/−35M/−13M/−19M/−46M/−49M at 29.2k | aggTrades | tg:274, tg:279 | 3×3×2=18 | DESC (delta z-score split of R1 events) |
| R3 | **Rotation momentum / exhaustion.** On range bars, ride while all groups are green; the first bar where all groups turn red after a green run = demand momentum over (exit, expect at least a pause; sometimes an 8 h bleed). Never act on a bar before it closes ("wait until it fully shifts the dominance"). | Range 500 bars on XBTUSD (≈0.43% at 58k), 7 groups, colour grade 8 steps / 90% | range bars from ticks | tg:199–223 | 2×2×3=12 | BACKLOG (needs range bars) |
| R4 | **Mousetrap.** A bar undercuts an obvious range low on heavy volume and closes back above it; on that bar the broad-market delta is negative while large-lot delta is positive (retail chased the break, size did not). Buy as soon as buyers take over; stop under the trap low; shorts' stops fuel the run. | ES example: broad −4,353 vs ≥100-lot +1,369; prints 600–1,600 lots after = stops | aggTrades 5-min by size + 1m bars | tg:169–171, tg:206 | 3×2×3=18 | PRE-REG `mousetrap` |
| R5 | **L-shock (liquidation fade).** High-volume liquidation candle(s), then the first sizeable opposite candle on relatively small volume that swallows the push back: enter at its close. Take half at an intermediate level, half at the origin of the dump; do the round quickly. Works both ways, but "not so much for bearish pivots". | 1-min chart; Feb 15 2021: dump 47,900 → 45,576, targets 46,750 / 47,200 / 47,700 | 1m klines (author: no feed needed) | tg:165–168, tg:173–174, wa:18.10.18, 18.10.25 (1), 18.10.35 (3) | 3×2×3=18 | PRE-REG `lshock` |
| R6 | **A low on thin volume is not a bottom.** Bottoms need volume or time ("90% of the time a few days"); V-reversals are rare. | Sep 21 2021 low 40.0k on a thin tail | daily klines | wa:18.10.26, 18.10.24 (1), 18.10.25 (1) | 3×2×2=12 | DESC (complement of R1: new 20-day lows that are NOT all-negative) |
| R7 | **Order velocity ×10.** On fixed-distance bars, a ~10× change in trade count between consecutive rotations = change of character → reversal or at least consolidation. | 826 → 80 trades at a high; 701 vs ~100–250 at a low (Nov 13 2020, ~0.1% bars) | range bars from ticks | wa:18.10.41 (2), 18.10.42, 18.10.42 (2), 18.10.29 (1) | 1×2×2=4 | BACKLOG (needs range bars) |
| R8 | **Volume on rallies.** A drift up on falling volume keeps going; a volume spike into highs = price ran into sellers (Nov 2021 ATH). A real squeeze needs a sharp volume candle. | none numeric | daily / 1h klines | wa:18.11.00 (1), 18.10.35 (1), tg:286–287 | 3×2×2=12 | BACKLOG |
| R9 | **Empty stop-driven moves are revisited.** A fast move on no volume through a thin book is repricing, not demand. | none | 1m klines | wa:18.10.58, 18.10.23 (1), tg:231 | 3×2×2=12 | BACKLOG (partly covered by minute study G: fade of 4σ moves, dead) |
| R10 | **Conviction / momentum / absorption / exhaustion** vocabulary: big one-sided market orders; market orders overwhelming limits; big orders failing to move price; orders shrinking and slowing. | none | flow + price | tg:168, wa video 18.10.20 | – | NOTE (absorption tested 11-10 minute study: dead) |
| R11 | **Liquidity withdrawal.** Makers pull before FOMC/CPI, on weekends and after liquidations (those orders do not come back) → volatility aberrations; "real alpha is price reaction to pulls and lifts of limit orders". | limits return ≈1 h after the event | L2 history | wa:18.10.30 (2), 18.10.35 (3), 18.10.19, 18.10.54 (1), 18.10.35 (2) | 0 | NO DATA |
| R12 | **Size cohorts.** 1k–10k-contract clips run ≈20× leverage and get liquidated before taking profit; each size group behaves consistently. | 1k–10k vs 5k+ contracts | liquidation prints | wa:18.10.38 (3), 18.10.52 (2), tg:278 | 0 | NO DATA (→ T7 with HL positions) |
| R13 | **Perp delta vs spot.** Most perp shorts are spot hedges: negative perp delta in a spot-led rally is not bearish. | none | spot + perp aggTrades | wa:18.11.00 (2), 18.11.02 (2) | 2×1×1=2 | BACKLOG (low) |

## B. Profile / auction
| id | rule | parameters | data | sources | score | status |
|---|---|---|---|---|---|---|
| R14 | **Fill the gap.** Next day's value forms where the previous day traded least; low-volume nodes and delta gaps get revisited. | daily profiles, VA 68–70% | volume-at-price | tg:29–33, tg:38, wa:18.10.31 (2) | 2×2×3=12 | BACKLOG (L5) |
| R15 | **Previous POC / fat node is better support than the daily open**; the composite POC is a magnet; first touch bounces mechanically. | – | volume-at-price | tg:29, tg:38, tg:44–47 | 2×3×2=12 | BACKLOG (L5) |
| R16 | **Single prints get filled** ("repairman"); session single prints are more reliable than daily ones; a fill is followed by a mechanical bounce. Tails are not single prints. | sessions (UTC): Asia 00:00, London 07:00, CME 13:30, Pre-Close 19:15; 30-min TPO | 30m bars | tg:41–45, tg:80–81, tg:133–134, tpl | 2×2×3=12 | BACKLOG (L5) |
| R17 | **Ten laws of balance.** Accept into a balance → travel to its other side; edges reject until proven otherwise; destination of an imbalance = an older balance's POC; time/volume building at an edge → break. | – | profiles | tg:288, tg:52–57 | 2×2×2=8 | BACKLOG (L5) |
| R18 | Rotation factor ≈ 0 = balanced session; thin non-overlapping legs get retraced, a trend lasts until legs overlap. | R/F −2..+2 per 30-min bracket | 30m bars | tg:253–254, tg:231, wa:18.10.19 (1) | 2×1×2=4 | NOTE |

## C. Passive micro price action
| id | rule | parameters | data | sources | score | status |
|---|---|---|---|---|---|---|
| R19 | **Range → impulse → range.** After a breakout, bid the previous range high (offer the previous range low in a downtrend); the first touch bounces "for at least one candle"; take profit one average candle away. One attempt only. "Rebate harvest starter pack". | 1-min ETHUSDT: range high 2073.9, breakout to 2082.7, bounce +3 to +5 points; target = average 1-min candle | 1m klines | tg:226–234 | 2×3×3=18 | PRE-REG `range_retest` |
| R20 | Small size is the edge: no impact, can farm spread on illiquid moves; at size, price sensitivity becomes the counterparty. | dust → 0.5 BTC claim | – | wa:18.10.32 (3), 18.10.21 (1) | – | NOTE (design principle) |

## D. Calendar
| id | rule | parameters | data | sources | score | status |
|---|---|---|---|---|---|---|
| R21 | **Weekend → Monday reversion.** Makers are off; whatever the weekend did, Monday gravitates back to Friday's "collar" price: on Sunday evening bid/offer the Friday price. Sunday pre-futures-open pump is bait. | Friday reference = CME close (17:00 New York); Sunday reopen 18:00 New York | 1h klines | tg:69–70, tg:134, wa:18.10.59, 18.10.23 (3), 18.10.31 | 3×3×3=27 | PRE-REG `weekend_revert` |
| R22 | **Friday after the US close pumps** ("legacy casino closed", up-only). | Fri 23:00 author's time = 16:00 New York | 1h klines | wa:18.11.03 | 3×3×2=18 | DESC |
| R23 | **Legacy daily break**: weekend-like moves while CME is shut. | 17:00–18:00 New York (author: 00:00–01:00 EET "full stop") | 1h klines | wa:18.11.01 (2) | 3×2×1=6 | DESC |
| R24 | Kill zones: trends that leave a kill zone persist to the next; the rest is filler that is given back. Author: "kinda true but also false". | Asia 19–23, London 02–04, New York 08:30–10:30 (New York time) | 1h klines | tg:66–69 | 3×2×1=6 | DESC (hour-of-day table; minute study 11-10 found nothing) |
| R25 | September: bullish first half, then a crash (Sep 24); Santa rally Dec 18–23 then Dec 24 correction; Chinese New Year; sell in May; equinoxes, lunar phases. | – | daily | wa:18.10.28 (3), 18.11.00, 18.10.24, 18.10.23, tg:98, tg:181–182 | 1 | NOTE (≤ 6 observations each: cannot be tested to significance) |
| R26 | Round numbers: trend into the nearest round level and overshoot ("hundy roll"). | enter 2–3% before, expect +6% | daily/1h | tg:119, wa:18.10.24 (1) | 3×1×1=3 | BACKLOG (low) |

## E. Sentiment, indicators, cross-section
| id | rule | parameters | data | sources | score | status |
|---|---|---|---|---|---|---|
| R27 | Fade clout accounts intraday ("X is dead" = buy, "moon" = sell). | 50–100 large accounts | tweet timestamps | tg:135–159 | 0 | NO DATA |
| R28 | **Unit-price bias.** Retail pumps low-unit-price coins in alt seasons: hold a basket of the cheapest-per-unit coins on top exchanges. | – | bnall daily | tg:235–236 | 3×2×2=12 | BACKLOG (cross-sectional factor, cheap to test) |
| R29 | An oscillator pinned at an extreme means trend, not reversal; the signal is the return to the mean. 3–4 failed reversal signals in a row = continuation. | RSI 70/30; Hull 55 for entries, 180 for resistance | klines | tg:86, tg:91–92, tg:98, wa:18.10.36* | 3×1×2=6 | BACKLOG (low; generic trend-following, already covered by tsmom) |
| R30 | RSI vs volume-zone oscillator divergence on "scam pumps"; fade the first 2 candles after a MACD cross. | – | klines | tg:90, tg:100 | 3×1×1=3 | BACKLOG (low) |
| R31 | Vanna/charm: heavy put buying with no follow-through → IV compresses → dealers buy → up. FOMC: IV ramps in, crushes after. | – | options | wa:18.10.28 (2), 18.10.30 (2), tg:282, tg:285 | 0 | NO DATA |
| R32 | BTC = high-beta SPX; decoupling is a canary. Inverse-contract convexity makes dumps sharper than pumps. | – | equities | tg:114–116 | 0 | NOTE (inverse contracts no longer dominate: regime changed) |

## Caveats the author states himself (they bound every test here)
* (a) Venue: BitMEX / Bybit-inverse / Kraken / Bitfinex give "cleaner" flow than big retail venues; TSize is "exchange sensitive"
  (tg:274–275, tg:284, wa:18.10.34). Our data is Binance USDT-M, the noisiest venue by his own standard.
* (b) Intraday edges cannot be mechanised without constant re-fitting to volatility (tg:95 audio); tools are not strategies.
* (c) A retail view of the book is stale next to co-located players (wa:18.10.30).
* (d) Size groups are fitted per pair from the recent size distribution ("AI levels", 1 day back); ours are fixed USD edges.
