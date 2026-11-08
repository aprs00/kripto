Scheduled REVIEW session (headless, no human present). Follow CLAUDE.md hard rules strictly.
Time budget: ~10 minutes. Do not start new research.

1. `git pull --rebase`. Run `.venv/bin/python -m kripto.paper status` and check
   `systemctl --user list-timers` and `journalctl --user -u kripto-trader --since -5h | tail -50`.
2. Health: did the trader run every hour? Any ERROR/ALERT events? Is data fresh (last_bar within 8h)?
   Fix obvious operational bugs (tests must pass). Restart nothing outside your user units.
3. Sanity: are fills/slippage/fees/funding plausible? Any book behaving very differently from its
   backtest expectation (see the latest research numbers in journal / config)? Note it, don't overreact:
   a few days of paper P&L is mostly noise.
4. Apply lifecycle rules ONLY if a gate in docs/design.md §4 is clearly met (e.g. kill-switch, retirement).
5. Overwrite STATUS.md, append a short entry to journal/<today>.md, commit, push.
