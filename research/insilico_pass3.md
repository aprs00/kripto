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
