"""TLQB a: known answer, blend with tsmom {'top_n': 20} explicit == the shipped config/strategies.json blend_nested params on HL 1d."""
import json
from kripto import data
from kripto.strategies import REGISTRY
cfg = json.load(open("config/strategies.json"))
e = cfg.get("blend_nested") or cfg["strategies"]["blend_nested"]
p = data.load_panel("hl", "1d")
a = REGISTRY[e["strategy"]](p, **e["params"]).fillna(0)
b = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {"top_n": 20}}, slow_lam=0.33).fillna(0)
out = {"shipped_params": e["params"], "maxdw": float((a - b).abs().max().max())}
print(out); json.dump(out, open("research/is3/tlqb_a.json", "w"))
