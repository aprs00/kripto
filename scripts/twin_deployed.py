"""Deployed share of every $200 twin vs its big sibling, from the latest equity rows (insilico SMB1 2026-11-28; backlog SMB step 1).
deployed = (twin gross / twin equity) / (sibling gross / sibling equity): 1.0 = the twin holds the strategy at the same exposure; 0 = all cash.
A $200 return must be quoted next to this number (CLAUDE.md standing lesson). No network; reads state/paper.db.
    .venv/bin/python -m scripts.twin_deployed            # table
    .venv/bin/python -m scripts.twin_deployed --line     # one line for STATUS.md / scoreboard"""
from __future__ import annotations

import sqlite3
import sys

from scripts.twin_check import DB, sibling


def latest(con) -> dict[str, tuple[float, float, int]]:
    q = ("select e.book, e.equity, e.gross, e.n_pos from equity e join (select book, max(ts) ts from equity group by book) m "
         "on e.book = m.book and e.ts = m.ts")
    return {b: (float(eq), float(g), int(n)) for b, eq, g, n in con.execute(q)}


def table(rows: dict[str, tuple[float, float, int]]) -> list[dict]:
    out = []
    for b in sorted(rows):
        s = sibling(b)
        if s is None or s not in rows:
            continue
        eq, g, n = rows[b]
        seq, sg, sn = rows[s]
        big = sg / seq if seq > 0 else 0.0
        out.append({"twin": b, "sibling": s, "twin_gross_x": round(g / eq, 3) if eq > 0 else None, "sibling_gross_x": round(big, 3),
                    "deployed": round((g / eq) / big, 2) if eq > 0 and big > 0 else None, "names": n, "sibling_names": sn})
    return out


def main():
    t = table(latest(sqlite3.connect(DB)))
    if "--line" in sys.argv:
        mains = [r for r in t if r["sibling"] in ("main", "main_bn", "main@pair")]
        print("$200 deployed share of the $1,000 book: " + ", ".join(f"{r['twin']} {r['deployed']} ({r['names']} vs {r['sibling_names']} names)" for r in mains))
        return
    for r in t:
        print(f"{r['twin']:28s} vs {r['sibling']:26s} deployed {r['deployed']!s:>5}  gross {r['twin_gross_x']}x vs {r['sibling_gross_x']}x  names {r['names']} vs {r['sibling_names']}")


if __name__ == "__main__":
    main()
