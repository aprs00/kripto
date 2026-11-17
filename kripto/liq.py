"""Binance liquidation-print collector over the PUBLIC websocket (backlog LQ1, 2026-11-17).

    python -m kripto.liq            # runs forever (systemd: kripto-liq.service, Restart=always)

Why: the liquidation fade (findings: lshock, OPEN, tail-event) and several InSilico rules need to tell a forced-liquidation
cascade from an ordinary dump. Binance publishes liquidation orders only as a live stream; nothing serves their history, so
this data exists only if we record it as it happens (non-backfillable).
What: ONE connection to wss://fstream.binance.com/market/ws/!forceOrder@arr (public, unauthenticated, read-only market data; HARD
RULE 1 as amended 2026-11-10). Every message is one liquidation order: symbol, side (SELL = a long was liquidated), qty,
average fill price, filled qty, status, trade time. Binance sends at most the latest liquidation per symbol per second, so
counts are a LOWER bound in a cascade; notional is still the best public measure.
Output (gitignored): raw rows in data/bn/liq/YYYY-MM-DD.jsonl while the day is open -> YYYY-MM-DD.parquet after it ends
(pyarrow reader, the lesson of kripto/flow.py's OOM at compaction). Connect/disconnect times in gaps.jsonl.
Heartbeat: meta `liq_tick` in state/paper.db every minute (scripts/health.py alerts if it is silent for 5 min, and warns if no
liquidation arrived for 2 h: across all Binance perps they come several per minute, so silence means a dead stream). Never touches the trader or any book.
"""
from __future__ import annotations

import asyncio
import json
import time

import pandas as pd

from . import data

# 2026-11-17: the legacy /ws/ path still ACCEPTS connections but delivers nothing (not even !markPrice@arr@1s); Binance moved
# market streams to /market/. A connection is not data: the watchdog also checks that liquidations keep arriving (`last_event`).
WS_URL = "wss://fstream.binance.com/market/ws/!forceOrder@arr"
LIQ_DIR = data.DATA / "bn" / "liq"
RECONNECT_S = 23 * 3600      # Binance drops a connection after 24 h: reconnect on our schedule, logged as a gap


def parse(msg: str | dict) -> dict | None:
    """One forceOrder message -> flat row, or None for anything else."""
    m = json.loads(msg) if isinstance(msg, str) else msg
    if m.get("e") != "forceOrder" or "o" not in m:
        return None
    o = m["o"]
    try:
        q, ap, z = float(o["q"]), float(o.get("ap") or o.get("p") or 0), float(o.get("z") or 0)
        return {"T": int(o["T"]), "E": int(m.get("E", 0)), "sym": str(o["s"]), "side": str(o["S"]),
                "q": q, "ap": ap, "z": z, "ntl": z * ap, "status": str(o.get("X", ""))}
    except (KeyError, TypeError, ValueError):
        return None


def write_rows(rows: list[dict], d=None):
    d = d or LIQ_DIR
    d.mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list] = {}
    for r in rows:
        by_day.setdefault(time.strftime("%Y-%m-%d", time.gmtime(r["T"] / 1000)), []).append(r)
    for day, rs in by_day.items():
        with (d / f"{day}.jsonl").open("a") as f:
            for r in rs:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")


def log_gap(kind: str, d=None, ts: float | None = None):
    d = d or LIQ_DIR
    d.mkdir(parents=True, exist_ok=True)
    with (d / "gaps.jsonl").open("a") as f:
        f.write(json.dumps({"ts": time.time() if ts is None else ts, "event": kind}) + "\n")


def compact(d=None, today: str | None = None):
    """Closed days: JSONL -> parquet (deduplicated on time+symbol+side+qty, sorted), then the JSONL is removed."""
    d = d or LIQ_DIR
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    for f in sorted(d.glob("*.jsonl")):
        if f.stem >= today or f.name == "gaps.jsonl":
            continue
        import pyarrow.json as pj
        df = pj.read_json(f).to_pandas() if f.stat().st_size else pd.DataFrame()
        out = d / f"{f.stem}.parquet"
        if out.exists():
            df = pd.concat([pd.read_parquet(out), df])
        if len(df):
            df = df.drop_duplicates(["T", "sym", "side", "q"]).sort_values(["T", "sym"]).reset_index(drop=True)
            tmp = out.with_suffix(".tmp")
            df.to_parquet(tmp)
            tmp.replace(out)
        f.unlink()


def load(day_from: str | None = None) -> pd.DataFrame:
    """All recorded liquidations (closed days + today's open file)."""
    parts = [pd.read_parquet(p) for p in sorted(LIQ_DIR.glob("*.parquet")) if not day_from or p.stem >= day_from]
    for f in LIQ_DIR.glob("2*.jsonl"):
        parts.append(pd.read_json(f, lines=True))
    df = pd.concat(parts) if parts else pd.DataFrame(columns=["T", "sym", "side", "q", "ap", "z", "ntl"])
    if len(df):
        df["ts"] = pd.to_datetime(df["T"], unit="ms", utc=True)
    return df


def heartbeat(info: dict):
    from . import paper as P
    try:
        P.Store().set_meta("liq_tick", json.dumps(info))
    except Exception as e:      # a locked db must not kill the collector
        print(f"{P.now_iso()} heartbeat failed: {e!r}", flush=True)


async def run_forever():
    import websockets
    n_total, reconnects, fails, buf, last_event, started = 0, 0, 0, [], None, time.time()
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=60, max_size=2**20, open_timeout=20) as ws:
                print(f"{time.strftime('%FT%TZ', time.gmtime())} connected", flush=True)
                fails, opened = 0, time.time()
                log_gap("connect")
                last_flush = time.time()
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        msg = None
                    if msg:
                        r = parse(msg)
                        if r:
                            buf.append(r)
                            n_total += 1
                            last_event = r["T"]
                    now = time.time()
                    if now - last_flush >= 60:
                        write_rows(buf)
                        buf = []
                        compact()
                        last_flush = now
                        heartbeat({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "events_total": n_total,
                                   "last_event": last_event and time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_event / 1000)),
                                   "reconnects": reconnects, "up_s": round(now - started)})
                    if now - opened > RECONNECT_S:
                        log_gap("disconnect")
                        break
        except Exception as e:
            log_gap("disconnect")
            if buf:
                write_rows(buf)
                buf = []
            reconnects, fails = reconnects + 1, fails + 1
            print(f"{time.strftime('%FT%TZ', time.gmtime())} websocket error ({reconnects}): {e!r}", flush=True)
            await asyncio.sleep(min(60, 5 * fails))


def main():
    print(f"liquidation collector: {WS_URL} -> {LIQ_DIR}", flush=True)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
