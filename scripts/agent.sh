#!/usr/bin/env bash
# Headless Claude session. Usage: scripts/agent.sh review|research
set -uo pipefail
MODE="${1:?review|research}"
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
mkdir -p logs
LOG="logs/agent-$(date -u +%F)-$MODE.log"
exec 9>"$HOME/.kripto-agent.lock"
flock -n 9 || { echo "$(date -u) another agent session is running; skip" >> "$LOG"; exit 0; }
git pull -q --rebase || echo "git pull failed" >> "$LOG"
case "$MODE" in review) TURNS=40; TMO=35m;; research) TURNS=200; TMO=140m;; *) exit 2;; esac
echo "=== $(date -u +%FT%TZ) start $MODE" >> "$LOG"
timeout "$TMO" claude -p "$(cat prompts/$MODE.md)" --dangerously-skip-permissions --max-turns "$TURNS" \
  --output-format text >> "$LOG" 2>&1
RC=$?
echo "=== $(date -u +%FT%TZ) end $MODE rc=$RC" >> "$LOG"
# safety net: never lose the session's notes if the agent forgot to commit
if [ -n "$(git status --porcelain -- journal STATUS.md research config)" ]; then
  git add journal STATUS.md research config 2>/dev/null
  git commit -qm "agent($MODE): auto-commit session notes (rc=$RC)" && git pull -q --rebase && git push -q
fi
if [ $RC -ne 0 ]; then echo "$(date -u +%FT%TZ) $MODE rc=$RC" >> logs/agent-failures.log; fi
exit 0
