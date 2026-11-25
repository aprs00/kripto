#!/usr/bin/env bash
# Headless Claude session. Usage: scripts/agent.sh review|research|insilico
set -uo pipefail
MODE="${1:?review|research|insilico}"
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
mkdir -p logs
LOG="logs/agent-$(date -u +%F)-$MODE.log"
exec 9>"$HOME/.kripto-agent.lock"
# reviews (health) wait up to 100 min for a running session instead of being skipped; other modes skip
WAIT=0; [ "$MODE" = review ] && WAIT=6000
flock -w "$WAIT" 9 || { echo "$(date -u) another agent session is running; skip" >> "$LOG"; exit 0; }
git pull -q --rebase || echo "git pull failed" >> "$LOG"
case "$MODE" in review) TURNS=40; TMO=35m;; research) TURNS=250; TMO=140m;; insilico) TURNS=220; TMO=105m;; *) exit 2;; esac
# The InSilico programme costs tokens only when it has work: paused (state/insilico.paused) or nothing due -> stop here
if [ "$MODE" = insilico ]; then
  WHY="$(.venv/bin/python -m scripts.insilico_queue should-run)" || { echo "$(date -u +%FT%TZ) insilico: no session ($WHY)" >> "$LOG"; exit 0; }
fi
# HARD RULES are immutable for headless sessions: remember the section now, put it back afterwards if it changed
SNAP="$(mktemp)"; .venv/bin/python -m scripts.guard save "$SNAP" 2>> "$LOG" || SNAP=""
echo "=== $(date -u +%FT%TZ) start $MODE" >> "$LOG"
# The model is pinned on purpose (owner 2026-11-10: "stick with opus" on the server). Without it the account-wide default
# applies, and a /model change on the owner's laptop silently moved the server to another model for a day.
MODEL="${KRIPTO_MODEL:-claude-opus-5-5}"
timeout "$TMO" claude -p "$(cat prompts/$MODE.md)" --model "$MODEL" --dangerously-skip-permissions --max-turns "$TURNS" \
  --output-format text >> "$LOG" 2>&1
RC=$?
echo "=== $(date -u +%FT%TZ) end $MODE rc=$RC" >> "$LOG"
if [ -n "$SNAP" ]; then
  .venv/bin/python -m scripts.guard check "$SNAP" >> "$LOG" 2>&1
  if [ $? -eq 3 ]; then
    echo "$(date -u +%FT%TZ) $MODE edited HARD RULES; restored" >> logs/agent-failures.log
    git add CLAUDE.md && git commit -qm "guard: restore HARD RULES section edited by a headless $MODE session" \
      && git pull -q --rebase && git push -q
  fi
  rm -f "$SNAP"
fi
# safety net: never lose the session's notes if the agent forgot to commit
if [ -n "$(git status --porcelain -- journal STATUS.md research config)" ]; then
  git add journal STATUS.md research config 2>/dev/null
  git commit -qm "agent($MODE): auto-commit session notes (rc=$RC)" && git pull -q --rebase && git push -q
fi
if [ $RC -ne 0 ]; then echo "$(date -u +%FT%TZ) $MODE rc=$RC" >> logs/agent-failures.log; fi
# usage limit hit: one retry of a research/review session 5 min after the reset (2026-11-25; the 11-24 research day was lost).
# KRIPTO_RETRY marks the retry itself, so it never schedules another. InSilico runs every 2 h anyway: no retry.
if [ $RC -ne 0 ] && [ -z "${KRIPTO_RETRY:-}" ] && { [ "$MODE" = research ] || [ "$MODE" = review ]; }; then
  if WHEN="$(.venv/bin/python -m scripts.limit_retry "$LOG")"; then
    systemd-run --user --unit "kripto-retry-$MODE-$(date -u +%m%d%H%M)" --on-calendar "$WHEN" --setenv KRIPTO_RETRY=1 \
      -p WorkingDirectory="$PWD" "$PWD/scripts/agent.sh" "$MODE" >> "$LOG" 2>&1 \
      && echo "$(date -u +%FT%TZ) $MODE: usage limit, retry scheduled for $WHEN" | tee -a "$LOG" >> logs/agent-failures.log
  fi
fi
exit 0
