# Process changelog (append; newest last)

Moved out of CLAUDE.md on 2026-11-26 (it was 210 of CLAUDE.md's 430 lines, read in full by every session). Append every process change here;
put a lesson into CLAUDE.md "Standing lessons" only if a future session must act on it at the moment it works.

* 2026-11-08 setup: initial system.
* 2026-11-08 review: untested edit (py3.12-only f-string) crashed the trader twice → added import smoke test
  and rule 6 "run the real trader after code changes".
* 2026-11-08 setup: owner hands over all decisions. Added "YOU OWN THIS", the memory table,
  `research/findings.md`, weekly retrospective, and the rule for changing gates.
* 2026-11-08 setup: owner noted research shouldn't be one-idea-at-a-time. research_run gained `--grids <batch.json>`
  (parallel multi-hypothesis batches, 3 workers ≈ 2 GB); research sessions now test 2–5 hypotheses each; up to ~10
  shadow books in parallel.
* 2026-11-08 setup: owner asked whether 1 day is too short to scrap a strategy. Made error bars explicit (findings.md
  cross-cutting lessons). Live paper's job = tracking vs backtest replay (backlog T0a, top priority). HL-only DEAD verdicts
  get re-checked after 6 more months of HL data (T0b).
* 2026-11-08 review: HL client/download/paper rate-limit defaults raised to 3.0s, so rule 2 holds even outside systemd (previously 0.3s/2.0s defaults).
* 2026-11-09 review: `sqlite3` CLI is not installed (and rule 3 forbids system packages) → added `scripts/sql.py` (read-only queries on state/paper.db) and fixed the Commands section.
* 2026-11-09 review: shadow books never traded → found `rebalance_rows` used `index.asi8` assuming ns, but pandas 3 loads µs, so
  live never rebalanced and ALL 2026-11-08 backtests were wrong (rebalance in 1000-bar blocks, hold ~5000). Fixed (Timedelta
  arithmetic), added tests/test_strategies.py (all datetime units), marked every finding provisional → backlog T0 re-run. Lesson:
  timestamp/alignment helpers need known-answer tests; a "flat book" past its expected trade time is a bug until proven otherwise.
* 2026-11-09 research: result JSONs named per minute overwrote each other (lost one T0 file) → seconds+pid in filenames;
  added scripts/show_result.py (stop hand-parsing result JSON). Added `--interval 1d` and the survivorship-free `bnall`
  dataset (all 923 Binance USDT perps incl. delisted, `data.bn_download_all_daily`). The BN-82 set is survivor-biased, so
  prefer bnall for any test where survivorship matters. HL loader masks pre-listing zero-volume oracle candles.
* 2026-11-09 review: `paper status` shows `lastreb=<bar>` per book. A book whose last rebalance is older than its schedule is
  a bug until proven otherwise (the 11-08 bug went unnoticed because status showed no rebalance age).
* 2026-11-09 owner: added `scripts/dash.sh` / `scripts/dash.py`, a read-only, phone-width (≤ 46 cols) dashboard the owner
  opens over SSH (health line, books, timer results, Claude session rc/duration, commits, disk/RAM). If you add a book type,
  log format or timer, check the dashboard still shows it correctly.
* 2026-11-09 interactive (owner asked for a self-improvement pass): (1) DSR `n_trials` counted raw registry lines, so
  the bar rose ~150/day with cost stresses and re-runs, became unreachable on HL (SR ≈ 3.4), and made re-checks
  costly. Now WF OOS is deflated by the number of WF experiments and measured on the longest survivorship-free venue
  (design.md changelog, effective from the 11-10 research session; no current strategy passes). Test added.
  (2) Backlog: non-backfillable HL data collection (T6a) and the candidate blend (T4) moved to the top. (3) The weekly retro now
  audits the week's self-modifications (did any make a gate easier without a general rationale? did last week's
  process fixes actually help?) and tracks a one-line trajectory, so self-improvement is checked, not just done.
* 2026-11-09 interactive: owner approved a second daily research session (13:40 UTC; the 06:40 one used ~45 of 140 min,
  so throughput was the bottleneck, not compute). The Sunday retro is the morning session only. The afternoon
  session continues from the morning's journal.
* 2026-11-09 interactive: owner supplied a 174 GB folder of trading books/courses. I read and triaged it and kept 11 texts
  (order-flow microstructure (Bouchaud/Farmer/Lillo, Tóth et al.), BTC price discovery, Max Dama, Pole stat arb, Guéant
  execution, Tsay, a HAR vol paper, plus Valtos/Dalton/Tradingriot as concept sources) in `library/books/` (gitignored,
  copyrighted). Rejections and reasons are in library/INDEX.md. Seeded library/notes.md N1–N7 → backlog L1–L6. Research
  sessions now read one library section when time allows (step 4b); the retro checks library ROI.
* 2026-11-09 research (pm): T6a collector (kripto/collect.py) runs at the end of every trader step on the same 3 s client
  (≤ ~56 extra /info calls/h, 5-min deadline, failures only WARN). `paper status` now ends with a `collector:` line (last
  pass + days held of ctx/positions/L2) and the review prompt checks it: a silent gap in non-backfillable data is lost forever.
  Lesson from T4: blend components' params were picked after seeing results; when combining candidates, either nest the
  param choice inside the walk-forward or say so explicitly (backlog T4b).
* 2026-11-09 interactive: owner added Binance as a second paper venue (design.md changelog). The gate is judged on the venue
  traded; one $200 main book per venue. Build spec = backlog B1 (top priority).
* 2026-11-09 interactive: built the Binance paper venue (B1): kripto/bn.py (whitelisted public GETs only, 1 req/s,
  small-limit incremental klines ≈ 61 weight/run), kripto/venue_bn.py (depth-walk fills, 5 bp, step/min-notional,
  8h funding), paper.py split into compute_targets/run_books shared by both venues, with positions/funding separated
  per venue (book_venue). Tests: tests/test_venue_bn.py (fake client). Shadow books xsmom_k@bn, flow@bn, tsmom@bn.
* 2026-11-09 review: `scripts/sql.py` prints the table schemas on an OperationalError (wrong column names cost a round trip).
* 2026-11-09 interactive (owner asked for a whole-project review, then "implement whatever would help"): the review found
  that single-start-day schedules made concentrated books a lottery (bnall xsmom_k 0.26–1.46 by weekday), that the blend's
  1.57 leaned on hindsight component choice, a thin early window and same-close fills, and that 8 Claude sessions a day
  cost more than a $200 account could earn. Changed: staggered tranches in research AND live (`strategies.scheduled`);
  main books $1,000 and band 0.01; a robustness block stored with every walk-forward (gate reads `robust.worst`);
  `scripts/forward_score.py`; hourly deterministic `scripts/health.py` + daily review + research Tue/Thu + Sunday retro;
  `scripts/guard.py` restores the HARD RULES section after a headless session. New section "What the owner wants".
  Lessons: (1) a result that depends on an arbitrary choice (start day, start date, same-close fill) is not a result, so
  compute those stresses by default instead of remembering to; (2) "noticing" belongs in code, "fixing" in a session.
* 2026-11-09 interactive (owner asked for one or two more strategies, from the library where possible): added cross-venue
  datasets `hlx` and `pair` (data.load_panel) and tested flow-on-HL (library N1/N4) and `fspread` funding capture. Both are
  positive before costs and dead after them, like xsmom_k on HL. Lesson: report gross, costs and turnover separately and
  distinguish "dead" from "dead at taker costs"; the latter list is the to-do list for execution work (T9), which is now
  backlog priority 1. The nightly data job also starts HL funding history for 8 more coins a night (`--funding-extra`).
* 2026-11-10 research: (1) batch files may carry `_note` keys (the pre-registration rationale and decision rule live next to the
  grid; research_run skips them). (2) `scripts/exec_study.py` + `kripto/execution.py`: execution policies are compared through
  research.evaluate (lines tagged exec) instead of ad-hoc scripts. (3) Config entries may carry `due`/`due_what`; the hourly watchdog
  WARNs when a chore is overdue (first use: blend_nested's 60-day refit, `scripts/nested_choice.py`), so dated chores live in code,
  not in memory. (4) Library .txt files need `grep -a` (plain grep silently found nothing in maxdama). Lesson from T9: a cost
  saving in fees can be eaten by alpha loss; measure execution changes on the longest history with the return effect, not cost/yr.
* 2026-11-10 research: retiring an entry left its shadow book holding stale positions (HL xsmom kept 30 open positions and kept
  accruing funding). `run_books` now closes a retired entry's book once (test added). Lesson: a lifecycle change needs its exit path.
* 2026-11-10 review: `paper status` kept showing the closed, retired xsmom book with its last live equity row (30 positions it no
  longer held). run_books now writes a final equity row when it closes a retired book. Lesson: status reads snapshots, so every
  path that changes a book outside the normal loop has to write its own snapshot.
* 2026-11-10 interactive: owner asked to test at $200 as well as $1,000. `small_equity` in config/risk.json → `small:` twin of
  every book (run_books), `small_acct` in every robustness block, one order-book snapshot per coin per run (`simulate_fill` cache,
  180 s) so twins cost no API calls, dashboard section for the small accounts. First comparison (full-sample, chosen configs):
  many-name books lose most of their edge at $200 (flow 1.31 → 0.72, broad momentum 1.49 → 0.97), concentrated ones don't
  (listing shorts, trend, funding capture, the hand-picked blend). Lesson: "which strategy" depends on "which account".
* 2026-11-10 interactive (owner: "why isn't it always live", "why only daily data", "this does not seem
  RSI at all"): three day-1 choices had never been tested. (1) Monitoring was hourly only because the trader was a timer →
  `kripto/live.py` + kripto-live.service (20 s). (2) Decisions/bars: decision-frequency study says faster decisions earn more
  before costs and less after them at modelled costs. (3) The cost model had never been compared with live fills: live slippage
  is 0.9 bp vs 5.1 bp modelled on HL, so every HL "dead at taker costs" verdict was judged at ≈ 1.8× real cost (backlog C1).
  Process fix: `docs/assumptions.md` + an assumption audit in the Sunday retro. Lesson: self-improvement that only reviews its
  own recent changes never finds the flaws it was born with; audit what has NOT changed, and calibrate every model
  against reality as soon as reality produces data.
* 2026-11-10 interactive: the owner reduced their instructions to one: "the only rule is that it should create a profitable
  trading bot, rest of the stuff is up to you to decide". New section "The mandate". HARD RULE 1 amended in the owner's presence,
  minimally: public read-only websocket market data is allowed (it was /info polling only); paper-only, no keys, no orders,
  legality and the sandbox are unchanged and stay unchanged. Two consequences decided now: (1) the paper MAIN books should trade
  the best current estimate instead of sitting flat until a statistical gate passes (design.md changelog; effective from the
  next research session, not this one); the gate now governs the recommendation to fund real money. (2) Backlog W1: collect
  HL trade flow over the websocket (non-backfillable; flow is the strongest signal on Binance and HL has no history of it).
* 2026-11-10 interactive: the server's sessions had silently switched model. The owner changed the default on their laptop and the
  account-wide setting reached the server (the 08:25 review ran on it). `scripts/agent.sh` now passes `--model` explicitly
  (`KRIPTO_MODEL`, default claude-opus-5-5, the owner's choice). Lesson: pin anything the owner decided; inherited defaults drift.
* 2026-11-11 review: the owner's "run everything now" session died silently twice (unknown model, then the 5-hour usage limit) and the
  watchdog only said `rc=1`. It now quotes the failed session's last log line. Lesson: interactive work and headless sessions share one
  usage budget; a hand-started session after a long interactive day may not get to run.
* 2026-11-12 research: built M1 (main books trade the rule-picked mix), X2 (`kripto/venue_pair.py`, two-venue books, live watcher
  prices them from the same tick) and W1 (`kripto/flow.py` + kripto-flow.service; heartbeat `flow_tick`, watchdog ALERT after 5 min).
  Descriptive studies now live in `research/studies/` (one script per question) instead of ad-hoc heredocs, so a finding can be re-run.
  Lessons: (1) X1c/X1d: a backtest of a cross-venue book silently assumed ONE margin account (mdd −1.7%); two real accounts at gross 2
  would have been liquidated on 2025-10-10. Model the account structure that would really hold the money, not just the portfolio
  (assumptions.md row 14). (2) Verify a data field against an independent source before trusting it: HL `side` looked 7% wrong until
  the check used the quote from before the trade's block. (3) The forward ledger had never run end-to-end (crashed on exec_study
  result lists): a weekly tool must be run once when it is built, not first on the Sunday it is needed.
* 2026-11-12 interactive (owner supplied a trader's chat archive; "turn it into tested hypotheses"): 32 rules catalogued, 5 pre-registered,
  4 dead, 1 open (findings). Built `kripto/events.py` (order-level fills for intraday rules; the weight engine could not express a resting
  bid), `kripto/tsize.py` + `scripts/aggtrades.py`, datasets bnm / bnts. Lessons: (1) **The owner had to ask why the server lacked the test
  data.** Research data pulled in an interactive session stayed on the laptop. Rule: before a session ends, every dataset a recorded
  result depends on is on the server or rebuildable there by one command written in the journal. (2) A failed-then-promising result gets a
  frozen-config replication on unseen instruments, pre-registered before their data is downloaded; then check clustering (t on daily sums,
  top-3-day share) before believing it. (3) Measure the RAM of one unit of work before parallelising (first run: 6 GB against a 2 GB limit).
* 2026-11-12 interactive (owner: "you are giving up on things too suddenly"):
  the five InSilico rules had each been tested in one literal form and recorded as dead. The protocol had many guards against
  false positives and none against false negatives. Added: design.md §4 "No verdict on one formulation" (think-through, ≥ 3
  formulations, explore/confirm split, diagnosed failures, DEAD needs three failed forms), research prompt step 2b, a dead-list
  audit in the Sunday retro (backlog A1), the ledger's verdict vocabulary, `prompts/insilico_pass2.md` for the second pass (P2).
  Lesson: pre-registration protects a test from me, not an idea from a bad test; the choice of WHAT to pre-register deserves more
  thought than the test itself.
* 2026-11-15 retro: (1) **The forward ledger was blind on Binance.** bnall came only from data.binance.vision monthly archives, so it ended at the
  previous month-end and all 30 Binance rows had 0 forward days (they would have until December); nobody noticed because "0 days, too early"
  looks normal in week one. `data.bn_all_recent` now tops it up via the public fapi (tests/test_bn_recent.py); assumptions row 16. Lesson: a
  number that is legitimately small early on hides a pipeline that will never grow it. Check that each source's last bar is recent (data_end),
  not just that the tool runs. (2) Assumption row 9 tested: picking the in-sample best adds noise (grid average won 6/9); walk_forward now
  stores `oos_grid_avg` (known-answer test) and show_result prints it; the gate change is backlog WF1, for a research session. (3) `pgrep -f`
  / `pkill -f` match their own shell command line: wait on a PID (`while kill -0 $pid`) instead.
* 2026-11-15 interactive (owner: "research this extensively", "test shorter timeframes also, hours, minutes"): InSilico second pass under the
  new §4 rule. ~30 formulations, explore 2021–23 → confirm 2024–26 + unseen coins, 4 walk-forwards; findings + research/insilico_pass2.md.
  Survivors: friday_follow (backlog FF1) and the liquidation fade (E1). New strategies `spike_high_short`, `friday_follow`; studies is2_*.py.
  Lessons (also in findings): (1) an event study in log returns made a losing short look like a 3.7% edge: report simple-return mean and
  median and the funding sign. (2) "Levels" need placebo levels. (3) Check a translated rule's base rate on the venue before testing it.
  (4) An arbitrary clock time is a start-day problem: trade it as tranches. (5) A download broke the 2 GB limit again (Bybit days of ~1 GB
  read whole): check the LARGEST file's size before choosing workers, not a typical one. (6) I used Bybit's public archive, which HARD RULE 1's
  endpoint list does not name; reported to the owner in STATUS.md. Do not add a venue's data, even historical, without saying so first.

* 2026-11-16 review: kripto-flow was OOM-killed at every 00:00 day compaction for 3 days (pd.read_json on a whole day in a 300 MB unit) and
  nobody noticed: systemd restarted it in 30 s, under every heartbeat threshold. Fix: pyarrow reader, 500 MB cap, and the watchdog now WARNs on
  any kripto-flow/kripto-live "Failed with result" in the last 2 h; the review greps those journals too. Lesson: an auto-restarting service hides
  its crashes from heartbeat checks, so count restarts, not just silence.
* 2026-11-17 research: (1) T0a finally built (`scripts/live_vs_backtest.py`): HL books track their replay at daily corr 0.99–1.00; the BN gaps were
  the REPLAY's universe (today's top-volume list includes coins that pumped into it later), so live now records the point-in-time universe per bar
  (`universe` table, paper.record_universe). Two of my own first-pass errors would have read as engine bugs (day grouping off by one; held-before-
  rebalance vs live-after weights): a tracking tool needs its own known-answer check before its verdicts count. (2) **A connection is not data:**
  Binance's legacy `/ws/` path accepts websocket connections and sends nothing; the new liquidation collector looked healthy with 0 events.
  Every stream collector's watchdog now checks that data arrives (liq: WARN after 2 h without a print), not just a heartbeat. (3) A leg's P&L
  sum is not its value (R1: alt shorts lose in sum but are the hedge; dropping them took SR 1.23 → 0.33). (4) `pkill -f` killed my own shell
  again (logged 11-15): use the PID. (5) Long downloads go into a transient systemd unit (`systemd-run --user --unit ...`), not a session process.
* 2026-11-19 research: (1) **Third RAM overrun in a week** (11-12 aggTrades, 11-15 Bybit, today bn100: 3.8 GB on load, then OOM-killed twice
  inside the 2 GB unit). The tools made each mistake easy: nothing measured memory, and the backtest copied the whole panel ~7 times. Fixed at the
  root instead of shrinking the test: lean float32 loader, row-wise backtest, block-wise `universe()`, in-place slippage model (results equal to
  1e-12 on float64 data, tests/test_backtest_lean.py keeps the old implementation as the reference); `research_run --probe` measures one evaluate,
  and every result records `max_rss_gb`. Lesson: when the same class of mistake recurs, change the tool so the default is safe, not the checklist.
  (2) inspect_strategy printed its beta/band WARN on every run (noted 11-09, never fixed); now conditional. An alarm that always fires is not read.
  (3) T5b's data job built (nightly, capped): Binance history that grows by night instead of waiting for HL collection.
* 2026-11-22 retro: (1) **The research universe held instruments live cannot trade.** bnall had 233 stock/commodity perps (46% of its top-30 in 2026Q3); live drops them by
  contractType. Nobody had compared the two because T0a replays on live's own list. Loaders now cut them (`config/bn_tradfi.json`, refreshed by `download bnall`; `data.bn_tradfi`).
  Lesson: a tracking check that reuses the live system's own input cannot see that input is wrong; compare the two universes directly. (2) I twice read bnall while its
  alphabetical refresh was running and printed false ranks; `data.refreshing` now marks it and the loader WARNs. Cut a panel at the last date every file has, or wait.
  (3) `live_vs_backtest --since / --daily`; `research/studies/{live_universe,fill_delay,tradfi_effect}.py`. Live delay costs HL +5–17 bp (weak): C1 must include it.
* 2026-11-22 review: the review's journal grep matched the hourly `"errors": []` / `"errors": 0` status lines (48 of them a day), so its `tail -30` pushed real errors out
  (the six flow disconnects of 11-21 09:31, HL 502s, were not shown). prompts/review.md now filters them and includes kripto-liq.
* 2026-11-22 interactive (owner: "did you thoroughly research insilico stuff?" → no; "test everything ... every 12 hours ... i mean it"): about half of what the second pass
  planned had no code, families were still called DEAD, and his main method (distance bars) was never catalogued. Built: `scripts/insilico_queue.py` (137 planned forms; refuses
  a verdict while one has no outcome), `research/studies/is3_lib.py` (one battery for every form: null data, causality, matched baseline, day-block bootstrap, MDE, cost ladder,
  committed pre-registration, one-shot confirm, vault, FDR), `kripto/mbars.py` (move bars), session mode `insilico` + timer. Lesson: a plan without per-item outcomes is a wish;
  put "done / skipped why" in a tool that blocks the verdict.
* 2026-11-23 insilico: first ORDER-level live book (E2b, kripto/ladder.py). Its fill model is the one-bar-late backtest by construction (a quote only
  judges minutes that open after it was computed), so live-vs-backtest compares like with like. Lesson: build the live fill rule from the stressed backtest variant, not the base one.
* 2026-11-23 interactive (owner: "you are kind of too slow, actually, very slow, speed things up"): InSilico sessions every 2 h (10 a day, up to 105 min each) and told to keep
  working through items instead of one chunk; research Mon–Sat instead of Tue/Thu; the daily review now WAITS for a running session (it used to be skipped by the lock).
  Queue deferrals take an hour (`defer <id> 2026-11-24T05:00`). Lesson: a session that is told to do one chunk finishes in 10 minutes and the machine then idles for 12 hours;
  throughput was set by my schedule, not by compute or data. The 6-walk-forward cap per research session and the DSR bar stay: speed must not buy weaker evidence.
* 2026-11-24 insilico: two daily forms (ladder-by-RSI filter, absorption) passed pooled explore cards carried by 2021–22 and failed every confirm. research/insilico_pass3.md §3 now requires each explore year to beat its matched baseline before pre-registration (stricter only). Also found: the pass-2 80%-rule test counted unresolved trades as misses (corrected in findings) and a mixed-side matched baseline (O2; now asserted). Lesson: a pooled p-value over a bull year is not evidence; split by year before spending a confirm.
* 2026-11-25 insilico: `pkill -f` killed my own shell a third time (logged 11-15, 11-17 in this changelog, which a fresh session does not read at the moment it types the command). The warning now sits in
  prompts/insilico.md step 3, next to the unit command where it is used. F0 harness gained a DELAY transform (`is3_filter.noadd`: blocked days may not open/increase a position) with a known-answer test: L5 had been
  tested as an exit, not as the delay the source describes. Lesson: put a recurring warning at the point of use, not in a history log.
* 2026-11-25 research: (1) **A whole research day was lost to the usage limit and nobody re-ran it.** 11-24 06:40 research and 08:25 review both died in 3 s ("hit your 5-hour
  limit · resets 9:40am") after a night of InSilico sessions; the watchdog only logged rc=1. `scripts/agent.sh` now schedules ONE retry of a research/review session 5 min after
  the printed reset (`scripts/limit_retry.py`, test; a transient `kripto-retry-*` timer, KRIPTO_RETRY stops chains). (2) The hourly trader downloaded 30 days of HL funding per coin and
  accrued funding per held coin BEFORE trading: HL fills came ~11 min after the close (C1 drift). Trades now come first (3 min); accrual uses the pre-trade snapshot (test).
  (3) `scripts/cost_calibration.py` (C1, monthly): live slip + drift vs the model per venue and volume bucket. Lesson: an average cost number can be one event (XTEN = 78% of HL cost);
  always print the cost by bucket and the top contributors before refitting a model.
* 2026-11-26 research: (1) **A clause of a fixed rule was applied on one venue only, twice.** The M1 interpretation "of two blends, the hindsight-free one" replaced blend by
  blend_nested on HL (11-12) but nobody applied it on Binance (11-12, 11-19); "no change" looked plausible, so nobody re-read the rule. Applied now (main_bn = flow@bn +
  blend_nested@bn). Lesson: when re-deriving by a rule, walk every clause against every venue in writing, especially when the answer is "no change". (2) The T5b metrics
  backfill runs newest-first per coin, so an incomplete early year is a biased subset (BTC started 2024-07 while 2022 held 13k coin-days): `scripts/metrics_coverage.py` (test)
  prints per-year completeness; explore only complete years. (3) The live BN panel now carries funding (venue_bn.funding_panel), so funding strategies can trade on Binance.
  (4) AL2b main-book monthly vol multiplier (design.md 2026-11-26), switched on next session by `scripts.main_scale --write`.
* 2026-11-26 interactive on the owner's PC (owner: "continue and spread out agents, note that this running on pc rather than on server"): first session off the server.
  The data copy was 17–27 days stale and missing whole sources, and nothing said so: `scripts/data_status.py` (+ test) prints every source's last bar and age;
  CLAUDE.md "interactive on the owner's PC" says what may run there; `[pc]` commit tag + review step so PC code changes get the rule-6 trader run on the server.
  Parallel research agents each got one backlog item, a walk-forward budget share (total ≤ 6) and no write access to the shared memory files (lead integrates), so
  findings/journal edits cannot collide.
* 2026-11-26 interactive (owner, angry, rightly: "why the fuck this has not run since yesterday morning"): the InSilico queue held nothing due from 11-25 05:36 (every item waited
  for data), so the 2-hourly sessions skipped for 40 h, and two reviews wrote "insilico idle (nothing due)" as if that were healthy. The owner noticed, not the system.
  Fix: `scripts/health.py` WARNs when the queue has nothing due and no InSilico session ran for 6 h (test), which starts a review; prompts/review.md step 3b makes that review
  refill the queue from the backlog in the same session. Lesson: a scheduler that is allowed to skip must treat "nothing to do" as a fault to fix, not a status to report.
* 2026-11-26 interactive (owner: "you are gatekeeping actual profitable strategies", then "the issue is in you, the model"): agreed. My caution added a condition
  the gate does not have (ladder@bn: every clause passed 11-23, alloc 0 until 11-27), and the protocol I wrote guards only against false positives. Counterweights
  that do not depend on my judgement: design.md §4 "No unwritten hold-backs" (gate sufficient; extra conditions = gate changes), `scripts/held_back.py` (mechanical
  table, test; mixed-sign grids judged on the pick's own sign, missing evidence shown as missing), watchdog WARN + review step 3a, an ADVOCATE paragraph in the
  journal before any strategy is left out, and STATUS.md "Held back" + "Scoreboard" (`scripts/scoreboard.py`) at the top where the owner reads first.
* 2026-11-26 interactive (owner: "do we need to cleanup or change up any .md files?"): yes. The memory files every session reads had grown to ~160 KB (CLAUDE.md 50 KB, of which the
  changelog 30 KB; findings 75 KB; backlog 35 KB, half of it done items). Moved this changelog to docs/process_changelog.md and kept a short "Standing lessons" list in CLAUDE.md;
  moved done/superseded backlog items to research/backlog_done.md (backlog 15 KB); `scripts/findings_index.py` (+ test) generates a one-line-per-hypothesis Index at the top of
  findings.md that sessions read instead of the whole file; prompts/insilico_pass2.md archived. HARD RULES section verified byte-identical. Lesson: memory that only grows
  becomes memory nobody reads; give each file a pruning rule at the moment it is written.
* 2026-11-26 insilico: E2B's first anchored-daily run gave five anchors identical prices (pandas ignores `resample(offset=)` on tz-aware daily bins; only a RuntimeWarning, drowned
  among others) with shifted funding, and logged five junk `anchor` registry lines (bn100_1d@04..@20, ~21:45 UTC). Caught because five different anchors printed the same SR to 3 decimals.
  Fixed by shifting the index + a known-answer assert on BTC; repo grep found no other use. Lesson in CLAUDE.md "Verify the plumbing". Also: queue items with no due work were refilled
  in-session (FF2, W3B) instead of letting the queue run dry.
* 2026-11-27 research: (1) A structural hold-back: a strategy type with no main book (pair) could pass the gate and have nowhere to trade; held_back.py flagged it,
  which is how it was found. Fixed with `main@pair` (design.md 2026-11-27) rather than by leaving it out. Lesson: when adding a new book TYPE (venue, overlay), give it
  a path into a main book in the same change. (2) The ladder needed main-book plumbing for 4 days after passing; the `sleeve` table now lets any overlay strategy share
  a main book's ledger without the hourly rebalance netting it. (3) `scripts/ledger_decomp.py <book>` (+ test): daily funding / fees / price split and live vol from the
  ledger alone, for books scripts.live_vs_backtest cannot replay (pair, sleeves). Built because today's DSR pass of fspread_hold rested on a backtest vol 3× below live.
