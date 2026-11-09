import json

from kripto import research


def test_n_trials_counts_by_kind(tmp_path, monkeypatch):
    reg = tmp_path / "registry.jsonl"
    monkeypatch.setattr(research, "REG", reg)
    assert research.n_trials() == 1 and research.n_trials("walk_forward") == 1  # empty/missing registry
    lines = [{"strategy": "a", "params": {}}] * 5 + [{"kind": "walk_forward", "strategy": "a"}] * 2
    reg.write_text("".join(json.dumps(x) + "\n" for x in lines))
    assert research.n_trials() == 5
    assert research.n_trials("config") == 5
    assert research.n_trials("walk_forward") == 2
