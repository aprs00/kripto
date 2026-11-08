Scheduled RESEARCH session (headless, no human present). Follow CLAUDE.md hard rules strictly.
Time budget: ~60 minutes of wall clock. Heavy compute with `nice -n 19`.

1. `git pull --rebase`. Read STATUS.md, the last 2 journal files, research/backlog.md, and
   `.venv/bin/python -m kripto.paper status`.
2. Live check: compare each shadow/main book's live paper returns with its backtest expectation.
   Apply promotion/demotion gates from docs/design.md §4 where clearly met. Record the numbers.
3. Pick the highest-value item in research/backlog.md (or a better idea you can justify in writing),
   and take it as far as you can this session:
   form a falsifiable hypothesis with an economic rationale (who pays us, and why?) → implement
   (new strategy = @register function in kripto/strategies.py + causality test passes automatically)
   → `scripts/research_run.py` walk-forward on HL and Binance → write up results honestly.
   Parameter grids: small (≤ 30 configs) and decided BEFORE you look at results.
4. If a candidate passes the incubation gate, add it to config/strategies.json as `incubation` with
   a small alloc. If it only looks interesting, add it as `candidate` (shadow book only).
5. Update research/backlog.md (mark done with a one-line result, add new ideas you discovered).
   Overwrite STATUS.md, append to journal/<today>.md, run tests, commit, push.
Think like a skeptical quant reviewer of your own work: costs, lookahead, survivorship, multiple testing,
regime dependence, capacity at $200 (min order $10).
