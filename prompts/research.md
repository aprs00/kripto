Scheduled RESEARCH session (headless, no human present, nobody will answer questions: you decide).
Follow CLAUDE.md strictly, especially "YOU OWN THIS" and HARD RULES.
Time budget: ~90 minutes of wall clock. Heavy compute with `nice -n 19`.

0. `git pull --rebase`. Read STATUS.md, research/findings.md, research/backlog.md, the last 2 journal files,
   and `.venv/bin/python -m kripto.paper status`. If today (UTC) is **Sunday**, do the WEEKLY RETROSPECTIVE
   below instead of steps 2–4.
1. Live check: compare each shadow/main book's live paper returns with its backtest expectation.
   Apply promotion/demotion gates from docs/design.md §4 where clearly met. Record the numbers.
2. Choose the highest-expected-value research item: from the backlog, or a better idea you can justify.
   Check findings.md first, and don't repeat a DEAD idea unless you state the new angle.
3. Take it as far as you can this session:
   falsifiable hypothesis + economic rationale (who pays us, and why?) → implement (new strategy =
   @register function in kripto/strategies.py; causality test runs automatically) → walk-forward on HL (and
   Binance where meaningful) via scripts/research_run.py → decompose with scripts/inspect_strategy.py →
   conclude honestly. Parameter grids: small (≤ 30 configs) and fixed BEFORE looking at results.
4. If a strategy passes the incubation gate, set it to `incubation` with a small alloc. If it's promising but
   not passing, make it a `candidate` (shadow book only). Write the verdict into research/findings.md.
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
* Memory hygiene: keep findings.md, backlog.md and STATUS.md concise. Summarize old journal weeks into
  journal/summary-YYYY-MM.md if they are getting long.
* Write `## HH:MM UTC retro` in the journal with conclusions, then commit and push.

Think like a skeptical quant reviewer of your own work: costs, lookahead, survivorship, multiple testing,
regime dependence, capacity at $200 (min order $10).
