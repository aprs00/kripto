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
    try:
        cur = con.execute(q)
    except sqlite3.OperationalError as e:  # print the schema so a wrong column name is fixed in one step
        print(f"error: {e}\nschema:", file=sys.stderr)
        for (sql,) in con.execute("select sql from sqlite_master where type='table'"):
            print(sql, file=sys.stderr)
        sys.exit(1)
    if cur.description:
        print("\t".join(d[0] for d in cur.description))
    for row in cur:
        print("\t".join(str(x) for x in row))


if __name__ == "__main__":
    main()
