Scheduled REVIEW session (headless, no human present, nobody will answer questions: you decide).
Follow CLAUDE.md strictly, especially "YOU OWN THIS" and HARD RULES.
Time budget: ~10–15 minutes. No new strategy research here.

1. `git pull --rebase`. Read STATUS.md. Run `.venv/bin/python -m kripto.paper status`, check
   `systemctl --user list-timers`, `systemctl --user --failed`, `journalctl --user -u kripto-trader --since -5h | tail -50`,
   and the latest `logs/agent-*` and `logs/agent-failures.log` if present. Check disk space (`df -h ~`).
2. Health: did the trader run every hour? Any ERROR/ALERT events? Is data fresh (last_bar within 8h)?
   Did the nightly data job and the last research session succeed?
   If anything is broken: diagnose, fix, verify (tests + a real trader run), record. Don't just report it.
3. Sanity: are fills/slippage/fees/funding plausible? Is any book behaving very differently from its backtest
   expectation (see research/findings.md)? Note it. Don't overreact: a few days of paper P&L is mostly noise.
4. Apply lifecycle rules ONLY if a gate in docs/design.md §4 is clearly met (e.g. kill-switch, retirement).
5. If you noticed a process weakness, fix it now if it's quick, or add it to the backlog. Log fixes in the CLAUDE.md
   Process changelog.
6. Overwrite STATUS.md, append a short entry to journal/<today>.md, commit, push.
