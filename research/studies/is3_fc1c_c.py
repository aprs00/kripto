"""FC1C c: does the SLOPE of the HL-BN funding gap (7-d mean vs the 14-d mean fspread_hold trades) improve fspread_hold@pair's ENTRIES?
c1 gate: a pair may open only if the 7-d mean spread has the same sign as the 14-d AND |7d| >= |14d| (crowding still building). Exits unchanged.
Judge: dSR vs 200 circular-shift random gates (same on-share / run lengths per coin), 2023 and 2024 halves, per-trip dose by |7d|/|14d| tercile.
Explore 2023-05-15..2024-07-01 (backfilled HL funding; fspread's WF began 2024-07). Book = config params (lookback 14, enter 0.1), local copy with a gate hook
(asserted identical to kripto.strategies.fspread_hold without a gate).  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fc1c_c [--confirm]"""
import json, resource, sys
import numpy as np
import pandas as pd
from kripto import data, backtest as bt
from kripto.strategies import REGISTRY, bars_per_day, dollar_volume, rebalance_rows
from research.studies import is3_lib as L
from research.studies import is3_filter as F

LO, HI = "2023-05-15", "2024-07-01"
CLO, CHI = "2025-07-01", "2026-11-01"
PAR = {"lookback": 14, "enter": 0.1}
NAME = "FC1Cc_fspread_widening_gate"


def fsh(panel, gate=None, lookback=14, enter=0.20, top_n=20, max_pair=0.10, gross=2.0):
    """kripto.strategies.fspread_hold with an entry gate (DataFrame over the @hl columns, True = may open). Returns (w, O matrix, s, s7)."""
    c, f = panel["close"], panel["funding"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    bnc = [x[:-3] + "@bn" for x in hlc]
    bpd = bars_per_day(c.index)
    n = lookback * bpd
    on_bn = lambda df: df[bnc].set_axis(hlc, axis=1)
    d = f[hlc] - on_bn(f)
    s = d.rolling(n, min_periods=n).mean() * bpd * 365
    s7 = d.rolling(7 * bpd, min_periods=7 * bpd).mean() * bpd * 365
    same = np.log(c[hlc] / on_bn(c)).abs().rolling(30 * bpd, min_periods=10 * bpd).median() < 0.03
    dv = dollar_volume(panel)
    dvm = np.minimum(dv[hlc], on_bn(dv))
    elig = same & s.notna() & c[hlc].notna() & on_bn(c).notna() & (dvm > 0)
    liquid = dvm.where(elig).rank(axis=1, ascending=False) <= 2 * top_n
    can_open = elig & (dvm.where(elig).rank(axis=1, ascending=False) <= top_n)
    if gate is not None:
        can_open = can_open & gate.reindex(index=c.index, columns=hlc).fillna(True).astype(bool)
    S, E, Lo, O = s.to_numpy(), (elig & liquid).to_numpy(), can_open.to_numpy(), np.zeros(len(hlc))
    slots = int(round(gross / (2 * max_pair)))
    out = np.zeros((len(c), len(hlc)))
    for t in range(len(c)):
        st_ = S[t]
        keep = (O != 0) & E[t] & np.isfinite(st_) & (np.sign(np.nan_to_num(st_)) == O)
        O = np.where(keep, O, 0.0)
        free = slots - int((O != 0).sum())
        if free > 0:
            cand = np.flatnonzero((O == 0) & Lo[t] & np.isfinite(st_) & (np.abs(np.nan_to_num(st_)) > enter))
            cand = cand[np.argsort(-np.abs(st_[cand]))][:free]
            O[cand] = np.sign(st_[cand])
        out[t] = O
    leg = pd.DataFrame(-out * max_pair, c.index, hlc)
    w = pd.DataFrame(0.0, c.index, c.columns)
    w[hlc], w[bnc] = leg, -leg.to_numpy()
    w = rebalance_rows(w.where(elig.any(axis=1), np.nan), bpd)
    return w, pd.DataFrame(out, c.index, hlc), s, s7


def trips(O: pd.DataFrame, s, s7, panel, lo, hi, max_pair=0.10):
    """one row per opened trip in [lo, hi): entry ratio |7d|/|14d| (and same sign), price and funding P&L (fraction of equity, next-day convention)."""
    c, f = panel["close"], panel["funding"]
    hl = list(O.columns); bn = [x[:-3] + "@bn" for x in hl]
    r_h, r_b = c[hl].pct_change(fill_method=None).shift(-1), c[bn].pct_change(fill_method=None).shift(-1).set_axis(hl, axis=1)
    f_h, f_b = f[hl].shift(-1), f[bn].shift(-1).set_axis(hl, axis=1)
    rows = []
    A = O.to_numpy()
    for j, col in enumerate(hl):
        a = A[:, j]
        t = 0
        while t < len(a):
            if a[t] != 0 and (t == 0 or a[t - 1] != a[t]):
                u = t
                while u + 1 < len(a) and a[u + 1] == a[t]:
                    u += 1
                ts = O.index[t]
                if pd.Timestamp(lo, tz=ts.tz) <= ts < pd.Timestamp(hi, tz=ts.tz):
                    sg = a[t]
                    seg = slice(t, u + 1)
                    pr = float(np.nansum(sg * max_pair * (-r_h[col].iloc[seg] + r_b[col].iloc[seg])))
                    fu = float(np.nansum(sg * max_pair * (f_h[col].iloc[seg] - f_b[col].iloc[seg])))
                    s14, x7 = s[col].iloc[t], s7[col].iloc[t]
                    rows.append({"coin": col, "t": ts, "days": u - t + 1, "sign": sg, "ratio": abs(x7) / abs(s14) * np.sign(x7 * s14),
                                 "price": pr, "fund": fu, "tot": pr + fu})
                t = u + 1
            else:
                t += 1
    return pd.DataFrame(rows)


def main(confirm=False):
    panel = data.load_panel("pair", "1d")
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    w0 = REGISTRY["fspread_hold"](panel, **PAR)
    wb, O, s, s7 = fsh(panel, None, **PAR)
    assert np.allclose(w0.fillna(0).to_numpy(), wb.fillna(0).to_numpy()), "local copy differs from the registered strategy"
    gate = (np.sign(s7) == np.sign(s)) & (s7.abs() >= s.abs())
    gate = gate | s7.isna()
    lo, hi = (CLO, CHI) if confirm else (LO, HI)
    sample = "confirmT" if confirm else "explore"
    L.SAMPLES[sample] = (lo, hi)
    if confirm:
        if NAME not in L.committed_prereg():
            raise SystemExit("pre-register and commit first")
        if (L.OUT / f"{NAME}__confirmT.json").exists():
            raise SystemExit("confirm already used")
    wg, Og, _, _ = fsh(panel, gate, **PAR)
    base, filt = F.cut(F.run(wb, panel, slip), sample), F.cut(F.run(wg, panel, slip), sample)
    sb, sf = F.stats(base), F.stats(filt)
    cand_share = float(gate.loc[lo:hi].to_numpy().mean())
    rnd = []
    for k, g in enumerate(F.random_masks(gate, 200, seed=0)):
        wr, _, _, _ = fsh(panel, g, **PAR)
        rnd.append(F.stats(F.cut(F.run(wr, panel, slip), sample))["sr"] - sb["sr"])
    dsr = sf["sr"] - sb["sr"]
    pct = float((np.array(rnd) < dsr).mean() * 100)
    yrs = {}
    for y in sorted(set(base.index.year)):
        yrs[int(y)] = {"base": round(F.stats(base[base.index.year == y])["sr"], 2), "gate": round(F.stats(filt[filt.index.year == y])["sr"], 2)}
    tr = trips(O, s, s7, panel, lo, hi)
    dose = None
    if len(tr) >= 9:
        tr["q"] = pd.qcut(tr["ratio"].rank(method="first"), 3, labels=["low", "mid", "high"])
        dose = tr.groupby("q", observed=True)[["price", "fund", "tot", "days"]].agg(["mean"]).round(5)
        dose["n"] = tr.groupby("q", observed=True).size()
        dose.columns = ["price", "fund", "tot", "days", "n"]
    pairs_open = float((O.loc[lo:hi] != 0).sum(axis=1).mean())
    out = {"name": NAME, "sample": sample, "lo": lo, "hi": hi, "base": sb, "gate": sf, "dsr": dsr, "pct_vs_random": pct,
           "rnd_dsr_p50": float(np.median(rnd)), "rnd_dsr_p95": float(np.quantile(rnd, .95)), "gate_on_share": cand_share,
           "years": yrs, "trips": len(tr), "mean_pairs_open": pairs_open,
           "base_ann_net": sb["ann"], "dose": None if dose is None else dose.reset_index().to_dict("records"),
           "max_rss_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6}
    print(json.dumps({k: v for k, v in out.items() if k != "dose"}, default=float, indent=1))
    if dose is not None:
        print(dose.to_string())
    fn = f"{NAME}__confirmT.json" if confirm else "fc1c_c_explore.json"
    json.dump(out, open(L.OUT / fn, "w"), indent=1, default=str)


if __name__ == "__main__":
    main("--confirm" in sys.argv)
