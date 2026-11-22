"""Test battery of the InSilico third pass (research/insilico_pass3.md section 2). Every form is judged by the same card.

An "event" = one hypothetical trade: time (decision, UTC), coin, side (+1/-1), gross (SIMPLE return in the direction of the
side, before costs), optional `cost` (fraction, round trip). Usage in a study:

  from research.studies import is3_lib as L
  L.null_check(fn, panel)            # 1. the event function on sign-flipped surrogate data must earn ~0 (else: look-ahead/bias)
  L.check_causal(fn, panel, cut)     # 2. events before `cut` do not change when the future is removed
  L.card("L1a", events, "explore", base=L.matched(events, pool))   # 3. explore freely
  L.prereg("L1a", claim, rule)       # 4. freeze, COMMIT, only then:
  L.card("L1a", events, "confirmT")  # 5. once per name and sample; confirmC = unseen coins
  L.card("L1a", events, "vault")     # 6. 2026, only after a passed confirm card
  python -m research.studies.is3_lib fdr    # Benjamini-Hochberg over every confirm card of the programme

Cards: research/is3/<name>__<sample>.json, index: research/is3/index.jsonl (append-only). Nothing here is a backtest that
feeds a gate: survivors still go through kripto.research (registry) before any book.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "research" / "is3"
COINS10 = "BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC".split()
SAMPLES = {"explore": ("2021-01-01", "2024-01-01"), "confirmT": ("2024-01-01", "2026-01-01"),
           "confirmC": ("2021-01-01", "2026-01-01"), "vault": ("2026-01-01", "2026-11-01")}
LADDER = {"free": 0.0, "maker_taker": 8.0, "taker": 13.0, "taker_x2": 26.0, "crash": 80.0}    # round trip, bp


def half(coin: str) -> int:
    """Fixed coin split for wide universes (bnall / bn100 / HL): 0 = explore and confirmT, 1 = confirmC."""
    return zlib.crc32(coin.encode()) % 2


# ---------------------------------------------------------------- pre-registration
def read_prereg() -> dict:
    p = OUT / "prereg.json"
    return json.loads(p.read_text()) if p.exists() else {}


def committed_prereg() -> dict:
    r = subprocess.run(["git", "show", "HEAD:research/is3/prereg.json"], capture_output=True, text=True, cwd=ROOT)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def prereg(name: str, claim: str, rule: str, **params) -> None:
    d = read_prereg()
    if name in d:
        raise SystemExit(f"{name} is already pre-registered; a changed rule needs a new name")
    d[name] = {"claim": claim, "rule": rule, "params": params, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prereg.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- statistics
def _daily(e: pd.DataFrame) -> pd.DataFrame:
    g = e.groupby(pd.to_datetime(e["time"], utc=True).dt.floor("D"))["gross"]
    return pd.DataFrame({"s": g.sum(), "n": g.size()})


def _boot(e: pd.DataFrame, base: pd.DataFrame | None, reps: int, seed: int = 7) -> tuple[np.ndarray, np.ndarray | None]:
    """Day-block bootstrap of the mean per event (and of mean - baseline mean): whole UTC days are resampled together."""
    d = _daily(e)
    b = _daily(base) if base is not None and len(base) else None
    days = d.index.union(b.index) if b is not None else d.index
    A = d.reindex(days).fillna(0.0).to_numpy()
    B = b.reindex(days).fillna(0.0).to_numpy() if b is not None else None
    rng, m, diff = np.random.default_rng(seed), np.empty(reps), (np.empty(reps) if B is not None else None)
    for i in range(reps):
        w = np.bincount(rng.integers(0, len(days), len(days)), minlength=len(days))
        s, n = w @ A
        m[i] = s / max(n, 1)
        if B is not None:
            sb, nb = w @ B
            diff[i] = m[i] - sb / max(nb, 1)
    return m, diff


def _p(boot: np.ndarray, est: float) -> float:
    """Two-sided p of est != 0 from a bootstrap distribution (shifted to the null)."""
    return float((1 + np.sum(np.abs(boot - np.nanmean(boot)) >= abs(est))) / (len(boot) + 1))


def stats(e: pd.DataFrame, base: pd.DataFrame | None = None, reps: int = 2000) -> dict:
    g = e["gross"].to_numpy(dtype=float)
    d = _daily(e)
    m, diff = _boot(e, base, reps)
    top3 = d["s"].nlargest(3).index
    rest = e[~pd.to_datetime(e["time"], utc=True).dt.floor("D").isin(top3)]["gross"]
    tot = d["s"].sum()
    bp = lambda x: round(float(x) * 1e4, 2)
    out = {"n": int(len(e)), "days": int(len(d)), "coins": int(e["coin"].nunique()), "mean_bp": bp(g.mean()), "median_bp": bp(np.median(g)),
           "win": round(float((g > 0).mean()), 3), "se_bp": bp(m.std()), "ci95_bp": [bp(np.quantile(m, 0.025)), bp(np.quantile(m, 0.975))],
           "p": _p(m, g.mean()), "mde80_bp": bp(2.8 * m.std()), "mean_ex_top3_bp": bp(rest.mean()) if len(rest) else None,
           "top3_share": round(float(d["s"].nlargest(3).sum() / tot), 2) if tot > 0 else None,
           "t_day_mean": round(float((d.s / d.n).mean() / ((d.s / d.n).std() / np.sqrt(len(d)) + 1e-18)), 2)}
    t = pd.to_datetime(e["time"], utc=True)
    out["by_year"] = {int(y): [int(len(x)), bp(x.mean())] for y, x in e["gross"].groupby(t.dt.year)}
    out["by_side"] = {int(s): [int(len(x)), bp(x.mean())] for s, x in e["gross"].groupby(e["side"])}
    out["coins_positive"] = round(float((e.groupby("coin")["gross"].mean() > 0).mean()), 2)
    out["net_bp"] = {k: round(out["mean_bp"] - v, 2) for k, v in LADDER.items()}
    if "cost" in e:
        out["net_bp"]["own_cost"] = bp((e["gross"] - e["cost"]).mean())
    if base is not None and len(base):
        est = g.mean() - base["gross"].mean()
        out |= {"base_n": int(len(base)), "base_bp": bp(base["gross"].mean()), "vs_base_bp": bp(est), "p_vs_base": _p(diff, est)}
    return out


def card(name: str, e: pd.DataFrame, sample: str, base: pd.DataFrame | None = None, note: str = "", rerun: str = "", reps: int = 2000) -> dict:
    """Judge one form on one sample, print and store the card. `passes` = positive after costs, p < 0.05 (against the matched
    baseline when there is one), and still positive without its three best days. It is a screen, not a promotion."""
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in SAMPLES[sample])
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{name}__{sample}.json"
    if sample != "explore":
        if name not in committed_prereg():
            raise SystemExit(f"{name}: pre-register (L.prereg) and COMMIT before touching {sample}")
        if f.exists() and not rerun:
            raise SystemExit(f"{name}: {sample} was already used; rerun=\"<bug that was fixed>\" is the only exception and is recorded")
    if sample == "vault":
        ok = [json.loads(p.read_text()).get("passes") for p in OUT.glob(f"{name}__confirm*.json")]
        if not ok or not all(ok):
            raise SystemExit(f"{name}: the vault opens only after every confirm card passed ({ok})")
    if len(e) == 0:
        c = {"n": 0, "passes": False}
    else:
        t = pd.to_datetime(e["time"], utc=True)
        if (t < lo).any() or (t >= hi).any():
            raise SystemExit(f"{name}: events outside the {sample} dates {lo.date()}..{hi.date()}")
    if len(e):
        c = stats(e, base, reps)
        net = c["net_bp"].get("own_cost", c["net_bp"]["taker"])
        p = c.get("p_vs_base", c["p"])
        c["passes"] = bool(net > 0 and p < 0.05 and c["p"] < 0.05 and c.get("vs_base_bp", 1.0) > 0
                           and (c["mean_ex_top3_bp"] or -1) - (c["mean_bp"] - net) > 0)
    c = {"name": name, "sample": sample, **c, "note": note, "rerun": rerun, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    f.write_text(json.dumps(c, indent=1, default=float) + "\n")
    with (OUT / "index.jsonl").open("a") as fh:
        fh.write(json.dumps({k: c.get(k) for k in ("at", "name", "sample", "n", "days", "mean_bp", "se_bp", "p", "vs_base_bp", "p_vs_base", "passes", "rerun")}) + "\n")
    if len(e):
        print(f"[{name} {sample}] n={c['n']} days={c['days']} coins={c['coins']} mean {c['mean_bp']:+.1f} bp (se {c['se_bp']:.1f}, p {c['p']:.3f}, "
              f"mde {c['mde80_bp']:.1f}) median {c['median_bp']:+.1f} win {c['win']:.0%} | ex-top3 {c['mean_ex_top3_bp']} | net {c['net_bp']}"
              + (f" | base {c['base_bp']:+.1f}, diff {c['vs_base_bp']:+.1f} (p {c['p_vs_base']:.3f})" if "base_bp" in c else "")
              + f" | years {c['by_year']} | sides {c['by_side']} | passes={c['passes']} {note}")
    else:
        print(f"[{name} {sample}] no events")
    return c


# ---------------------------------------------------------------- null data, causality, baselines
def surrogate(p: dict, seed: int) -> dict:
    """Sign-flipped copy of an OHLCV panel: every bar keeps its size, range and volume, but its direction is a coin toss (the
    same toss for all coins, so cross-coin correlation stays). No rule can earn anything here except by look-ahead or bias."""
    rng = np.random.default_rng(seed)
    c = p["close"].to_numpy(dtype=float)
    o = np.vstack([c[:1], c[:-1]])
    s = rng.choice([-1.0, 1.0], size=(len(c), 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        r, up, dn = np.log(c / o), np.log(np.maximum(p["high"].to_numpy(dtype=float), np.maximum(o, c)) / o), \
            np.log(np.minimum(p["low"].to_numpy(dtype=float), np.minimum(o, c)) / o)
    r2, up2, dn2 = s * r, np.where(s > 0, up, -dn), np.where(s > 0, dn, -up)
    nan = np.isnan(c)
    first = np.array([x[np.isfinite(x)][0] if np.isfinite(x).any() else np.nan for x in c.T])
    c2 = first * np.exp(np.cumsum(np.nan_to_num(r2), axis=0))
    o2 = np.vstack([first[None, :], c2[:-1]])
    fr = lambda x: pd.DataFrame(np.where(nan, np.nan, x), p["close"].index, p["close"].columns)
    out = {"close": fr(c2), "high": fr(o2 * np.exp(np.nan_to_num(up2))), "low": fr(o2 * np.exp(np.nan_to_num(dn2)))}
    for k, x in p.items():
        if k in out:
            continue
        out[k] = fr(np.where(s > 0, x.to_numpy(dtype=float), p["volume"].to_numpy(dtype=float) - x.to_numpy(dtype=float))) if k == "tb" else x
    return out


def null_check(fn, panel: dict, n: int = 20) -> dict:
    """Run the event function on n surrogates. bad=True when the mean over surrogates is more than 3 standard errors from 0."""
    m = [float(x["gross"].mean()) for x in (fn(surrogate(panel, s)) for s in range(n)) if len(x)]
    a = np.array(m) * 1e4
    se = a.std(ddof=1) / np.sqrt(len(a)) if len(a) > 2 else np.nan
    out = {"surrogates": len(a), "mean_bp": round(float(a.mean()), 2) if len(a) else None, "se_bp": round(float(se), 2),
           "q95_bp": round(float(np.quantile(a, 0.95)), 2) if len(a) else None, "bad": bool(len(a) > 2 and abs(a.mean()) > 3 * se and abs(a.mean()) > 0.3)}
    print("null check (sign-flipped data):", out)
    return out


def check_causal(fn, panel: dict, cut: str, horizon: str = "2D") -> bool:
    """Events decided more than `horizon` before the cut must be identical with and without the data after it."""
    c = pd.Timestamp(cut, tz="UTC")
    key = ["time", "coin", "side", "gross"]
    pick = lambda e: e[pd.to_datetime(e["time"], utc=True) < c - pd.Timedelta(horizon)][key].sort_values(key[:3]).reset_index(drop=True)
    a, b = pick(fn(panel)), pick(fn({k: x[x.index < c] for k, x in panel.items()}))
    ok = len(a) == len(b) > 0 and np.allclose(a.gross, b.gross, atol=1e-9) and bool((a[key[:3]].astype(str) == b[key[:3]].astype(str)).all().all())
    print("causality check:", "ok" if ok else f"FAIL ({len(a)} vs {len(b)} events)")
    return bool(ok)


def matched(e: pd.DataFrame, pool: pd.DataFrame, k: int = 5, seed: int = 3) -> pd.DataFrame:
    """k non-event rows per event from `pool` with the same coin and the same matching bin `m` (e.g. decile of the past move)."""
    rng = np.random.default_rng(seed)
    ek = set(zip(e["time"].astype("int64"), e["coin"]))
    q = pool[[(t, c) not in ek for t, c in zip(pool["time"].astype("int64"), pool["coin"])]]
    g = {key: x.index.to_numpy() for key, x in q.groupby(["coin", "m"])}
    take = [rng.choice(g[(c, m)], k) for c, m in zip(e["coin"], e["m"]) if (c, m) in g]
    return q.loc[np.concatenate(take)].reset_index(drop=True) if take else q.iloc[:0]


def bh(ps: dict, q: float = 0.10) -> set:
    s = sorted(ps.items(), key=lambda x: x[1])
    k = max([i + 1 for i, (_, p) in enumerate(s) if p <= q * (i + 1) / len(s)], default=0)
    return {n for n, _ in s[:k]}


if __name__ == "__main__" and sys.argv[1:] == ["fdr"]:
    rows = [json.loads(x) for x in (OUT / "index.jsonl").read_text().splitlines()]
    last = {(r["name"], r["sample"]): r for r in rows if r["sample"].startswith("confirm") and r["p"] is not None}
    ps = {f"{n}__{s}": (r["p_vs_base"] if r["p_vs_base"] is not None else r["p"]) for (n, s), r in last.items()}
    keep = bh(ps)
    for k, p in sorted(ps.items(), key=lambda x: x[1]):
        print(f"{'KEEP' if k in keep else '    '} p={p:.4f} {k}")
    print(f"{len(keep)}/{len(ps)} confirm cards survive a 10% false-discovery rate; explore cards run: {sum(r['sample'] == 'explore' for r in rows)}")
