"""InSilico pass 3, E2 d: is the ladder short crash insurance? Its daily P&L vs the main_bn mix (flow, xsmom, blend on bnall 1d) and BTC in their worst weeks; size bounds.

  nice -n 19 .venv/bin/python -m research.studies.is3_e2d
"""
from __future__ import annotations

import json
import json as _j

import numpy as np
import pandas as pd

from kripto import data, research
from research.studies import is3_e2 as E
from research.studies import is3_e2risk as RK


def main():
    cfg = _j.load(open("config/strategies.json"))
    panel = data.load_panel("bnall", "1d")
    mix = {}
    for e in ("flow@bn", "xsmom@bn", "blend@bn"):
        c = cfg[e]
        res, _ = research.evaluate(c["strategy"], panel, c.get("params", {}), "bnall", tag="E2d")
        mix[e] = res.returns
    btc = panel["close"]["BTC"].pct_change() if "BTC" in panel["close"] else None
    del panel
    M = pd.DataFrame(mix)
    M.index = pd.to_datetime(M.index, utc=True).floor("D")
    t = RK.fills().reset_index(names="fid")
    k = RK.kept(t)
    lad = RK.booked(k)
    df = pd.DataFrame({"ladder": lad, "mix": M.mean(axis=1), "btc": btc.reindex(lad.index) if btc is not None else np.nan}).dropna(subset=["mix"])
    df = df[(df.index >= E.LO) & (df.index < E.HI)].fillna(0.0)
    W = df.resample("W").sum()
    out = {"days": len(df), "weekly_corr": W.corr().round(2).to_dict(), "daily_corr": df.corr().round(2).to_dict()}
    for col in ("mix", "btc"):
        w = W.nsmallest(20, col)
        out[f"worst20_{col}"] = {"ladder_sum": round(float(w.ladder.sum()), 4), "ladder_mean": round(float(w.ladder.mean()), 4), "ladder_neg_weeks": int((w.ladder < 0).sum()),
                                 f"{col}_sum": round(float(w[col].sum()), 4), "mix_plus_ladder_sum": round(float((w.mix + w.ladder).sum()), 4)}
    out["ladder_total"] = round(float(df.ladder.sum()), 4)
    out["ladder_worst_weeks"] = {str(i.date()): round(float(v), 4) for i, v in W.ladder.nsmallest(5).items()}
    # size bounds
    nmax = int(k.groupby("time").size().max())
    out["size_worstcase"] = {"largest_batch": nmax, "f_for_minus25_at_50pct_loss": round(0.25 / (nmax * 0.5), 4)}
    mu, var = df.ladder.mean(), df.ladder.var()
    out["size_kelly"] = {"kelly_mult_of_5pct": round(float(mu / var), 2), "half_kelly_f": round(float(0.05 * 0.5 * mu / var), 4)}
    # worst real batch outcome per fill (the -50% case vs history)
    out["worst_fill_h60"] = round(float(k.h60.min()), 4)
    print(json.dumps(out, indent=1))
    (E.OUT / "e2d.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
