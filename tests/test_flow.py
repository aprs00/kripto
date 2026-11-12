"""W1 trade-flow collector: aggregation, dedup on reconnect replay, side check, day compaction (no network)."""
import json

import pandas as pd
import pytest

from kripto import flow as F

T0 = 1_794_000_000_000 - 1_794_000_000_000 % 60000     # a minute boundary (ms)


def _t(tid, ms, side, px=100.0, sz=1.0, coin="BTC"):
    return {"coin": coin, "side": side, "px": str(px), "sz": str(sz), "time": ms, "tid": tid}


def test_minute_rows_sum_taker_sides_and_ignore_replays():
    a = F.Agg()
    a.set_bbo("BTC", 99.0, 101.0, T0 + 500)
    a.add(_t(1, T0 + 1000, "B", px=101.0, sz=2.0), now=T0 / 1000)    # at the ask, buyer: consistent
    a.add(_t(2, T0 + 2000, "A", px=99.0, sz=1.0), now=T0 / 1000)     # at the bid, seller: consistent
    a.add(_t(3, T0 + 1500, "A", px=101.0, sz=1.0), now=T0 / 1000)    # at the ask but "seller": inconsistent
    a.add(_t(1, T0 + 1000, "B", px=101.0, sz=2.0), now=T0 / 1000)    # replay after reconnect: ignored
    a.add(_t(4, T0 + 61000, "B", px=100.0, coin="ETH"), now=T0 / 1000)
    rows = a.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)        # first minute complete, second not
    assert len(rows) == 1
    r = rows[0]
    assert r["buy_ntl"] == pytest.approx(202.0) and r["sell_ntl"] == pytest.approx(99.0 + 101.0)
    assert (r["n_buy"], r["n_sell"], r["chk_ok"], r["chk_bad"]) == (1, 2, 2, 1)
    assert (r["o"], r["h"], r["l"], r["c"]) == (101.0, 101.0, 99.0, 101.0)
    a.add(_t(5, T0 + 5000, "B"), now=T0 / 1000 + 100)                 # belongs to a flushed minute
    assert a.late == 1


def test_compact_turns_closed_days_into_parquet(tmp_path):
    rows = [{"coin": "BTC", "minute": T0 // 60000, "buy_ntl": 1.0, "sell_ntl": 2.0, "n_buy": 1, "n_sell": 1,
             "o": 1, "h": 1, "l": 1, "c": 1, "chk_ok": 0, "chk_bad": 0}]
    F.write_rows(rows, tmp_path)
    F.write_rows(rows, tmp_path)                                        # duplicate line -> deduplicated
    day = pd.Timestamp(T0, unit="ms").strftime("%Y-%m-%d")
    F.compact(tmp_path, today=day)                                      # the day is still open: untouched
    assert (tmp_path / f"{day}.jsonl").exists()
    F.compact(tmp_path, today="2999-01-01")
    df = pd.read_parquet(tmp_path / f"{day}.parquet")
    assert len(df) == 1 and not (tmp_path / f"{day}.jsonl").exists()


def test_trades_from_before_the_connection_are_a_partial_snapshot_and_dropped():
    a = F.Agg()
    a.since_ms = T0 + 30000
    a.add(_t(1, T0 + 1000, "B"), now=T0 / 1000)
    a.add(_t(2, T0 + 31000, "B"), now=T0 / 1000)
    assert a.replay == 1 and a.n == 1


def test_side_check_ignores_quotes_from_after_the_trade():
    a = F.Agg()
    a.set_bbo("BTC", 99.0, 101.0, T0 + 5000)
    a.add(_t(1, T0 + 1000, "A", px=101.0), now=T0 / 1000)
    r = a.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)[0]
    assert (r["chk_ok"], r["chk_bad"]) == (0, 0)


def test_side_check_uses_the_quote_from_before_the_trades_block():
    a = F.Agg()
    a.set_bbo("BTC", 99.0, 100.0, T0)              # before: bid 99, ask 100
    a.set_bbo("BTC", 98.0, 99.0, T0 + 1000)        # same block as the sell below: the 99 bid was taken, 99 is the new ask
    a.add(_t(1, T0 + 1000, "A", px=99.0), now=T0 / 1000)
    r = a.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)[0]
    assert (r["chk_ok"], r["chk_bad"]) == (1, 0)


def test_large_takers_are_recorded_by_address():
    a = F.Agg()
    t1 = _t(1, T0 + 1000, "B", px=100.0, sz=300.0); t1["users"] = ["0xbuyer", "0xmaker"]
    t2 = _t(2, T0 + 2000, "A", px=100.0, sz=10.0); t2["users"] = ["0xmaker2", "0xsmall"]
    a.add(t1, now=T0 / 1000); a.add(t2, now=T0 / 1000)
    r = a.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)[0]
    assert r["n_takers"] == 2 and "_tk" not in r
    assert json.loads(r["big"]) == [["0xbuyer", 30000.0]]          # the $1,000 seller is below BIG_NTL


def test_trade_size_buckets_use_each_takers_net_per_minute():
    from kripto import tsize
    assert F.TS_EDGES == list(tsize.EDGES)
    a = F.Agg()
    u = lambda tid, ms, side, sz, buyer, seller: {**_t(tid, ms, side, px=100.0, sz=sz), "users": [buyer, seller]}
    a.add(u(1, T0 + 1000, "B", 300.0, "0xbig", "0xm1"), now=T0 / 1000)      # 0xbig buys 30k ...
    a.add(u(2, T0 + 1100, "B", 300.0, "0xbig", "0xm2"), now=T0 / 1000)      # ... and 30k more from another maker: ONE 60k order
    a.add(u(3, T0 + 2000, "A", 5.0, "0xm3", "0xsmall"), now=T0 / 1000)      # 0xsmall sells 500
    a.add(u(4, T0 + 3000, "A", 8.0, "0xm3", "0xsmall2"), now=T0 / 1000)     # 0xsmall2 sells 800
    (r,) = a.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)
    assert json.loads(r["tsz"]) == [[0, -1300.0, 1300.0], [6, 60000.0, 60000.0]]   # bin 6 = [60k, 110k)
    b = F.Agg()
    b.add(_t(9, T0 + 1000, "B"), now=T0 / 1000)                             # a print without addresses: no buckets, no crash
    assert b.pop_done(now=(T0 + 60000) / 1000 + F.GRACE_S + 1)[0]["tsz"] == ""
