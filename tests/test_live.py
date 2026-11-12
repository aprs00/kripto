"""Always-on watcher: values open books every tick, kills only on a confirmed drawdown with every coin priced."""
import json

import pandas as pd
import pytest

from kripto import live, paper as P

RISK = {"kill_drawdown": 0.25}


def _store(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DB", tmp_path / "p.db")
    s = P.Store(tmp_path / "p.db")
    s.ensure_book("shadow:a", 2000.0)          # long 10 X bought at 100: cash 1000 + 10 * mark
    s.x("update books set cash=1000.0 where name='shadow:a'")
    s.x("insert into positions values('shadow:a','X',10.0)")
    s.ensure_book("shadow:b@bn", 2000.0)       # Binance book, flat
    s.ensure_book("small:a", 200.0)
    s.x("update books set cash=100.0 where name='small:a'")
    s.x("insert into positions values('small:a','X',1.0)")
    return s


def _venue(name, marks, log):
    def flatten(store, book, m):
        log.append(book)
        P.rebalance(None, store, book, pd.Series(dtype=float), m, {}, "kill_switch", fill=lambda c, d: (m[c], m[c], 0.0))
    return live.Venue(name, lambda: dict(marks), flatten)


def test_tick_values_books_tracks_the_peak_and_writes_a_heartbeat(tmp_path, monkeypatch):
    s, marks, log, state = _store(tmp_path, monkeypatch), {"X": 100.0}, [], {}
    v = [_venue("hl", marks, log), _venue("bn", {"X": 1.0}, log)]
    out = live.tick(s, RISK, v, state, now=1000.0)
    assert out["open_books"] == 2 and out["killed"] == [] and out["worst_dd"] == 0.0     # flat Binance book is not counted
    marks["X"] = 120.0
    live.tick(s, RISK, v, state, now=1020.0)
    assert s.q("select peak from books where name='shadow:a'") == [(2200.0,)]            # true intra-hour peak
    assert json.loads(s.get_meta("live_tick"))["open_books"] == 2
    assert s.q("select count(*) from equity where book='shadow:a'") == [(1,)]            # one row per EQUITY_EVERY, not per tick
    live.tick(s, RISK, v, state, now=1000.0 + live.EQUITY_EVERY + 1)
    assert s.q("select count(*) from equity where book='shadow:a'") == [(2,)]


def test_kill_needs_a_confirmed_breach_then_flattens_and_halts_at_once(tmp_path, monkeypatch):
    s, marks, log, state = _store(tmp_path, monkeypatch), {"X": 100.0}, [], {}
    v = [_venue("hl", marks, log)]
    live.tick(s, RISK, v, state, now=0.0)
    marks["X"] = 40.0                           # shadow:a equity 1400 = -30% from 2000: beyond the 25% stop
    out = live.tick(s, RISK, v, state, now=20.0)
    assert out["killed"] == [] and log == []    # first breaching tick: wait for confirmation
    marks["X"] = 100.0
    live.tick(s, RISK, v, state, now=40.0)      # a single bad print that recovers never kills
    marks["X"] = 40.0
    live.tick(s, RISK, v, state, now=60.0)
    out = live.tick(s, RISK, v, state, now=80.0)
    assert set(out["killed"]) == {"shadow:a", "small:a"} and set(log) == {"shadow:a", "small:a"}
    assert not s.positions("shadow:a") and s.q("select halted from books where name='shadow:a'") == [(1,)]
    assert s.q("select count(*) from events where level='ALERT'") == [(2,)]
    assert s.q("select count(*) from fills where reason='kill_switch'") == [(2,)]
    out = live.tick(s, RISK, v, state, now=100.0)
    assert out["killed"] == [] and out["open_books"] == 0          # halted books are left alone


def test_missing_mark_or_unreachable_venue_never_moves_a_book(tmp_path, monkeypatch):
    s, log, state = _store(tmp_path, monkeypatch), [], {}
    out = live.tick(s, RISK, [_venue("hl", {}, log)], state, now=0.0)      # X has no price
    out = live.tick(s, RISK, [_venue("hl", {"X": 0.0}, log)], state, now=20.0)
    assert out["nomark"] == 2 and out["open_books"] == 0 and log == []
    assert s.q("select peak, halted from books where name='shadow:a'") == [(2000.0, 0)]

    def boom():
        raise RuntimeError("down")
    out = live.tick(s, RISK, [live.Venue("hl", boom, None)], state, now=40.0)
    assert out["errors"] and log == [] and s.positions("shadow:a") == {"X": 10.0}


def test_fill_is_one_transaction_and_hourly_kill_ignores_unpriced_books(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError):            # a failure inside a fill leaves cash and positions untouched
        class Boom:
            def __getattr__(self, k):
                raise RuntimeError("db")
        real = s.c
        P.rebalance(None, s, "shadow:a", pd.Series({"X": 0.0}), {"X": 100.0}, {}, "t",
                    fill=lambda c, d: (_ for _ in ()).throw(RuntimeError("no book")))
    assert s.positions("shadow:a") == {"X": 10.0} and s.cash("shadow:a") == 1000.0
    calls = []
    entries = {"a": {"status": "candidate"}}
    risk = {"start_equity": 1000.0, "shadow_equity": 2000.0, "kill_drawdown": 0.25, "max_asset_weight": 1.0, "max_gross": 3.0}
    P.run_books(s, entries, risk, {}, {}, "bar1", "main", lambda b, t, r: calls.append((b, r)))   # no mark for X at all
    assert ("shadow:a", "kill_switch") not in calls and s.q("select halted from books where name='shadow:a'") == [(0,)]


def test_pair_venue_prices_both_legs_from_this_ticks_marks(tmp_path, monkeypatch):
    s = P.Store(tmp_path / "p.db")
    monkeypatch.setattr(P, "DB", tmp_path / "p.db")
    s.ensure_book("shadow:f@pair", 2000.0)
    s.x("insert into positions values('shadow:f@pair','kPEPE@hl',-1000.0)")
    s.x("insert into positions values('shadow:f@pair','kPEPE@bn',1000.0)")
    log = []
    pv = live.pair_venue(None, None)
    v = [_venue("hl", {"kPEPE": 0.01}, log), _venue("bn", {"1000PEPE": 0.011}, log), pv]
    out = live.tick(s, RISK, v, {}, now=0.0)
    assert out["open_books"] == 1 and out["nomark"] == 0 and out["errors"] == []
    assert P.book_venue("shadow:f@pair") == "pair"
    with pytest.raises(RuntimeError):     # one venue missing -> no partial marks
        pv.marks({"hl": {"kPEPE": 0.01}})
