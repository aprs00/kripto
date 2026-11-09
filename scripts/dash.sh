#!/usr/bin/env bash
# Phone dashboard. Run as the kripto user:  ~/kripto/scripts/dash.sh [dash|status|journal|log]
# Also used as a forced command for a restricted SSH key (then the arg comes from SSH_ORIGINAL_COMMAND).
cd "$(dirname "$0")/.." || exit 1
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
show() {
  case "${1:-dash}" in
    dash|"")   .venv/bin/python -m scripts.dash ;;
    status|s)  cat STATUS.md ;;
    journal|j) f=$(ls journal/*.md | tail -1); echo "== $f"; tail -n 60 "$f" ;;
    log|l)     f=$(ls -t logs/agent-*.log 2>/dev/null | head -1); echo "== $f"; tail -n 40 "$f" ;;
    *)         echo "usage: dash|status|journal|log" ;;
  esac
}
CMD="${1:-${SSH_ORIGINAL_COMMAND:-dash}}"
show "$CMD"
# interactive mini-menu when there is a terminal (e.g. Termius on a phone)
if [ -t 0 ] && [ -t 1 ]; then
  while true; do
    printf '\n[Enter]=refresh  s=status  j=journal  l=log  q=quit > '
    read -r k || break
    case "$k" in q|Q) break ;; "") clear; show dash ;; *) clear; show "$k" ;; esac
  done
fi
