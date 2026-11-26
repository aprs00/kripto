Scheduled REVIEW session (headless, no human present, nobody will answer questions: you decide).
Follow CLAUDE.md strictly, especially "YOU OWN THIS" and HARD RULES.
Time budget: ~10–15 minutes. No new strategy research here. Reviews run once a day (08:25 UTC); an hourly watchdog
(`scripts/health.py`, no Claude) starts an extra one when it finds a new problem, so if this session was not
scheduled, something is broken: `cat state/health.json` tells you what.

1. `git pull --rebase`. Read STATUS.md. Run `.venv/bin/python -m scripts.health` (the facts), then
   `.venv/bin/python -m kripto.paper status`, check
   `systemctl --user list-timers`, `systemctl --user --failed`, `journalctl --user -u kripto-trader -u kripto-flow -u kripto-live -u kripto-liq --since -25h | grep -iE 'error|warn|traceback|failed|oom' | grep -vE '"errors": (\[\]|0[,}])' | tail -30`,
   and the latest `logs/agent-*` and `logs/agent-failures.log` if present. Check disk space (`df -h ~`).
   Code pushed from the owner's PC (commit messages tagged `[pc]`) was never run by this server's trader before it went live:
   `git log --since=-25h --grep '\[pc\]' --stat -- kripto/ config/` non-empty → `systemctl --user start kripto-trader.service`, confirm it exits 0, record it.
2. Health: if STATUS.md's first line was written by the watchdog ("not by Claude"), Claude sessions had been failing:
   find out why from logs/agent-*.log and say so in STATUS.md. Did the trader run every hour? Any ERROR/ALERT events? Is data fresh (last_bar within 8h)?
   Is the `collector:` line of `paper status` from the last hour with errors=0? (positions/L2 data can't be backfilled.)
   Did the nightly data job and the last research session succeed?
   If anything is broken: diagnose, fix, verify (tests + a real trader run), record. Don't just report it.
3. Sanity: are fills/slippage/fees/funding plausible? Is any book behaving very differently from its backtest
   expectation (see research/findings.md)? Note it. Don't overreact: a few days of paper P&L is mostly noise.
3a. `.venv/bin/python -m scripts.held_back --check`: exit 2 = a strategy passes every written gate clause and is not trading. Fix it now
   (incubation + equal-risk main-book share, by the M1 rule), unless it needs code that cannot be tested in this session: then make it item 0 of the backlog.
3b. **InSilico queue empty** (watchdog WARN "InSilico queue has nothing due", or `python -m scripts.insilico_queue should-run` exits 3 without
   state/insilico.paused): that is NOT a healthy idle state; the 2-hourly sessions do nothing until someone gives them work (11-25 → 11-26: 40 h lost,
   the owner had to notice). Refill it in THIS session: take the highest-value backlog items that the battery can test now with data on disk
   (descriptive studies, filters for live books, data-waiting items' forms that need no new data), add each as a queue item with ≥ 3 planned forms
   (edit research/insilico_queue.json in the existing format; `tests/test_insilico_queue.py` must pass), commit, push, and confirm `should-run` exits 0.
4. Apply lifecycle rules ONLY if a gate in docs/design.md §4 is clearly met (e.g. kill-switch, retirement).
5. If you noticed a process weakness, fix it now if it's quick, or add it to the backlog. Log fixes in the CLAUDE.md
   Process changelog.
6. Overwrite STATUS.md, append a short entry to journal/<today>.md, commit, push.
