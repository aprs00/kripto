"""Run a read-only SQL query against state/paper.db (sqlite3 CLI is not installed on the server).

Usage: .venv/bin/python -m scripts.sql "select * from fills order by ts desc limit 20"
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "state" / "paper.db"


def main() -> None:
    q = sys.argv[1] if len(sys.argv) > 1 else "select name from sqlite_master where type='table'"
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.execute(q)
    if cur.description:
        print("\t".join(d[0] for d in cur.description))
    for row in cur:
        print("\t".join(str(x) for x in row))


if __name__ == "__main__":
    main()
