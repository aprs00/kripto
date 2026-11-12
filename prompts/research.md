Scheduled RESEARCH session (headless, no human present, nobody will answer questions: you decide).
Follow CLAUDE.md strictly, especially "YOU OWN THIS" and HARD RULES.
Time budget: ~90–120 minutes of wall clock. Heavy compute with `nice -n 19`.

0. `git pull --rebase`. Read STATUS.md, research/findings.md, research/backlog.md, the last 2 journal files,
   and `.venv/bin/python -m kripto.paper status`. If today (UTC) is **Sunday**, do the WEEKLY RETROSPECTIVE
   below instead of steps 2–4. Research runs on Tue and Thu only: the history is fixed, so every extra walk-forward
   experiment raises the DSR bar for all of them (N=49 → SR 1.44, N=500 → 1.76) without adding information.
   Read "What the owner wants" in CLAUDE.md: $1,000 of real capital is waiting on evidence, steady risk, and
   small-account edges (maker execution, listings, cross-venue funding, positioning data) come before more generic factors.
1. Live check: compare each shadow/main book's live paper returns with its backtest expectation.
   Apply promotion/demotion gates from docs/design.md §4 where clearly met. Record the numbers.
2. Choose 2–3 high-expected-value hypotheses (hard cap: 6 new walk-forward experiments per session, counting each
   strategy × dataset): from the backlog, or better ideas you can
   justify. They can be independent ideas or variants attacking the same problem from different angles.
   Check findings.md first, and don't repeat a DEAD idea unless you state the new angle.
2b. THINK BEFORE YOU TEST (owner, 2026-11-12: "you are giving up on things too suddenly"; design.md §4 "No verdict on one
   formulation"). For each hypothesis write a short think-through in the journal BEFORE the batch file: (a) the mechanism: who
   pays us and why; (b) if it comes from a source (library, chat archive, paper), re-read the source and say what it actually
   does: context, level, timeframe, venue; (c) at least THREE materially different formulations (signal definition, bar type or
   horizon, universe or venue, stand-alone book vs filter/timing input for a book that already works, alone vs in combination)
   and which one is closest to the idea; (d) how each could fail for reasons that are not the idea (definition, venue, fill
   model, costs, too few events); (e) what result would change your mind either way. Then EXPLORE with descriptive event
   studies (research/studies/, free of the walk-forward count) on an exploration sample only, after writing down the
   confirmation sample you will not touch (a later period and/or instruments not used in exploration). Pre-register and
   walk-forward only the best one or two formulations, on the confirmation sample. Exploring is how you find the right form
   of an idea; the held-out sample is what stops it from being curve fitting. Never tune on the confirmation sample.
   Also use the library: `library/INDEX.md` (curated books, extracted text in library/books/*.txt, grep it, never
   read a whole book) and `library/notes.md` (ideas already mined from them, with backlog ids). A book's claim is a
   hypothesis that must earn its place through the protocol, never a shortcut past it.
3. Test them in parallel:
   for each, a falsifiable hypothesis + economic rationale (who pays us, and why?) → implement (new strategy =
   @register function in kripto/strategies.py; causality test runs automatically). Then write ONE batch file
   research/batches/<date>.json = {strategy: pre-registered grid, ...} (each grid ≤ 30 configs, fixed BEFORE
   looking at results; commit it) and run them all at once:
   `nice -n 19 .venv/bin/python -m scripts.research_run --grids research/batches/<date>.json --datasets hl bn`
   (3 workers ≈ 2 GB RAM; don't exceed 3 on the shared server; for daily bars and the survivorship-free universe:
   `--datasets hl bnall --interval 1d`). Every result now carries a robustness block for the config the walk-forward
   would trade today (`scripts.show_result <strategy> <dataset>`): 2× costs, one bar of execution delay, first 6/12
   months dropped, each single start day of the schedule, corr to BTC, and `small_acct` (the same config in the $200
   account; the owner may fund $200 or $1,000, so STATUS.md shows both). Quote `worst` and the start-day spread next to
   the OOS Sharpe, never the OOS Sharpe alone. Schedules slower than daily trade as staggered tranches automatically.
   Then decompose EVERY result, the failures above all, with
   scripts/inspect_strategy.py (order strategies: `scripts.insilico_study decomp`) and say WHY it came out as it did:
   negative before costs, killed by costs, killed by the fill model, too few events, wrong venue, one regime only, or carried
   by a handful of days (quote the day-clustered t and the top-3-day share for event strategies). Conclude honestly, one
   findings.md entry per hypothesis, in the ledger's vocabulary: one failed formulation is **OPEN (one form failed)** with the
   untried forms listed in the backlog; **DEAD** needs at least three materially different formulations that failed AND a
   diagnosed reason. Before writing DEAD ask: would a sceptical colleague say I tested the idea, or only my first translation of it? Remember that every
   extra config raises the deflated-Sharpe bar for everything: test many ideas, not many knobs per idea.
4. If a strategy passes the incubation gate, set it to `incubation` with a small alloc. Promising but not
   passing → `candidate`. Shadow books are free live tests and run in parallel, so put every genuinely promising
   variant into one (keep ≤ ~10 non-retired books so live API usage stays polite; retire the weakest to make room).
   Write each verdict into research/findings.md.
4b. Reading (if ≥ 20 min of budget remains): pick ONE `skimmed`/`unread` section from library/INDEX.md that bears on the
   current backlog, read it via grep/sed on the .txt (≤ ~30 pages), and add any *testable* idea to library/notes.md
   (source, claim in your own words, mechanical rule, data needed) plus a backlog item. Mark the section `mined`. If you
   meet a well-cited free paper (arXiv/SSRN) that beats what's on file, note it in INDEX.md's wishlist.
5. Self-improvement check (always): what slowed you down, confused you, or could make you fool yourself this
   session? Fix one such thing if feasible (tooling, tests, data, memory files, prompts) and log it in the
   CLAUDE.md Process changelog.
6. Update backlog.md (reprioritize; add ideas), overwrite STATUS.md, append to journal/<today>.md, run tests,
   run the trader if you changed kripto/ code, commit, push.

WEEKLY RETROSPECTIVE (Sundays): step back from individual experiments.
* Progress: what did we learn this week? Is the main book any closer to having an edge? Look at the trend in
  findings.md and the live shadow books.
* Direction: are we stuck polishing one idea? What are the 2–3 most promising directions overall, including
  ideas not yet in the backlog (HL-specific structure, data we aren't collecting yet, execution improvements)?
  Rewrite the backlog priorities accordingly.
* Process: review the past week's journals for repeated problems, wasted effort and missing tooling. Make the
  highest-leverage process fix and log it in the CLAUDE.md Process changelog.
* **Assumption audit (docs/assumptions.md).** Auditing your changes is not enough: the worst flaws so far were things that never
  changed (hourly-only monitoring, daily-only data, an uncalibrated cost model), and the owner found them, not you. Take the two
  rows with the weakest or oldest evidence, test or challenge each with data (descriptive studies are free; walk-forwards count
  against the budget), and update the row. Add any assumption you catch yourself relying on. Ask of the whole system: if I were
  building this today from scratch, what would I do differently, and what evidence says the current way is right?
* **Dead-list audit.** Take the two oldest DEAD entries in findings.md not yet audited. For each: how many materially
  different formulations were really tested, and is the reason for the failure diagnosed? If fewer than three or no diagnosed
  reason, relabel it OPEN (one form failed), list the untried forms (other definition, bar type, venue, as a filter for an
  existing book, in combination) in the backlog with an honest prior, and mark the entry `audited <date>`. Do not re-test in
  the retro; this only stops ideas from being buried by one test.
* Audit your own self-modifications (the recursive part): `git log -p --since='8 days ago' -- CLAUDE.md prompts docs
  config/risk.json kripto/metrics.py kripto/research.py kripto/backtest.py`. For each change ask: (a) did it make a
  gate, cost or check easier to pass? If so, is there a general rationale in the design.md changelog that would have
  been written without knowing any strategy's result? If not, revert it. (b) Did each process fix from last week
  actually get used and help (check the journals)? Keep what worked; remove or simplify what didn't. Unused rules
  and tools are a cost. Then pick next week's highest-leverage process change based on that evidence.
* Library ROI: how many library-derived ideas were tested, and did any survive? Demote books that produced nothing
  testable after being mined; promote the sources that did.
* Forward ledger: `nice -n 19 .venv/bin/python -m scripts.download bnall` (incremental), then
  `nice -n 19 .venv/bin/python -m scripts.forward_score`. Report, for configs with ≥ 30 forward days: how ALIVE configs did
  versus DEAD ones (the null), and each candidate's forward return next to its backtest OOS Sharpe. Put the candidates'
  forward numbers in STATUS.md. Until there are 30 days, say "too early" and nothing more. Commit research/forward.json.
* Track the trajectory in one line in the retro: experiments run this week, ALIVE/DEAD verdicts, the best candidate's
  distance to each gate clause, and how many days of non-backfillable HL data (ctx, positioning, L2) we hold.
* Memory hygiene: keep findings.md, backlog.md and STATUS.md concise. Summarize old journal weeks into
  journal/summary-YYYY-MM.md if they are getting long.
* Write `## HH:MM UTC retro` in the journal with conclusions, then commit and push.

Think like a skeptical quant reviewer of your own work: costs, lookahead, survivorship, multiple testing,
regime dependence, start-day and start-date luck, and whether it is executable in a $1,000 account (min order $10).
