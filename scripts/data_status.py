"""Last bar and age of every local data source, one line each.

Why: sessions also run on the owner's PC (WSL), where data/ is a partial, older copy of the server's (no live ledger,
no websocket collections, monthly archives only). A result on stale or missing data looks like a result; print what is
here before choosing work, and quote the data end in the journal.

    .venv/bin/python -m scripts.data_status          # table
    .venv/bin/python -m scripts.data_status --json
"""
from __future__ import annotations

import json
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]

# (name, directory, reference files tried in order (parquet with a ms time column), or None = dated file names)
SOURCES = [
    ("bnall 1d klines", "data/bn/klines_1d_all", ["BTCUSDT.parquet"]),
    ("bnall funding", "data/bn/funding_all", ["BTCUSDT.parquet"]),
    ("bn 1h klines (82)", "data/bn/klines_1h", ["BTCUSDT.parquet"]),
    ("bn100 1h klines", "data/bn/klines_1h_all", ["BTCUSDT.parquet"]),
    ("bn 1m klines", "data/bn/klines_1m", ["BTCUSDT.parquet"]),
    ("bn funding (82)", "data/bn/funding", ["BTCUSDT.parquet"]),
    ("bn metrics (T5b)", "data/bn/metrics", ["BTCUSDT.parquet"]),
    ("bn liquidations", "data/bn/liq", None),
    ("bn mbars", "data/bn/mbars", None),
    ("hl 1d candles", "data/hl/candles_1d", ["BTC.parquet"]),
    ("hl 4h candles", "data/hl/candles_4h", ["BTC.parquet"]),
    ("hl 1h candles", "data/hl/candles_1h", ["BTC.parquet"]),
    ("hl funding", "data/hl/funding", ["BTC.parquet"]),
    ("hl ctx", "data/hl/ctx", None),
    ("hl positions", "data/hl/positions", None),
    ("hl l2", "data/hl/l2", None),
    ("hl flow (ws)", "data/hl/flow", None),
    ("paper ledger", "state/paper.db", "file"),
]
_DATE = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)")


def _parquet_last_ms(p: Path) -> int | None:
    t = pq.read_table(p)
    for col in ("t", "time", "ts"):
        if col in t.column_names:
            v = t.column(col).to_pylist()
            if not v:
                return None
            m = max(v)
            return int(m.timestamp() * 1000) if hasattr(m, "timestamp") else int(m)
    return None


def _dated_last(d: Path) -> datetime | None:
    best = None
    for f in d.rglob("*"):
        m = _DATE.search(f.name)
        if m:
            s = m.group(1)
            dt = datetime.strptime(s, "%Y-%m-%d" if len(s) == 10 else "%Y-%m").replace(tzinfo=timezone.utc)
            best = dt if best is None or dt > best else best
    return best


def status(root: Path = ROOT, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    rows = []
    for name, rel, ref in SOURCES:
        p = root / rel
        row = {"source": name, "path": rel, "files": 0, "last": None, "age_d": None}
        if ref == "file":
            if p.exists():
                row["files"] = 1
                last = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                row["last"], row["age_d"] = last.isoformat(timespec="minutes"), round((now - last).total_seconds() / 86400, 1)
            rows.append(row)
            continue
        if not p.is_dir():
            rows.append(row)
            continue
        row["files"] = sum(1 for _ in p.iterdir())
        last = None
        if ref is None:
            last = _dated_last(p)
        else:
            for r in ref:
                if (p / r).exists():
                    ms = _parquet_last_ms(p / r)
                    last = datetime.fromtimestamp(ms / 1000, timezone.utc) if ms else None
                    break
        if last is not None:
            row["last"], row["age_d"] = last.isoformat(timespec="minutes"), round((now - last).total_seconds() / 86400, 1)
        rows.append(row)
    return rows


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    rows = status()
    if "--json" in argv:
        print(json.dumps(rows, indent=1))
        return
    host = socket.gethostname()
    print(f"host {host} root {ROOT}  (server checkout is /home/kripto; anything else is a copy: check ages before trusting a result)")
    for r in rows:
        last = r["last"] or "-"
        age = f"{r['age_d']:>6.1f} d" if r["age_d"] is not None else "   missing" if not r["files"] else "      ?"
        print(f"{r['source']:<20} {r['files']:>6} files  last {last:<22} {age}")


if __name__ == "__main__":
    main()
