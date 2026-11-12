"""Hyperliquid trade-flow collector over the PUBLIC websocket (backlog W1, 2026-11-12).

    python -m kripto.flow           # runs forever (systemd: kripto-flow.service, Restart=always)

Why: taker flow is the strongest signal we have on Binance (flow@bn) and it transfers to HL prices before costs, but HL
candles carry no taker split and HL serves no trade history, so this data exists only if we record it as it happens.
What: ONE websocket connection (wss://api.hyperliquid.xyz/ws, public, unauthenticated, read-only; HARD RULE 1 as amended
2026-11-10), `trades` for the top-N coins by 24h volume (re-ranked every 6 h through the public /info endpoint, ≥ 3 s client),
plus `bbo` for a few liquid coins to VERIFY the taker-side field: a trade printed at/above the best ask must be a taker buy.
Output (gitignored): per coin per minute, taker buy/sell notional, trade counts, first/last/high/low price,
  data/hl/flow/YYYY-MM-DD.jsonl while the day is open → compacted to YYYY-MM-DD.parquet after the day ends.
Verification counters (side vs bbo) go into every minute row of the bbo coins (`chk_ok`, `chk_bad`).
Heartbeat: meta `flow_tick` in state/paper.db every minute (scripts/health.py alerts if it is silent for 5 min).
Never touches the trader or any book.
"""
from __future__ import annotations

import asyncio
import collections
import json
import os
import time

import pandas as pd

from . import data

WS_URL = "wss://api.hyperliquid.xyz/ws"
FLOW_DIR = data.DATA / "hl" / "flow"
TOP_N = int(os.environ.get("KRIPTO_FLOW_COINS", "60"))
BBO_COINS = ("BTC", "ETH", "SOL")
RERANK_S = 6 * 3600
GRACE_S = 10            # a minute is written once it ended this many seconds ago (late trades are counted, not lost silently)


class Agg:
    """Per (coin, minute) aggregation, deduplicated by trade id (a reconnect replays recent trades)."""

    def __init__(self):
        self.rows: dict[tuple[str, int], dict] = {}
        self.seen: dict[int, float] = {}
        self.seen_q: collections.deque = collections.deque()
        self.bbo: dict[str, tuple[float, float, int]] = {}
        self.flushed_to = 0          # minutes (epoch min) < this were written
        self.late = 0
        self.replay = 0
        self.since_ms = 0            # trades before the current connection began are a partial snapshot: dropped
        self.n = 0

    def add(self, t: dict, now: float | None = None):
        now = time.time() if now is None else now
        tid = int(t.get("tid", 0))
        if tid:
            if tid in self.seen:
                return
            self.seen[tid] = now
            self.seen_q.append((now, tid))
            while self.seen_q and self.seen_q[0][0] < now - 900:
                self.seen.pop(self.seen_q.popleft()[1], None)
        coin, px, sz, side = t["coin"], float(t["px"]), float(t["sz"]), t["side"]
        if int(t["time"]) < self.since_ms:
            self.replay += 1
            return
        m = int(t["time"]) // 60000
        if m < self.flushed_to:
            self.late += 1
            return
        r = self.rows.get((coin, m))
        if r is None:
            r = self.rows[(coin, m)] = {"coin": coin, "minute": m, "buy_ntl": 0.0, "sell_ntl": 0.0, "n_buy": 0, "n_sell": 0,
                                        "o": px, "h": px, "l": px, "c": px, "chk_ok": 0, "chk_bad": 0}
        ntl = px * sz
        if side == "B":                     # HL: side of the aggressor (verified against bbo below)
            r["buy_ntl"] += ntl
            r["n_buy"] += 1
        else:
            r["sell_ntl"] += ntl
            r["n_sell"] += 1
        r["h"], r["l"], r["c"] = max(r["h"], px), min(r["l"], px), px
        q = self.bbo.get(coin)
        if q and 0 <= int(t["time"]) - q[2] <= 2000:   # only a quote from just BEFORE the trade (messages can race)
            bid, ask, _ = q
            if px >= ask or px <= bid:      # unambiguous prints only
                ok = (px >= ask) == (side == "B")
                r["chk_ok" if ok else "chk_bad"] += 1
        self.n += 1

    def set_bbo(self, coin: str, bid: float, ask: float, t_ms: int = 0):
        self.bbo[coin] = (bid, ask, t_ms)

    def pop_done(self, now: float | None = None) -> list[dict]:
        now = time.time() if now is None else now
        upto = int(now - GRACE_S) // 60          # minutes < upto are complete
        done = [k for k in self.rows if k[1] < upto]
        out = [self.rows.pop(k) for k in sorted(done, key=lambda k: (k[1], k[0]))]
        self.flushed_to = max(self.flushed_to, upto)
        return out


def write_rows(rows: list[dict], d=None):
    d = d or FLOW_DIR
    d.mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        by_day[time.strftime("%Y-%m-%d", time.gmtime(r["minute"] * 60))].append(r)
    for day, rs in by_day.items():
        with (d / f"{day}.jsonl").open("a") as f:
            for r in rs:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")


def log_gap(kind: str, d=None, ts: float | None = None):
    """connect / disconnect times (data/hl/flow/gaps.jsonl): minutes around a gap are partial and must be masked in analysis."""
    d = d or FLOW_DIR
    d.mkdir(parents=True, exist_ok=True)
    with (d / "gaps.jsonl").open("a") as f:
        f.write(json.dumps({"ts": time.time() if ts is None else ts, "event": kind}) + "\n")


def compact(d=None, today: str | None = None):
    """Closed days: JSONL -> parquet (sorted, deduplicated by coin+minute), then the JSONL is removed."""
    d = d or FLOW_DIR
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    for f in sorted(d.glob("*.jsonl")):
        if f.stem >= today:
            continue
        df = pd.read_json(f, lines=True)
        out = d / f"{f.stem}.parquet"
        if out.exists():
            df = pd.concat([pd.read_parquet(out), df])
        df = df.drop_duplicates(["coin", "minute"], keep="last").sort_values(["minute", "coin"]).reset_index(drop=True)
        tmp = out.with_suffix(".tmp")
        df.to_parquet(tmp)
        tmp.replace(out)
        f.unlink()


def top_coins(n: int = TOP_N) -> list[str]:
    from .hl import HL
    uni = data.hl_universe(HL(min_interval=max(3.0, float(os.environ.get("KRIPTO_HL_INTERVAL", "3.0")))))
    uni = uni[~uni["isDelisted"]]
    return list(uni["name"][:n])


def heartbeat(info: dict):
    from . import paper as P
    try:
        P.Store().set_meta("flow_tick", json.dumps(info))
    except Exception as e:      # a locked db must not kill the collector
        print(f"{P.now_iso()} heartbeat failed: {e!r}", flush=True)


async def run_forever():
    import websockets
    agg, coins, ranked_at, reconnects, fails = Agg(), [], 0.0, 0, 0
    while True:
        try:
            if time.time() - ranked_at > RERANK_S or not coins:
                coins = list(dict.fromkeys(top_coins() + list(BBO_COINS)))
                ranked_at = time.time()
            async with websockets.connect(WS_URL, ping_interval=None, max_size=2**22, open_timeout=20) as ws:
                for c in coins:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "trades", "coin": c}}))
                for c in BBO_COINS:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "bbo", "coin": c}}))
                print(f"{time.strftime('%FT%TZ', time.gmtime())} connected, {len(coins)} coins", flush=True)
                fails = 0
                agg.since_ms = int(time.time() * 1000)
                log_gap("connect")
                last_ping = last_flush = time.time()
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        msg = None
                    if msg:
                        m = json.loads(msg)
                        ch = m.get("channel")
                        if ch == "trades":
                            for t in m.get("data", []):
                                agg.add(t)
                        elif ch == "bbo":
                            b = m.get("data", {}).get("bbo") or []
                            if len(b) == 2 and b[0] and b[1]:
                                agg.set_bbo(m["data"]["coin"], float(b[0]["px"]), float(b[1]["px"]), int(m["data"].get("time", 0)))
                    now = time.time()
                    if now - last_ping > 30:              # HL closes idle connections after 60 s
                        await ws.send(json.dumps({"method": "ping"}))
                        last_ping = now
                    if now - last_flush >= 60:
                        rows = agg.pop_done(now)
                        write_rows(rows)
                        compact()
                        last_flush = now
                        ok = sum(r["chk_ok"] for r in rows)
                        bad = sum(r["chk_bad"] for r in rows)
                        heartbeat({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "coins": len(coins),
                                   "rows": len(rows), "trades_total": agg.n, "late": agg.late, "replay": agg.replay, "reconnects": reconnects,
                                   "side_ok": ok, "side_bad": bad})
                    if now - ranked_at > RERANK_S:
                        log_gap("disconnect")
                        break                               # reconnect with the re-ranked coin list
        except Exception as e:
            log_gap("disconnect")
            reconnects, fails = reconnects + 1, fails + 1
            print(f"{time.strftime('%FT%TZ', time.gmtime())} websocket error ({reconnects}): {e!r}", flush=True)
            await asyncio.sleep(min(60, 5 * fails))


def main():
    print(f"flow collector: top {TOP_N} coins, bbo check on {BBO_COINS}, out {FLOW_DIR}", flush=True)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
