"""InSilico pass 3, HTN a: standalone tsmom turnover per coin by liquidity / vol tercile, HL vs cached bnall. Descriptive."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data, strategies as S
from kripto.strategies import REGISTRY


def decomp(p, lo):
    w = REGISTRY["tsmom"](p).fillna(0.0)
    w = w[w.index >= pd.Timestamp(lo, tz="UTC")]
    dw = w.diff().abs().iloc[1:]
    dv = S.dollar_volume(p).reindex_like(dw)
    vol = S.ann_vol(p).reindex_like(dw)
    held = w.iloc[1:].abs() > 0
    out = {"turnover_ann": float(dw.sum(1).mean() * 365), "names_held_median": float(held.sum(1).median()),
           "median_vol_held": float(vol.where(held).stack().median()), "median_dv_held_musd": float(dv.where(held).stack().median() / 1e6)}
    # terciles within held names each day
    for lab, x in (("vol", vol), ("dv", dv)):
        rk = x.where(held).rank(axis=1, pct=True)
        sh = {}
        for t, (a, b) in enumerate(((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01))):
            m = (rk > a) & (rk <= b)
            sh[f"t{t+1}"] = float(dw.where(m).sum().sum() / dw.where(held | held.shift(1, fill_value=False)).sum().sum())
        out[f"turnover_share_by_{lab}_tercile"] = sh
    # turnover from entries/exits (held changes) vs resizing
    ent = (held != held.shift(1, fill_value=False))
    out["share_from_entry_exit"] = float(dw.where(ent).sum().sum() / dw.sum().sum())
    return out


if __name__ == "__main__":
    res = {"hl_2023_26": decomp(data.load_panel("hl", "1d"), "2023-01-01"), "bnall_2021_26": decomp(pickle.load(open(sys.argv[1], "rb")), "2021-01-01")}
    for k, v in res.items():
        print(k, json.dumps(v), flush=True)
    json.dump(res, open("research/is3/htn_a.json", "w"), indent=1)
