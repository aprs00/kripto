"""T3a + T3d: context model on every climax (instead of one if-x-then-y rule), with a shuffle test.

Events = is3_t3b.events() (COINS10 explore climaxes, decision at the close of climax+3) joined with the lshock trigger
columns. Features (all known at the decision): side, z, log vm, fall / sig, log sig, spring, spring1, spring x side,
hour-of-day (sin, cos), log dv30, breadth, and side interactions of each. Target = 60-min fade return (h60).
Model = ridge (numpy closed form, features standardised on the training window), walk-forward by calendar quarter:
train on every event before quarter start minus 1 day (purge), predict the quarter; first 4 quarters burn-in.
Score: OOS rank IC per quarter; P&L of trading the sign of the prediction on the top 10 % |prediction| (fade if > 0,
continuation if < 0) vs the fixed rule (fade everything). T3d: the same pipeline with the target permuted inside every
training window must earn ~0 (20 permutations). No gradient-boosted trees: not installed; ridge is the honest floor.

    nice -n 19 .venv/bin/python -m research.studies.is3_t3a     -> research/is3/T3a__model.json + card
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_t3b import events

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "is3" / "T3a__model.json"
LAM = 10.0


def frame() -> pd.DataFrame:
    e = events()
    t = pd.read_parquet(ROOT / "data/is3/lshock.parquet", columns=["time", "kind", "side", "coin", "vm", "sig", "dv30", "breadth"])
    t = t[(t.kind == "any") & t.coin.isin(L.COINS10)].drop(columns="kind")
    t["time"] = t.time + pd.Timedelta(minutes=2)            # lshock time = climax+1 close; events time = climax+3 close
    e = e.merge(t, on=["time", "coin", "side"], how="left")
    hr = e.time.dt.hour + e.time.dt.minute / 60
    X = pd.DataFrame({"side": e.side, "z": e.z, "lvm": np.log(e.vm), "fall_sig": e.fall / e.sig, "lsig": np.log(e.sig),
                      "spring": e.spring.clip(-1, 3), "spring1": e.spring1.clip(-1, 3), "hs": np.sin(2 * np.pi * hr / 24),
                      "hc": np.cos(2 * np.pi * hr / 24), "ldv": np.log(e.dv30), "breadth": e.breadth})
    for c in list(X.columns[1:]):
        X[f"{c}_x_side"] = X[c] * X.side
    e = pd.concat([e, X.add_prefix("f_")], axis=1)
    return e.replace([np.inf, -np.inf], np.nan).dropna(subset=[c for c in e.columns if c.startswith("f_")] + ["h60"]).sort_values("time").reset_index(drop=True)


def ridge(Xtr, ytr, Xte):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    w = np.linalg.solve(A.T @ A + LAM * len(A) / 1000 * np.eye(A.shape[1]), A.T @ (ytr - ytr.mean()))
    return B @ w + ytr.mean()


def walk(e: pd.DataFrame, perm_seed: int | None = None) -> pd.Series:
    F = [c for c in e.columns if c.startswith("f_")]
    X, y = e[F].to_numpy(float), e.h60.to_numpy(float)
    q = e.time.dt.to_period("Q")
    pred = pd.Series(np.nan, index=e.index)
    rng = np.random.default_rng(perm_seed) if perm_seed is not None else None
    for qq in sorted(q.unique())[4:]:
        start = qq.start_time.tz_localize("UTC")
        tr = (e.time < start - pd.Timedelta(days=1)).to_numpy()
        te = (q == qq).to_numpy()
        ytr = y[tr] if rng is None else rng.permutation(y[tr])
        pred[te] = ridge(X[tr], ytr, X[te])
    return pred


def score(e: pd.DataFrame, pred: pd.Series) -> dict:
    m = pred.notna()
    x = e[m].assign(p=pred[m])
    ic = x.groupby(x.time.dt.to_period("Q")).apply(lambda g: g.p.rank().corr(g.h60.rank()))
    top = x[x.p.abs() >= x.p.abs().quantile(0.9)]
    sgn = np.sign(top.p)
    return {"n_oos": int(len(x)), "ic_mean": float(ic.mean()), "ic_t": float(ic.mean() / (ic.std() / np.sqrt(len(ic)))), "ic_by_q": {str(k): round(float(v), 3) for k, v in ic.items()},
            "top10_mean_bp": float((sgn * top.h60).mean() * 1e4), "all_fade_mean_bp": float(x.h60.mean() * 1e4), "top": top.assign(side=(top.side * sgn).astype(int), gross=sgn * top.h60)}


def main() -> None:
    e = frame()
    print(f"events with all features: {len(e)}")
    s = score(e, walk(e))
    print(f"OOS rank IC {s['ic_mean']:+.4f} (t {s['ic_t']:+.2f}) by quarter {s['ic_by_q']}")
    print(f"top-10% |pred| traded by sign: {s['top10_mean_bp']:+.1f} bp/event vs fade-everything {s['all_fade_mean_bp']:+.1f} bp")
    perms = []
    for k in range(20):
        sp = score(e, walk(e, perm_seed=100 + k))
        perms.append((sp["ic_mean"], sp["top10_mean_bp"]))
    pa = np.array(perms)
    print(f"shuffle (20): IC {pa[:, 0].mean():+.4f} sd {pa[:, 0].std():.4f}; top-10% {pa[:, 1].mean():+.1f} bp sd {pa[:, 1].std():.1f}")
    pool = e.assign(gross=e.h60)
    pool["m"] = pool.groupby("coin").fall.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    top = s.pop("top").merge(pool[["time", "coin", "m"]], on=["time", "coin"], how="left")
    base = L.matched(top, pool, k=3)
    cols = ["time", "coin", "side", "gross"]
    card = L.card("T3a_ridge_top10_h60", top[cols], "explore", base[cols], note="ridge walk-forward by quarter, top 10% |pred|, traded by sign; base = fade matched climaxes")
    res = {**s, "shuffle_ic_mean": float(pa[:, 0].mean()), "shuffle_ic_sd": float(pa[:, 0].std()), "shuffle_top_mean_bp": float(pa[:, 1].mean()),
           "shuffle_top_sd_bp": float(pa[:, 1].std()), "card": {k: card.get(k) for k in ("n", "mean_bp", "p", "vs_base_bp", "p_vs_base", "mde80_bp", "passes")}}
    OUT.write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
