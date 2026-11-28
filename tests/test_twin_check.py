"""TWC 2026-11-28: twin / hedge integrity known answers."""
from scripts.twin_check import violations


def test_pair_legs_and_twins():
    rows = [("main@pair", "AAA@hl", -10), ("main@pair", "AAA@bn", 10),
            ("small:main@pair", "AAA@hl", -2), ("small:main@pair", "AAA@bn", 2),
            ("small:main@pair", "GRAM@bn", -10.2),                        # one-legged (the 11-28 case) and absent in the big book
            ("shadow:x@pair", "BBB@hl", 5), ("shadow:x@pair", "BBB@bn", 4),   # same sign
            ("shadow:y@pair", "CCC@hl", -10), ("shadow:y@pair", "CCC@bn", 3),  # unbalanced
            ("main", "BTC", 0.01), ("small:main", "BTC", 0.002), ("small:main", "ETH", -0.1),
            ("shadow:flow@bn", "SOL", 1.0), ("small:flow@bn", "SOL", -0.2)]
    v = violations(rows)
    assert any("one-legged pair GRAM@bn" in x for x in v)
    assert any("small:main@pair: holds GRAM@bn" in x for x in v)
    assert any("same-sign pair BBB" in x for x in v)
    assert any("unbalanced pair CCC" in x for x in v)
    assert any("small:main: holds ETH" in x for x in v)
    assert any("small:flow@bn: holds SOL" in x for x in v)
    assert not any("AAA" in x for x in v) and not any("BTC" in x for x in v)
    assert violations([("main", "BTC", 1.0), ("small:main", "BTC", 0.1)]) == []


def test_health_warns_on_twin_problems():
    from datetime import datetime, timezone
    from scripts import health
    now = datetime(2026, 11, 28, 13, tzinfo=timezone.utc)
    base = {"last_run": "2026-11-28T12:55:00Z", "disk_free_gb": 50, "events": [], "halted": [], "sessions": []}
    lvl, why = health.assess({**base, "twins": ["small:main@pair: one-legged pair GRAM@bn -10.2 (no hl hedge)"]}, now)
    assert any("twin/hedge integrity" in w for w in why)
    lvl0, why0 = health.assess({**base, "twins": []}, now)
    assert not any("twin/hedge" in w for w in why0)
