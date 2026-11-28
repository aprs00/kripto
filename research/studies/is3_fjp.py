"""FJP: power of the forward judges for FLX2 (main_bn mix with flow i vs iii), NPC2 (blend_nested H4 vs combo, cached bnall), TLQ2 (HL main slow .33 tsmom top20 vs top10).
Daily difference series: corr, sd, AC1, HAC long-run variance, mean, MDE (t = 2) at 90/180 d vs the in-sample gap; cost ratio windows for TLQ2. Not registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fjp -> research/is3/fjp_abc.json"""
import json, pickle
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day


def hac_var(x, L):                      # Newey-West long-run variance (same as is3_prbf.hac_var; that module is a script)
    x = x - x.mean(); v = float((x * x).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((x[l:].to_numpy() * x[:-l].to_numpy()).mean())
    return v


def table(ra, rb, ca=None, cb=None):
    d = (rb - ra).dropna(); lrv = hac_var(d, 10)
    o = {"days": len(d), "corr": round(float(ra.corr(rb)), 3), "sd_diff_bp": round(float(d.std() * 1e4), 1), "ac1": round(float(d.autocorr(1)), 3),
         "mean_diff_bp": round(float(d.mean() * 1e4), 2), "mean_diff_pct_yr": round(float(d.mean() * 365 * 100), 2), "t_full_hac": round(float(d.mean() / np.sqrt(lrv / len(d))), 2),
         "mde_bp": {n: round(2 * np.sqrt(lrv / n) * 1e4, 2) for n in (90, 180, 365)}}
    o["mde_over_gap"] = {n: (round(o["mde_bp"][n] / abs(o["mean_diff_bp"]), 1) if o["mean_diff_bp"] else None) for n in (90, 180, 365)}
    if ca is not None:
        cr = (cb.rolling(90).sum() / ca.rolling(90).sum()).dropna()
        o["cost_ratio_full"] = round(float(cb.sum() / ca.sum()), 3)
        o["cost_ratio_90d"] = {"p10": round(float(cr.quantile(.1)), 3), "p50": round(float(cr.median()), 3), "p90": round(float(cr.quantile(.9)), 3),
                               "share_gt_.85": round(float((cr > .85).mean()), 3)}
    return o


out = {}
# a: FLX2 on bnall 2021-01..2026-10
from research.studies import is3_flxf as X
SB = slice("2021-01-01", "2026-10-31")
wb = S.REGISTRY["blend"](X.p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=X.cols, fill_value=0.0)
mix = {}
for k, mode in (("i", None), ("iii", "resid_f7")):
    wf = X.flow_x(X.p, mode=mode).ffill().fillna(0.0).reindex(columns=X.cols, fill_value=0.0)
    mix[k] = X.run((wf + wb) * 0.5)
out["flx2_iii_minus_i"] = table(mix["i"].returns.loc[SB], mix["iii"].returns.loc[SB], mix["i"].costs.loc[SB], mix["iii"].costs.loc[SB])
print("FLX2", out["flx2_iii_minus_i"], flush=True)
del X, mix, wb
# b: NPC2 on the cached bnall pickle (the NPC/NPC3 panel)
p = pickle.load(open("data/is3/fc1c_bnall_1d.pkl", "rb")); c = p["close"]
slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
books = {}
for sel in ("h4", "combo"):
    comps, s, log = S.nested_selection(p, select=sel)
    tot = sum(comps[n].mul(s[n], axis=0) for n in comps).where(s.sum(axis=1) > 0, 0.0)
    books[sel] = (bt.run(S.scheduled(tot, p, 1, 0.25, 3.0, None).fillna(0.0), c, p.get("funding"), slip, band=0.005), s)
oos = books["h4"][1].index[(books["h4"][1].sum(axis=1) > 0).to_numpy()][0]
SN = slice(max(oos, pd.Timestamp("2021-01-01", tz="UTC")), None)
out["npc2_combo_minus_h4"] = table(books["h4"][0].returns.loc[SN], books["combo"][0].returns.loc[SN], books["h4"][0].costs.loc[SN], books["combo"][0].costs.loc[SN])
diff_rows = (books["h4"][1] - books["combo"][1]).abs().sum(axis=1).loc[SN] > 1e-9
out["npc2_combo_minus_h4"]["share_days_choice_differs"] = round(float(diff_rows.mean()), 3)
print("NPC2", out["npc2_combo_minus_h4"], flush=True)
del p, books
# c: TLQ2 on HL 1d 2023-26
p = data.load_panel("hl", "1d"); slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
R = {}
for tn in (20, 10):
    w = S.REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": ({"top_n": tn} if tn != 20 else {})}, slow_lam=0.33)
    R[tn] = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
SH = slice("2023-01-01", None)
out["tlq2_top10_minus_top20"] = table(R[20].returns.loc[SH], R[10].returns.loc[SH], R[20].costs.loc[SH], R[10].costs.loc[SH])
print("TLQ2", out["tlq2_top10_minus_top20"], flush=True)
json.dump(out, open("research/is3/fjp_abc.json", "w"), indent=1)
