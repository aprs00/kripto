"""TWC (insilico 2026-11-28): twin and hedge integrity of the paper books, from the positions table alone (no prices, no requests).

  pair books (coins `<C>@hl` / `<C>@bn`): every coin holds BOTH legs, of opposite sign, sizes within 0.7-1.4 of each other.
  small: twins: every position has the same sign in the big sibling (small:main -> main, small:main_bn -> main_bn,
  small:main@pair -> main@pair, small:<entry> -> shadow:<entry>).
Why: 11-28 the $200 pair twin held GRAM@bn / ZEC@bn without their HL hedge (27 % of its gross) and nobody saw it for a day.

  .venv/bin/python -m scripts.twin_check        # prints violations; exit 1 if any
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "paper.db"
MAINS = {"main", "main_bn", "main@pair"}


def sibling(book: str) -> str | None:
    if not book.startswith("small:"):
        return None
    x = book.removeprefix("small:")
    return x if x in MAINS else f"shadow:{x}"


def violations(rows) -> list[str]:
    """rows = (book, coin, size) with size != 0. Returns human-readable problems."""
    pos: dict[str, dict[str, float]] = {}
    for b, c, s in rows:
        if s:
            pos.setdefault(b, {})[c] = float(s)
    out = []
    for b, p in sorted(pos.items()):
        legs: dict[str, dict[str, float]] = {}
        for c, s in p.items():
            if "@" in c and c.rsplit("@", 1)[1] in ("hl", "bn") and (b.endswith("@pair") or b == "main@pair"):
                base, v = c.rsplit("@", 1)
                legs.setdefault(base, {})[v] = s
        for base, lg in sorted(legs.items()):
            if len(lg) == 1:
                (v, s), = lg.items()
                out.append(f"{b}: one-legged pair {base}@{v} {s:+g} (no {'bn' if v == 'hl' else 'hl'} hedge)")
            elif lg["hl"] * lg["bn"] > 0:
                out.append(f"{b}: same-sign pair {base} hl {lg['hl']:+g} bn {lg['bn']:+g}")
            elif not 0.7 <= abs(lg["hl"]) / abs(lg["bn"]) <= 1.4:
                out.append(f"{b}: unbalanced pair {base} hl {lg['hl']:+g} bn {lg['bn']:+g}")
        sib = sibling(b)
        if sib is not None:
            big = pos.get(sib, {})
            for c, s in sorted(p.items()):
                if big.get(c, 0.0) * s <= 0:
                    out.append(f"{b}: holds {c} {s:+g} but {sib} holds {big.get(c, 0.0):+g}")
    return out


def check(db: Path = DB) -> list[str]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return violations(con.execute("select book, coin, size from positions where size != 0").fetchall())


if __name__ == "__main__":
    v = check()
    print("\n".join(v) if v else "twins and hedges: OK")
    sys.exit(1 if v else 0)
