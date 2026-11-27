"""InSilico pass 3, HLD b: builder-deployed perp dexes on Hyperliquid (public info endpoint, >= 3 s between calls). Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is3_hld b   # -> research/is3/hld_b.json
"""
from __future__ import annotations

import json
import sys

from kripto.hl import HL


def run_b():
    hl = HL(min_interval=3.0)
    dexes = hl.post({"type": "perpDexs"})
    out = {"n_dexes_raw": len(dexes) if isinstance(dexes, list) else None, "dexes": []}
    for d in (dexes or []):
        if not d:                                  # the first entry is the main dex (null)
            continue
        name = d.get("name")
        try:
            r = hl.post({"type": "metaAndAssetCtxs", "dex": name})
            uni, ctx = r[0]["universe"], r[1]
            vols = sorted(((u["name"], float(c.get("dayNtlVlm", 0) or 0)) for u, c in zip(uni, ctx)), key=lambda x: -x[1])
            out["dexes"].append({"name": name, "full_name": d.get("fullName"), "n_perps": len(uni), "day_ntl_vlm_total": round(sum(v for _, v in vols), 0),
                                 "n_perps_over_1m_24h": sum(v >= 1e6 for _, v in vols), "top5": [[a, round(b, 0)] for a, b in vols[:5]]})
        except Exception as e:
            out["dexes"].append({"name": name, "error": repr(e)[:200]})
        print(out["dexes"][-1], flush=True)
        if len(out["dexes"]) >= 12:                # a handful of calls only (HARD RULE 2: shared IP)
            out["truncated"] = True
            break
    json.dump(out, open("research/is3/hld_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"b": run_b}[sys.argv[1]]()
