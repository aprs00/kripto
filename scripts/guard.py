"""Keep the HARD RULES section of CLAUDE.md immutable across headless sessions (scripts/agent.sh calls this).

  python -m scripts.guard save  <snapshot-file>     # before the session: remember the section
  python -m scripts.guard check <snapshot-file>     # after: if it changed, put it back and exit 3

The rules say the agent may not edit that section; this makes it true mechanically instead of on trust.
Owner-present interactive sessions do not go through agent.sh, so the owner can still change the rules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MANUAL = Path(__file__).resolve().parent.parent / "CLAUDE.md"
HEAD = re.compile(r"^## HARD RULES.*$", re.M)


def section(text: str) -> tuple[int, int] | None:
    """(start, end) character span of the HARD RULES section: its heading up to the next '## ' heading."""
    m = HEAD.search(text)
    if not m:
        return None
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return m.start(), (m.end() + nxt.start()) if nxt else len(text)


def restore(text: str, saved: str) -> tuple[str, bool]:
    """Text with the saved section back in place, and whether anything had changed."""
    span = section(text)
    if span is None:                       # heading deleted or renamed: put the section back before the first '## '
        first = re.search(r"^## ", text, re.M)
        at = first.start() if first else len(text)
        return text[:at] + saved + text[at:], True
    if text[span[0]:span[1]] == saved:
        return text, False
    return text[:span[0]] + saved + text[span[1]:], True


if __name__ == "__main__":
    cmd, snap = sys.argv[1], Path(sys.argv[2])
    text = MANUAL.read_text()
    if cmd == "save":
        span = section(text)
        if span is None:
            sys.exit("no HARD RULES section in CLAUDE.md")
        snap.write_text(text[span[0]:span[1]])
    elif cmd == "check":
        new, changed = restore(text, snap.read_text())
        if changed:
            MANUAL.write_text(new)
            print("HARD RULES section was modified during the session; restored")
            sys.exit(3)
