from scripts.twin_deployed import table


def test_deployed_share_by_hand():
    rows = {"main": (1000.0, 700.0, 26), "small:main": (200.0, 28.0, 1), "shadow:flow@bn": (2000.0, 2000.0, 30), "small:flow@bn": (200.0, 0.0, 0),
            "main_bn": (1000.0, 500.0, 20)}
    t = {r["twin"]: r for r in table(rows)}
    assert t["small:main"]["deployed"] == round((28 / 200) / (700 / 1000), 2) == 0.2
    assert t["small:flow@bn"]["deployed"] == 0.0
    assert "small:main_bn" not in t                  # no twin row, nothing reported
