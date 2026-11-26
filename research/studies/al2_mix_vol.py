"""AL2 (2026-11-26 research; follow-up of AL1): should a main book scale its MIX to the steady-mode vol target?
AL1 found main_bn's 1/N mix of separately vol-targeted books realises 14-18 % a year against the 25-30 % steady target (diversification
between books). Proposed general rule (design.md 2026-11-26): every main book's allocation-weighted target row is ex-ante vol-targeted to
0.25 (60-day covariance, the same `strategies.vol_target` every single book uses), capped at risk.json max_gross 3.0.
Descriptive, no new signal, no registry line. Books run through kripto.backtest directly (costs, funding, band) like AL1.
Pre-registered decision (written before running, journal 2026-11-26): adopt for paper main books if, on bnall 1d for main_bn's set
(new M1 mix flow + blend_nested, and the old mix flow + xsmom + blend as a second check): realised vol of the scaled mix in 20-32 %,
SR(scaled) >= SR(unscaled) - 0.10 (scaling turnover and the vol estimate's noise must not cost more than that), and
mdd(scaled) no worse than mdd(unscaled) * vol(scaled)/vol(unscaled) * 1.25. HL main (blend_nested alone) on hl 1d is reported too.
Form b (AL2b, pre-registered 2026-11-26 after form a failed on dSR, before running b): the daily ex-ante rescaling doubled costs. b scales the
mix by ONE number per calendar month, s = clip(0.25 / realised vol of the unscaled mix's net daily returns over the trailing 365 days
(ending the day before the month starts; >= 120 days of history, else 1), 0.5, 2.0), gross capped at 3. Same decision rule as a.
  usage: nice -n 19 .venv/bin/python -m research.studies.al2_mix_vol [b]
"""
import sys
import numpy as np
import pandas as pd

from kripto import backtest as bt, data
from kripto.research import bars_per_day, default_band
from kripto.strategies import REGISTRY, vol_target, _ffill_targets

CFG = {"flow": ("flow", {"lookback": 3, "cap": 0.05}), "xsmom": ("xsmom", {"lookback": 28, "every_days": 1, "cap": 0.05}),
       "blend": ("blend", {}), "blend_nested": ("blend_nested", {"top": 3})}
SETS = {"bnall": {"NEW": ["flow", "blend_nested"], "OLD": ["flow", "xsmom", "blend"]}, "hl": {"HLMAIN": ["blend_nested"]}}


def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    return r.mean() / r.std() * np.sqrt(365), r.std() * np.sqrt(365), (eq / eq.cummax() - 1).min()


FORM = sys.argv[1] if len(sys.argv) > 1 else "a"


def main():
    for ds, sets in SETS.items():
        p = data.load_panel(ds, "1d")
        slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
        held = {}
        for k in {c for cols in sets.values() for c in cols}:
            fn, prm = CFG[k]
            held[k] = _ffill_targets(REGISTRY[fn](p, **prm)).reindex(columns=p["close"].columns).fillna(0.0)
        for name, cols in sets.items():
            mix = sum(held[c] for c in cols) / len(cols)
            live = mix.abs().sum(axis=1) > 0
            start = live[live].index[0] if live.any() else mix.index[0]
            if FORM == "b":
                r_un = bt.run(mix, p["close"], p.get("funding"), slip, band=default_band()).returns
                rv = r_un.where(r_un.index >= start).rolling(365, min_periods=120).std().shift(1) * np.sqrt(365)
                months = mix.index.to_period("M")
                first_day = pd.Series(mix.index, index=mix.index).groupby(months).transform("min")
                s_m = (0.25 / rv).clip(0.5, 2.0).reindex(first_day.to_numpy()).fillna(1.0).to_numpy()
                scaled = mix.mul(s_m, axis=0)
                g = scaled.abs().sum(axis=1)
                scaled = scaled.mul((3.0 / g).clip(upper=1.0).fillna(1.0), axis=0)
                print(f"{ds} {name} form b: monthly scale mean {np.mean(s_m):.2f} min {np.min(s_m):.2f} max {np.max(s_m):.2f}")
            else:
                scaled = vol_target(mix, p, 0.25, max_gross=3.0)
            out = {}
            for lab, w in (("unscaled", mix), ("scaled", scaled)):
                res = bt.run(w, p["close"], p.get("funding"), slip, band=default_band())
                r = res.returns[res.returns.index >= start]
                sr, vol, mdd = stats(r)
                g = w.loc[w.index >= start].abs().sum(axis=1)
                yrs = " ".join(f"{y}:{stats(x)[0]:+.1f}/{stats(x)[1]:.0%}" for y, x in r.groupby(r.index.year))
                cost = getattr(res, "costs", None)
                cst = f" cost/yr {cost[cost.index >= start].sum() / (len(r) / 365):.1%}" if isinstance(cost, pd.Series) else ""
                out[lab] = (sr, vol, mdd)
                print(f"{ds} {name:6s} {lab:8s} SR {sr:.2f} vol {vol:.0%} mdd {mdd:.0%} gross mean {g.mean():.2f} max {g.max():.2f}{cst} | {yrs}")
            (s0, v0, d0), (s1, v1, d1) = out["unscaled"], out["scaled"]
            ok = (0.20 <= v1 <= 0.32) and (s1 >= s0 - 0.10) and (d1 >= d0 * v1 / v0 * 1.25)
            print(f"{ds} {name}: rule {'PASS' if ok else 'FAIL'} (vol {v1:.0%} in 20-32%: {0.20 <= v1 <= 0.32}; dSR {s1 - s0:+.2f} >= -0.10: "
                  f"{s1 >= s0 - 0.10}; mdd {d1:.0%} vs bound {d0 * v1 / v0 * 1.25:.0%}: {d1 >= d0 * v1 / v0 * 1.25})")


if __name__ == "__main__":
    main()
