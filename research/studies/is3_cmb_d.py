"""CMB d: TSB band .02 slow-leg form under the $10-at-$1,000 min-order rule vs lam1 and slow33 under it."""
import json
from research.studies import is3_cmb as C
from research.studies.is3_tsb import banded
l1, s33 = C.books(1.0)
fin, ref, _ = C.PRL.legs(C.p)
b02 = fin["listing_short"] + banded(fin["lowvol"] + fin["tsmom"], 0.02)
out = {"band02_min10": C.stats(C.minorder(b02))}
print({y: (round(x["sr"], 2), round(x["costs_ann"], 3)) for y, x in out["band02_min10"].items()}, flush=True)
json.dump(out, open("research/is3/cmb_d.json", "w"), indent=1)
