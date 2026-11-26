# InSilico rules, second pass (handoff from the 2026-11-11/12 interactive session)

You are continuing the InSilico rule research in /home/ploutos/kripto (laptop; the chat archive
`data/chat_extract` exists only here). Read CLAUDE.md and docs/design.md first: every rule applies.

Do not use the brainstorming skill: the owner does not want to be interviewed. The thinking is yours to
do, in writing, in `research/insilico_pass2.md`.
Stop after the think-through for the first three rules and show it to the owner before testing anything.

## Why this session exists
The owner judged the first pass (2026-11-11/12) as giving up too early, and he is right about how it was
done: each rule got ONE literal mechanical formulation, on ONE venue (Binance USDT-M), as a stand-alone
always-on strategy, and was called dead when that one version failed. "Dead in that form" was recorded as
"dead". This session is the second pass. Its job is to find out whether the IDEAS are dead, not whether
one translation of them is.

## Read first (in this order)
- `research/insilico_rules.md` (32 rules, sources, data map)
- `research/findings.md`, section "InSilico rules", plus the two newest cross-cutting lessons
- `journal/2026-11-11.md` and `journal/2026-11-12.md` (interactive sections)
- `research/batches/2026-11-11-insilico.json` (what was pre-registered and how)
- `kripto/events.py`, `kripto/tsize.py`, `scripts/insilico_study.py`, `scripts/aggtrades.py`
- For any rule you work on, RE-READ ITS SOURCE RECORDS in `data/chat_extract/out/dataset/items.jsonl`
  (ids are in the catalogue). The chart descriptions and transcripts hold details the first pass
  flattened. Skip records flagged `exploit_advocacy_do_not_use`; use `describes_manipulation_*` records
  only to recognise patterns, never as a strategy.

## How to work (this is the point of the session)
1. **Think before testing.** For each rule you take on, write a short think-through in
   `research/insilico_pass2.md` BEFORE running anything:
   - the mechanism: who is on the other side and why they lose;
   - what the author actually does (context, level, timeframe, venue, what he waits for);
   - at least three materially different formulations, and which is closest to the author;
   - why the first-pass version may have failed for reasons unrelated to the idea (definition, venue,
     bar type, fill model, universe, stand-alone vs filter);
   - what result would change your mind in each direction.
2. **Diagnose before any verdict.** For every failure say WHY: negative before costs, killed by costs,
   killed by the fill model, too few events, wrong venue, or regime. Use decompositions and event studies
   (`scripts.insilico_study`), not just a Sharpe.
3. **Two-stage evidence**, so exploring is allowed and self-deception is not:
   - EXPLORE freely (descriptive event studies, many formulations) on the exploration sample only:
     2021-01..2023-12 and the 10 original coins (BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC).
   - CONFIRM at most the 3–5 best formulations, pre-registered in a batch file before touching the
     confirmation sample: 2024-01..2026-10 and coins not used in exploration. One walk-forward or
     frozen-config test each, through `kripto.research` so it is logged.
   - Every backtest still goes through `kripto.research`. Never tune on the confirmation sample.
4. **Verdict vocabulary.** "This formulation fails" is not "the idea is dead". An idea may be recorded as
   DEAD only after at least three materially different formulations failed AND the reason is diagnosed.
   Otherwise record OPEN with what is still untried.
5. **Report for every result:** before costs vs after, turnover, per year, before/after 2023,
   day-clustered t-stat, share of P&L from the top 3 days, taker and maker cases, $1,000 and $200.

## What the first pass did not try (starting points, not a checklist to rush through)
**Trade-size buckets (R1, R2, R3)**
- buckets fitted per coin from the recent size distribution (the author's "AI levels"), not fixed USD;
- magnitude instead of sign: how extreme the one-sided selling is relative to that coin's history;
- the trend-conditional version (R2: capitulation on a pullback inside an uptrend);
- large-bucket delta vs small-bucket delta as "informed vs uninformed" flow;
- the confirmed opposite effect (all-buckets-positive days are followed by gains) as a feature that
  could improve the existing `flow` book;
- session and intraday bars instead of UTC days; thinner coins; spot plus perp combined;
- the venues the author says matter (BitMEX, Bybit inverse). Both publish free public trade archives;
  check their terms before downloading (HARD RULE 2).

**Mousetrap (R4)**
- real levels (prior-day low, weekly low, round numbers) instead of a rolling n-bar low;
- only in the direction of the larger trend; an exit that follows the move instead of a fixed time;
- absorption measured at the low itself (volume at the extreme vs the rest of the bar).

**Liquidation fade (R5), the one survivor**
- cascade-only version (many coins triggering together), on coins never used so far;
- pessimistic fills (30–50 bp slippage, no fill in the first minute);
- thinner coins and Hyperliquid; exits and sizing suited to a few large wins;
- spec for a live 1-minute paper book (backlog E1), since only live fills settle it.

**Range retest (R19)**
- the author says it works "especially well with range-based" bars and "from profile delivered levels":
  test on range bars and at profile levels (prior POC, value-area edges), not n-bar ranges;
- a fill model based on traded volume at the level after the order would have been placed (aggTrades
  carry price), instead of the blanket 1 bp trade-through;
- thin Hyperliquid coins where candles are large relative to fees.

**Weekend (R21)**
- the author's reference is the high-volume "collar" price, not simply Friday's close; test that;
- the continuation effect seen since 2023 on BTC, as a NEW hypothesis on the confirmation sample.

**Never tested at all**
- Profile rules R14–R17 (low-volume-node fill, prior POC as support, single-print fills, the balance
  laws). This is the largest part of the author's material and the first pass deferred it. It needs
  volume-at-price: add price bins to the aggTrades pass or approximate from 1-minute bars.
- R6 (thin-volume lows are not bottoms), R8 (volume on rallies), R9 (empty moves get refilled),
  R7 (order velocity on range bars), R28 (low unit-price coins), R23 (drift in the CME break hour).

**Beyond stand-alone strategies**
- each signal as a FILTER or timing input for the books that already work (blend, flow, listing shorts,
  funding capture): does skipping or delaying trades on these signals cut cost or drawdown?
- confluence: the author never trades one signal alone. Test two or three combined (for example
  capitulation flow at a prior-day POC), fixed before looking at the confirmation sample.

## Constraints
- Paper only, public data only, no keys. `nice -n 19`, under 2 GB RAM (measure one unit of work before
  parallelising), and say where any download is going before starting it.
- Data already on laptop AND server: `data/bn/tsize` (BTC ETH SOL 5-minute size buckets 2020–2026),
  `data/bn/klines_1m` (30 coins, 2021–2026). Anything new you download must be copied to the server or be
  rebuildable there by one command written in the journal, before the session ends.
- Nothing is promoted to a paper book in this session.
- pytest before every commit; after changes to `kripto/`, pull and test on the server and run the trader
  once (HARD RULE 6).

## Deliverables
- `research/insilico_pass2.md`: the think-through per rule, what was explored, what was confirmed.
- Updated `research/findings.md` (verdicts in the vocabulary above), `research/backlog.md`, journal,
  a STATUS.md section, the CLAUDE.md process changelog.
- A plain summary for the owner: what was tried per idea, why each failure failed, what is still open,
  and what you would test next. If nothing survives, say so, with the reasons, not just the numbers.
