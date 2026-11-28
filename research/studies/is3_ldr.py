"""LDR: HL main (live components listing_short + lowvol + tsmom, slow_lam .33) per quarter 2023-26: listing_short names/day, legs' gross share, the blend's scale k_t,
book vol / SR, leg P&L attribution with k_t (BNH method). Descriptive, NOT registered. PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_ldr -> research/is3/ldr_ab.json"""
import inspect, json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day

COMPS = {"listing_short": {}, "lowvol": {}, "tsmom": {}}
p = data.load_panel("hl", "1d"); c = p["close"]
ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
parts, names = {}, {}
for n, prm in COMPS.items():
    tv = inspect.signature(S.REGISTRY[n]).parameters["target_vol"].default
    w = S._ffill_targets(S.REGISTRY[n](p, **prm)).reindex(columns=c.columns, fill_value=0.0).fillna(0.0) * (0.20 / tv)
    names[n] = (w != 0).sum(axis=1)
    if n in S.SLOW_LEGS:
        w = S.partial_path(w, 0.33, 1)
    parts[n] = w / len(COMPS)
raw = sum(parts.values())
wb = S.REGISTRY["blend"](p, components=COMPS, slow_lam=0.33).ffill().fillna(0.0).reindex(columns=c.columns, fill_value=0.0)
res = bt.run(wb, c, p["funding"], bt.slippage_model(p["volume"], bars_per_day(c.index)), band=0.005)
k = (wb.abs().sum(axis=1) / raw.abs().sum(axis=1).replace(0, np.nan)).fillna(0.0)
contrib = {}
for n, w in parts.items():
    wl = w.mul(k, axis=0).shift(1).fillna(0.0)
    contrib[n] = (wl * ret).sum(axis=1) - (wl * fund).sum(axis=1)
r = res.returns; start = res.gross[res.gross > 0].index.min(); r = r[r.index >= start]
tot = sum(contrib.values()).reindex(r.index)
out = {"attribution_corr_vs_book_gross": round(float(tot.corr(r + res.costs.reindex(r.index))), 3), "quarters": {}}
for q, g in r.groupby(r.index.to_period("Q")):
    ix = g.index
    gs = {n: float(parts[n].abs().sum(axis=1).reindex(ix).mean()) for n in COMPS}; gt = sum(gs.values())
    out["quarters"][str(q)] = {"ls_names_per_day": round(float(names["listing_short"].reindex(ix).mean()), 1),
                               "gross_share": {n: round(gs[n] / gt, 2) if gt else None for n in COMPS}, "k_mean": round(float(k.reindex(ix).mean()), 2),
                               "book_gross": round(float(wb.abs().sum(axis=1).reindex(ix).mean()), 2),
                               "book_vol%": round(float(g.std() * np.sqrt(365) * 100), 1), "book_ret%": round(float(g.sum() * 100), 1),
                               "sr": round(float(g.mean() / g.std() * np.sqrt(365)), 2) if g.std() > 0 else None,
                               "contrib%": {n: round(float(contrib[n].reindex(ix).sum() * 100), 1) for n in COMPS}}
    print(q, json.dumps(out["quarters"][str(q)]), flush=True)
for lab, sl in (("2023-25", slice("2023", "2025")), ("2026", slice("2026", "2026"))):
    x = r.loc[sl]
    out[lab] = {"sr": round(float(x.mean() / x.std() * np.sqrt(365)), 2), "vol%": round(float(x.std() * np.sqrt(365) * 100), 1),
                "ls_names_per_day": round(float(names["listing_short"].loc[sl].reindex(x.index).mean()), 1),
                "contrib%_per_yr": {n: round(float(contrib[n].reindex(x.index).mean() * 365 * 100), 1) for n in COMPS}}
print(out["attribution_corr_vs_book_gross"], out["2023-25"], out["2026"])
json.dump(out, open("research/is3/ldr_ab.json", "w"), indent=1)
# per-coin concentration of the listing leg's P&L, 2026 vs 2023-25
wl = parts["listing_short"].mul(k, axis=0).shift(1).fillna(0.0)
pc = (wl * ret - wl * fund)
for lab, sl in (("2023-25", slice("2023", "2025")), ("2026", slice("2026", "2026"))):
    s = pc.loc[sl].sum().sort_values(ascending=False); s = s[s != 0]
    out[lab]["ls_coins"] = int(len(s)); out[lab]["ls_top3"] = [(i, round(float(v * 100), 1)) for i, v in s.head(3).items()]
    out[lab]["ls_top3_share"] = round(float(s.head(3).sum() / s.sum()), 2); out[lab]["ls_max_name_weight"] = round(float(wl.loc[sl].abs().max().max()), 3)
    print(lab, out[lab]["ls_coins"], out[lab]["ls_top3"], out[lab]["ls_top3_share"], out[lab]["ls_max_name_weight"])
json.dump(out, open("research/is3/ldr_ab.json", "w"), indent=1)
