"""Watchdog, rule guard and forward ledger: the pieces that keep the unattended system honest."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from scripts import forward_score as fs
from scripts import guard, health

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
iso = lambda **kw: (NOW - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ok():
    return {"last_run": iso(minutes=20), "last_bar": "2026-11-10 04:00:00+00:00", "bn_last_run": iso(minutes=18),
            "collect": {"ts": iso(minutes=15), "errors": 0}, "events": [], "halted": [], "disk_free_gb": 50.0,
            "sessions": [(iso(hours=4), "review", 0)]}


def test_health_ok_and_each_failure_is_noticed():
    assert health.assess(_ok(), NOW) == ("OK", [])
    f = _ok(); f["last_run"] = iso(hours=3)
    assert health.assess(f, NOW)[0] == "ALERT"
    f = _ok(); f["last_run"] = None
    assert health.assess(f, NOW)[0] == "ALERT"
    f = _ok(); f["collect"] = {"ts": iso(hours=5), "errors": 0}
    level, why = health.assess(f, NOW)
    assert level == "WARN" and "collector" in why[0]
    f = _ok(); f["halted"] = ["main"]
    assert health.assess(f, NOW)[0] == "ALERT"
    f = _ok(); f["events"] = [(iso(minutes=30), "ERROR", "strategy x failed")]
    assert health.assess(f, NOW)[0] == "WARN"
    f = _ok(); f["disk_free_gb"] = 3.0
    assert health.assess(f, NOW)[0] == "ALERT"
    f = _ok(); f["last_bar"] = "2026-11-09 20:00:00+00:00"
    assert health.assess(f, NOW)[0] == "WARN"
    f = _ok(); f["due"] = [("blend_nested", "2099-01-01", "refit")]
    assert health.assess(f, NOW) == ("OK", [])                      # a chore in the future is not a problem
    f = _ok(); f["due"] = [("blend_nested", "2020-01-02", "refit")]
    level, why = health.assess(f, NOW)
    assert level == "WARN" and "blend_nested" in why[0]             # an overdue chore wakes a review


def test_dead_agent_is_an_alert_that_does_not_ask_the_agent_to_fix_itself():
    f = _ok(); f["sessions"] = [(iso(hours=80), "review", 0), (iso(hours=30), "review", 1), (iso(hours=6), "review", 1)]
    level, why = health.assess(f, NOW)
    assert level == "ALERT" and why[0].startswith("agent:") and "login" in why[0]
    assert not health.should_trigger(level, why, {}, NOW)            # starting Claude cannot fix a dead Claude
    out = health.stamp_status("HEALTH: OK — fine\n\nbody\n", "HEALTH: ALERT — agent: dead")
    assert out.splitlines()[0].startswith("HEALTH: ALERT") and health.MARK in out.splitlines()[0] and out.endswith("body\n")
    f = _ok(); f["sessions"] = [(iso(hours=30), "review", 0), (iso(hours=6), "research", 1)]
    assert health.assess(f, NOW)[0] == "WARN"                         # one failed session is not a dead agent


def test_review_is_triggered_once_per_problem_and_again_after_12h():
    why = ["trader has not run for 3.0h"]
    assert health.should_trigger("ALERT", why, {}, NOW)
    prev = {"triggered": iso(hours=1), "triggered_for": why}
    assert not health.should_trigger("ALERT", why, prev, NOW)
    assert health.should_trigger("ALERT", why + ["disk 3.0G free"], prev, NOW)
    assert health.should_trigger("ALERT", why, {"triggered": iso(hours=13), "triggered_for": why}, NOW)
    assert not health.should_trigger("OK", [], prev, NOW)


def test_guard_restores_an_edited_or_deleted_hard_rules_section():
    doc = "# t\n\n## A\nx\n\n## HARD RULES (immutable)\n1. Paper only.\n2. Legal.\n\n## B\ny\n"
    a, b = guard.section(doc)
    saved = doc[a:b]
    assert saved.startswith("## HARD RULES") and saved.endswith("2. Legal.\n\n")
    assert guard.restore(doc, saved) == (doc, False)
    assert guard.restore(doc.replace("1. Paper only.", "1. Paper mostly."), saved) == (doc, True)
    assert guard.restore(doc + "\n## C\nnew section is fine\n", saved)[1] is False
    gone = doc[:a] + doc[b:]
    fixed, changed = guard.restore(gone, saved)
    assert changed and "1. Paper only." in fixed


def test_guard_finds_the_real_section():
    span = guard.section(guard.MANUAL.read_text())
    assert span and "Paper only" in guard.MANUAL.read_text()[span[0]:span[1]]


def test_forward_ledger_uses_only_bars_after_registration(tmp_path):
    assert fs.registered("20261108-1540_carry_bn.json") == pd.Timestamp("2026-11-08 15:40", tz="UTC")
    assert fs.registered("20261109-071001_123_tsmom_hl_1d.json") == pd.Timestamp("2026-11-09 07:10:01", tz="UTC")
    assert fs.registered("notes.json") is None
    idx = pd.date_range("2026-01-01", periods=100, freq="1D", tz="UTC")
    r = pd.Series(0.0, idx)
    r.iloc[:60] = 0.5                      # huge "returns" before registration must not count
    r.iloc[60:] = [0.01, -0.01] * 20
    st = fs.forward_stats(r, idx[60], 365.0)
    assert st["bars"] == 40 and st["days"] == pytest.approx(40.0) and abs(st["ret"]) < 0.01 and st["sharpe"] is not None
    assert fs.forward_stats(r, idx[90], 365.0)["sharpe"] is None      # under 30 days: no Sharpe
    (tmp_path / "20261109-0700_a_hl.json").write_text('{"strategy":"a","dataset":"hl","folds":[{"params":{"x":1}}],"oos":{"sharpe":1.0}}')
    (tmp_path / "20261110-0700_a_hl.json").write_text('{"strategy":"a","dataset":"hl","folds":[{"params":{"x":1}}],"oos":{"sharpe":2.0}}')
    (tmp_path / "20261110-0800_b_hl.json").write_text('{"strategy":"b","dataset":"hl","folds":[]}')
    ex = fs.experiments(tmp_path, known={"a", "b"})
    assert len(ex) == 1 and ex[0]["registered"].day == 9 and ex[0]["backtest_oos_sharpe"] == 1.0   # earliest wins
