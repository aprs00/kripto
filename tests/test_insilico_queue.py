"""The InSilico queue must make the 2026-11-15 mistake impossible: a verdict while planned forms have no outcome."""
import json

import pytest

from scripts import insilico_queue as q


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "FILE", tmp_path / "queue.json")
    monkeypatch.setattr(q, "EVID", tmp_path / "is3")
    monkeypatch.setattr(q, "PAUSE", tmp_path / "insilico.paused")
    (tmp_path / "is3").mkdir()
    items = [
        {"id": "A1", "title": "first", "prio": 1, "status": "todo", "forms": [{"id": k, "what": k, "status": "planned"} for k in "abc"]},
        {"id": "A2", "title": "later", "prio": 2, "status": "todo", "due": "2026-12-07", "forms": [{"id": "a", "what": "x", "status": "planned"}]},
        {"id": "A3", "title": "needs A1", "prio": 3, "status": "todo", "after": ["A1"], "forms": [{"id": "a", "what": "x", "status": "planned"}]}]
    q.save({"items": items})
    return tmp_path


def evidence(env, name):
    (env / "is3" / f"{name}.json").write_text("{}")
    return name


def test_next_respects_priority_due_dates_and_dependencies(env):
    assert q.next_item("2026-11-23")["id"] == "A1"
    for k in "abc":
        q.form("A1", k, "done", "r", evidence(env, f"A1{k}__explore"))
    q.close("A1", "DEAD", "diagnosed: costs")
    assert q.next_item("2026-11-23")["id"] == "A3"
    assert q.next_item("2026-12-07")["id"] == "A2"


def test_no_verdict_while_a_planned_form_has_no_outcome(env):
    q.form("A1", "a", "done", "r", evidence(env, "A1a__explore"))
    with pytest.raises(SystemExit, match="no outcome"):
        q.close("A1", "DEAD", "because")


def test_dead_needs_three_evidenced_forms_and_skips_do_not_count(env):
    for k in "ab":
        q.form("A1", k, "done", "r", evidence(env, f"A1{k}__explore"))
    q.form("A1", "c", "skipped", "no data", None)
    with pytest.raises(SystemExit, match="three"):
        q.close("A1", "DEAD", "because")
    q.close("A1", "OPEN", "c untested")


def test_done_form_needs_an_evidence_file_and_confirmed_needs_a_confirm_card(env):
    with pytest.raises(SystemExit, match="evidence"):
        q.form("A1", "a", "done", "r", "nope")
    for k in "abc":
        q.form("A1", k, "done", "r", evidence(env, f"A1{k}__explore"))
    with pytest.raises(SystemExit, match="confirm"):
        q.close("A1", "CONFIRMED", "looks good")
    evidence(env, "A1a__confirmC")
    q.close("A1", "CONFIRMED", "held out ok")


def test_pause_and_nothing_due_both_stop_the_session(env):
    assert q.should_run("2026-11-23") == (True, "A1")
    (env / "insilico.paused").write_text("")
    assert q.should_run("2026-11-23")[0] is False
    (env / "insilico.paused").unlink()
    d = q.load()
    for it in d["items"]:
        it["status"] = "closed"
    q.save(d)
    assert q.should_run("2026-12-31")[0] is False


def test_an_item_that_eats_four_sessions_goes_to_the_back(env):
    for _ in range(4):
        q.start("A1")
    assert q.next_item("2026-12-07")["id"] == "A2"
    assert q.get(q.load(), "A1")["status"] == "wip"


def test_real_queue_ids_are_unique():
    """2026-11-28: a refill reused the id FLD of a closed item; `start/form/close` then wrote into the OLD item (first match).
    Every refill runs this file, so a duplicate id now fails before it is committed."""
    from pathlib import Path
    items = json.loads((Path(__file__).resolve().parents[1] / "research" / "insilico_queue.json").read_text())["items"]
    ids = [it["id"] for it in items]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f"duplicate InSilico item ids: {dup} (pick a new id; commands act on the first match)"
