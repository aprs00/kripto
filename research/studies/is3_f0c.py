"""InSilico pass 3, F0C: HL blend with listing_short's third in cash on idle days vs 200 random day masks. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_f0c hlu_explore     # or hlu_confirm (after L.prereg + commit)
"""
from __future__ import annotations

import sys
from functools import partial

from kripto import strategies as S
from research.studies import is3_filter as F

COMPS = {"listing_short": {}, "lowvol": {}, "tsmom": {}}


def main(sample):
    w, panel, slip = F.book("blend", "hl", {"components": COMPS})
    wls = S.REGISTRY["listing_short"](panel).ffill().fillna(0.0)
    active = ((wls.drop(columns=["BTC"], errors="ignore") < 0).sum(axis=1) > 0)       # decided at the same bar as the blend's row
    F.judge("F0C", w, panel, slip, active, sample, tf=partial(F.scale, k=2 / 3), note="mask = listing_short holds >= 1 name; blocked (idle) rows x 2/3")


if __name__ == "__main__":
    main(sys.argv[1])
