"""NPCB b: known answer, strategies.nested_selection(select='combo') == research/studies/is3_npc3 size3 at every refit; default unchanged.
python -m research.studies.is3_npcb hl|<bnall pickle> -> research/is3/npcb_<venue>.json"""
import json, sys
import numpy as np
from research.studies import is3_npc3 as N          # runs the study once (it is a script) and leaves its state
from kripto import strategies as S
sel_study, _, _ = N.select(3, False)
_, sel_prod, log = S.nested_selection(N.p, select="combo")
_, sel_h4, _ = S.nested_selection(N.p)
d = float((sel_study.reindex_like(sel_prod).fillna(0) - sel_prod).abs().max().max())
dh = float((N.sel_std - sel_h4).abs().max().max())
_, _, lg = S.nested_selection(N.p, select="combo")
out = {"venue": N.tag, "maxdiff_combo_vs_study": d, "maxdiff_h4_vs_before": dh, "last_choice": [str(lg[-1][0].date()), lg[-1][1]]}
print(out); json.dump(out, open(f"research/is3/npcb_{N.tag}.json", "w"), default=str)
