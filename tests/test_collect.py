"""T6a collector: discovery -> snapshot selection -> JSONL outputs, with a fake /info client (no network)."""
import json

from kripto import collect


class FakeHL:
    def __init__(self):
        self.calls = []

    def post(self, body):
        self.calls.append(body["type"])
        if body["type"] == "recentTrades":
            return [{"px": "100", "sz": "10", "users": ["0xbig", "0xsmall"]},
                    {"px": "100", "sz": "1", "users": ["0xsmall", "0xmid"]}]
        if body["type"] == "clearinghouseState":
            av = {"0xbig": "5000000", "0xmid": "1000", "0xsmall": "10"}[body["user"]]
            return {"marginSummary": {"accountValue": av, "totalNtlPos": "1"},
                    "assetPositions": [{"position": {"coin": "BTC", "szi": "-1.5", "entryPx": "100",
                                                     "positionValue": "150", "unrealizedPnl": "1",
                                                     "leverage": {"value": 5}, "liquidationPx": "200"}}]}
        raise AssertionError(body)

    def l2_book(self, coin):
        self.calls.append("l2Book")
        return {"levels": [[{"px": "99", "sz": "1", "n": 2}] * 15, [{"px": "101", "sz": "2", "n": 1}] * 15]}


def test_collect_writes_positions_l2_and_address_book(tmp_path):
    hl = FakeHL()
    n = collect.collect(hl, ["BTC", "ETH"], n_disc=1, n_l2=2, n_track=1, n_explore=2,
                        pos_dir=tmp_path / "pos", l2_dir=tmp_path / "l2")
    assert n["errors"] == 0 and n["new_addr"] == 3 and n["snaps"] == 2 and n["l2"] == 2
    assert hl.calls.count("recentTrades") == 1 and hl.calls.count("clearinghouseState") == 2
    book = json.loads((tmp_path / "pos" / "addresses.json").read_text())
    # first pass: nothing known yet, so the 2 highest-notional addresses are explored (0xbig=1000, 0xsmall=1100)
    assert book["0xsmall"]["av"] == "10" and book["0xbig"]["av"] == "5000000" and book["0xmid"]["av"] is None
    recs = [json.loads(l) for f in (tmp_path / "pos").glob("*.jsonl") for l in f.read_text().splitlines()]
    assert recs[0]["pos"][0][:2] == ["BTC", "-1.5"]
    l2 = [json.loads(l) for f in (tmp_path / "l2").glob("*.jsonl") for l in f.read_text().splitlines()]
    assert len(l2) == 2 and len(l2[0]["bids"]) == collect.L2_LEVELS
    # second pass: the largest known account is tracked, the unexplored one gets explored
    assert collect.pick_addresses(book, 1, 1) == ["0xbig", "0xmid"]


def test_collect_respects_deadline(tmp_path):
    hl = FakeHL()
    n = collect.collect(hl, ["BTC"], deadline_s=0.0, pos_dir=tmp_path / "pos", l2_dir=tmp_path / "l2")
    assert hl.calls == [] and n["snaps"] == 0
