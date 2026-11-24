"""T5g/h: 1-hour moves split by open interest (wa 18.10.51 'selling was closing of positions'; tg:199-203 NL/NS panels).

Clock-hour bars from Binance 1-min klines; OI = Binance 5-min metrics snapshots (data/bn/metrics), forward-filled to minutes.
Event: |1-h log return| >= 2 x 30-day hourly sigma (shift 1). Side = FADE (long after a fall). Decision 5 minutes after the
hour closes (OI snapshot lag), simple returns 1 / 4 / 24 h from there. Features: doi = OI(end)/OI(start) - 1 in its own
30-day sigma; dlt = taker delta share of the hour signed TOWARD the move (> 0 = takers pushed it, < 0 = takers leaned against it).
g: fade by doi decile. h: four cells sign(doi) x sign(dlt); 'trapped' = OI up and takers against the move (they bought the fall).
Baseline = same coin, same move-size bin, events outside the cell (is3_lib.matched).

    nice -n 19 .venv/bin/python -m research.studies.is3_t5g build | curves | checks
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "data/is3/t5g.parquet"
OUT = ROOT / "research/is3/T5g__curves.json"


def panel(coins, lo: str, hi: str, mdir: str = "data/bn/metrics") -> dict:
    cols, ois = {}, {}
    for c in coins:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{c}USDT.parquet")
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= pd.Timestamp(lo, tz="UTC") - pd.Timedelta("32D")) & (k.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta("2D"))].asfreq("1min")
        cols[c] = k
        m = pd.read_parquet(ROOT / mdir / f"{c}USDT.parquet", columns=["t", "oi"]).set_index("t").oi
        ois[c] = m.reindex(k.index).ffill(limit=15)
    f = lambda col: pd.DataFrame({c: k[col] for c, k in cols.items()}).astype("float64")
    return {"close": f("c"), "high": f("h"), "low": f("l"), "volume": f("qv"), "tb": f("tbqv"), "oi": pd.DataFrame(ois).astype("float64")}


def events(p: dict, lo: str | None = None, hi: str | None = None) -> pd.DataFrame:
    out = []
    idx = p["close"].index
    for coin in p["close"].columns:
        c1 = p["close"][coin].ffill()
        hc = c1.resample("1h").last()                         # close of the hour [H, H+60) = close of minute H+59
        hv = p["volume"][coin].resample("1h").sum(min_count=1)
        htb = p["tb"][coin].resample("1h").sum(min_count=1)
        oi = p["oi"][coin]
        r = np.log(hc / hc.shift(1))
        sig = r.rolling(720, min_periods=360).std().shift(1)
        oi_s = oi.reindex(hc.index)                            # snapshot at H (start)
        oi_e = oi.reindex(hc.index + pd.Timedelta("60min"))    # snapshot at H+60 (end)
        doi = pd.Series(oi_e.to_numpy() / oi_s.to_numpy() - 1, index=hc.index)
        doi_z = doi / doi.rolling(720, min_periods=360).std().shift(1)
        z = r / sig
        c = c1.to_numpy()
        pos = pd.Series(np.arange(len(idx)), index=idx)
        for H in z.index[(z.abs() >= 2).to_numpy() & np.isfinite(doi_z.to_numpy())]:
            q = H + pd.Timedelta("64min")                     # entry at the close of minute H+64 = 5 min after the hour
            if q not in pos.index:
                continue
            i = int(pos[q])
            if i + 1440 >= len(c):
                continue
            s = -int(np.sign(r[H]))
            dlt = (2 * htb[H] - hv[H]) / hv[H] * np.sign(r[H]) if hv[H] > 0 else np.nan
            row = {"time": q, "coin": coin, "side": s, "z": abs(z[H]), "doi_z": doi_z[H], "doi": doi[H], "dlt": dlt}
            for h_ in (60, 240, 1440):
                row[f"f{h_}"] = s * (c[i + h_] / c[i] - 1)
            row["gross"] = row["f240"]
            out.append(row)
    e = pd.DataFrame(out)
    if len(e) and lo:
        e = e[(e.time >= pd.Timestamp(lo, tz="UTC")) & (e.time < pd.Timestamp(hi, tz="UTC"))]
    return e.reset_index(drop=True) if len(e) else pd.DataFrame(columns=["time", "coin", "side", "gross"])


def build(coins=None, out: Path = TAB) -> pd.DataFrame:
    parts = []
    for c in coins or L.COINS10:
        lo = "2021-02-01" if c == "BTC" else "2022-01-01"     # 30-d sigma warm-up after the metrics start
        parts.append(events(panel([c], lo, "2024-01-01"), lo, "2024-01-01"))
    e = pd.concat(parts, ignore_index=True)
    e["m"] = pd.cut(e.z, [2, 2.5, 3, 4, 1e9], labels=False, right=False)
    e["cell"] = np.where(e.doi_z > 0, "oi_up", "oi_dn") + np.where(e.dlt > 0, "_with", "_against")
    e.to_parquet(out)
    print(len(e), e.groupby("side").size().to_dict(), e.cell.value_counts().to_dict())
    return e


def _s(g, col, base=None, reps=400):
    x = g.assign(gross=g[col])[["time", "coin", "side", "gross"]]
    b = base.assign(gross=base[col])[["time", "coin", "side", "gross"]] if base is not None else None
    return L.stats(x, b, reps=reps)


def curves() -> None:
    e = pd.read_parquet(TAB)
    res = {"n": int(len(e))}
    for sname, x in (("all", e), ("falls", e[e.side == 1]), ("rises", e[e.side == -1])):
        res[sname] = {}
        for f in ("doi_z", "z", "dlt"):
            xb = x.assign(b=pd.qcut(x[f].rank(method="first"), 5, labels=False))
            for col in ("f240", "f1440"):
                means = []
                for b, g in xb.groupby("b"):
                    means.append(_s(g, col)["mean_bp"])
                rho = float(pd.Series(means).corr(pd.Series(range(5)), method="spearman"))
                res[sname][f"{f}_{col}"] = {"quintiles_bp": means, "spearman": rho}
                print(f"{sname:6s} {f:6s} {col:6s} n={len(x)} rho {rho:+.2f} | " + " ".join(f"{m:+.0f}" for m in means))
        for cell in sorted(x.cell.unique()):
            ev, pool = x[x.cell == cell], x[x.cell != cell]
            base = L.matched(ev, pool, k=3)
            for col in ("f240", "f1440"):
                s = _s(ev, col, base, reps=800)
                res[sname][f"{cell}_{col}"] = {k: s.get(k) for k in ("n", "mean_bp", "ci95_bp", "mde80_bp", "base_bp", "vs_base_bp", "p_vs_base")}
                print(f"  {sname} {cell:12s} {col}: n={s['n']} fade {s['mean_bp']:+.1f} vs base {s.get('base_bp')} (p {s.get('p_vs_base')}, mde {s['mde80_bp']})")
    OUT.write_text(json.dumps(res, indent=1, default=float))


def checks() -> None:
    p = panel(["BTC", "SOL"], "2022-01-01", "2022-09-01")
    res = {"null": L.null_check(lambda q: events(q), p, n=20), "causal": L.check_causal(lambda q: events(q), p, "2022-06-01")}
    (ROOT / "research/is3/T5g__checks.json").write_text(json.dumps(res, default=float))


if __name__ == "__main__":
    {"build": build, "curves": curves, "checks": checks}[sys.argv[1]]()
