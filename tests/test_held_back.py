import json

from scripts import held_back as hb


def _res(root, name, pick, avg, dsr, worst, grid):
    d = root / "research" / "results"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"20261101-000000_1_{name}.json").write_text(json.dumps(
        {"oos": {"sharpe": pick, "dsr": dsr}, "oos_grid_avg": avg, "n_configs": len(grid), "grid_median_sharpe": None,
         "robust": {"worst": worst, "params": {"sign": 1} if "sign" in grid[0] else {}}, "grid": grid}))


def test_passer_not_trading_is_flagged_and_mixed_sign_grid_handled(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "strategies.json").write_text(json.dumps({
        "good@bn": {"strategy": "good", "venue": "bn", "status": "candidate", "alloc": 0.0},
        "traded@bn": {"strategy": "traded", "venue": "bn", "status": "incubation", "alloc": 0.5},
        "weak@bn": {"strategy": "weak", "venue": "bn", "status": "candidate", "alloc": 0.0},
        "old": {"status": "retired", "alloc": 0.0}}))
    _res(tmp_path, "good_bnall_1d", 1.5, 1.4, 0.95, 1.2, [{"sharpe": 1.0}, {"sharpe": 1.2}])
    _res(tmp_path, "traded_bnall_1d", 1.5, -15.0, 0.95, 1.2,      # mixed-sign grid: the stored average is meaningless
         [{"sign": 1, "sharpe": 1.0}, {"sign": 1, "sharpe": 1.1}, {"sign": -1, "sharpe": -1.5}, {"sign": -1, "sharpe": -1.6}])
    _res(tmp_path, "weak_bnall_1d", 1.5, 1.4, 0.6, 1.2, [{"sharpe": 1.0}])
    (tmp_path / "research" / "gate_evidence.json").write_text(json.dumps({"traded@bn": {"grid_avg": 1.2, "source": "test"}}))
    rows = {r["name"]: r for r in hb.table(tmp_path)}
    assert set(rows) == {"good@bn", "traded@bn", "weak@bn"}
    assert rows["good@bn"]["held_back_unwritten"] and rows["good@bn"]["fails"] == []
    assert rows["traded@bn"]["fails"] == [] and rows["traded@bn"]["grid_med"] == 1.05 and not rows["traded@bn"]["held_back_unwritten"]
    assert rows["weak@bn"]["fails"] == ["DSR>0.9"] and not rows["weak@bn"]["held_back_unwritten"]
    assert "HELD BACK WITHOUT A WRITTEN CLAUSE" in hb.render(list(rows.values()))
