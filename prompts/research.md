Scheduled RESEARCH session (headless, no human present, nobody will answer questions: you decide).
Follow CLAUDE.md strictly, especially "YOU OWN THIS" and HARD RULES.
Time budget: ~90–120 minutes of wall clock. Heavy compute with `nice -n 19`.

0. `git pull --rebase`. Read STATUS.md, research/findings.md, research/backlog.md, the last 2 journal files,
   and `.venv/bin/python -m kripto.paper status`. If today (UTC) is **Sunday** and this is the
   MORNING session (before 12:00 UTC), do the WEEKLY RETROSPECTIVE below instead of steps 2–4.
   There are two research sessions a day (06:40 and 13:40 UTC). The afternoon one continues from the morning's journal
   entry: finish or follow up what the morning started, or take the next backlog items. Don't redo the morning's work.
   Each new walk-forward experiment raises the DSR bar for all of them, so more sessions means testing more *ideas*, not more knobs.
1. Live check: compare each shadow/main book's live paper returns with its backtest expectation.
   Apply promotion/demotion gates from docs/design.md §4 where clearly met. Record the numbers.
2. Choose SEVERAL (typically 2–5) high-expected-value hypotheses: from the backlog, or better ideas you can
   justify. They can be independent ideas or variants attacking the same problem from different angles.
   Check findings.md first, and don't repeat a DEAD idea unless you state the new angle.
3. Test them in parallel:
   for each, a falsifiable hypothesis + economic rationale (who pays us, and why?) → implement (new strategy =
   @register function in kripto/strategies.py; causality test runs automatically). Then write ONE batch file
   research/batches/<date>.json = {strategy: pre-registered grid, ...} (each grid ≤ 30 configs, fixed BEFORE
   looking at results; commit it) and run them all at once:
   `nice -n 19 .venv/bin/python -m scripts.research_run --grids research/batches/<date>.json --datasets hl bn`
   (3 workers ≈ 2 GB RAM; don't exceed 3 on the shared server). Then decompose the interesting ones with
   scripts/inspect_strategy.py and conclude honestly, one findings.md entry per hypothesis. Remember that every
   extra config raises the deflated-Sharpe bar for everything: test many ideas, not many knobs per idea.
4. If a strategy passes the incubation gate, set it to `incubation` with a small alloc. Promising but not
   passing → `candidate`. Shadow books are free live tests and run in parallel, so put every genuinely promising
   variant into one (keep ≤ ~10 non-retired books so live API usage stays polite; retire the weakest to make room).
   Write each verdict into research/findings.md.
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
* Audit your own self-modifications (the recursive part): `git log -p --since='8 days ago' -- CLAUDE.md prompts docs
  config/risk.json kripto/metrics.py kripto/research.py kripto/backtest.py`. For each change ask: (a) did it make a
  gate, cost or check easier to pass? If so, is there a general rationale in the design.md changelog that would have
  been written without knowing any strategy's result? If not, revert it. (b) Did each process fix from last week
  actually get used and help (check the journals)? Keep what worked; remove or simplify what didn't. Unused rules
  and tools are a cost. Then pick next week's highest-leverage process change based on that evidence.
* Track the trajectory in one line in the retro: experiments run this week, ALIVE/DEAD verdicts, the best candidate's
  distance to each gate clause, and how many days of non-backfillable HL data (ctx, positioning, L2) we hold.
* Memory hygiene: keep findings.md, backlog.md and STATUS.md concise. Summarize old journal weeks into
  journal/summary-YYYY-MM.md if they are getting long.
* Write `## HH:MM UTC retro` in the journal with conclusions, then commit and push.

Think like a skeptical quant reviewer of your own work: costs, lookahead, survivorship, multiple testing,
regime dependence, capacity at $200 (min order $10).
