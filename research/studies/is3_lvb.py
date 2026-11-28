"""InSilico pass 3, LVB b: main-book live vs replay (scripts.live_vs_backtest --main) + why small:main_bn does not track:
replay the $200 Binance book with each symbol's own MIN_NOTIONAL (BTC $50, ETH $20, ...) instead of one $5 band. Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lvb  -> research/is3/lvb_b.json"""
import json
import numpy as np
import pandas as pd
from kripto import paper as P, venue_bn as V
from scripts import live_vs_backtest as L

cfg, risk = P.load_cfg(); c = L._db()
coins = L.live_universe(c, "bn"); pn = L._panel("bn", coins)
live_e = {n: s for n, s in cfg.items() if P.venue_of(s) == "bn" and s.get("status") in ("incubation", "active") and s.get("alloc", 0) > 0}
out = {}
for book, eq0 in (("main_bn", 1000.0), ("small:main_bn", 200.0)):
    sb = pd.Timestamp(pd.read_sql("select bar from rebalances where book=? order by bar limit 1", c, params=(book,)).iloc[0, 0])
    m = L.main_targets([(s["alloc"], L.entry_targets(n, s, "bn", pn, sb)) for n, s in live_e.items()], float(risk["main_scale"]["main_bn"]))
    w = m.apply(lambda r: P.apply_risk(r, risk) if r.notna().any() else r, axis=1)
    info = V.symbol_filters(None, max_age_h=1e9)   # disk cache only, no request
    mn = pd.Series({k: v["min_notional"] for k, v in (info or {}).items()}) if info else pd.Series(dtype=float)
    mins = mn.reindex(w.columns).fillna(5.0)
    last = w.ffill().iloc[-1].fillna(0.0)
    held = (last.abs() * eq0 >= mins.reindex(last.index)) & (last != 0)
    # per-symbol min: a target below the symbol's minimum is not opened (approximation: zero it; live may keep an older bigger position)
    wm = w.where((w.abs() * eq0 >= mins.reindex(w.columns).to_numpy()) | (w == 0) | w.isna(), 0.0)
    res_m, _ = L.run_replay(wm, pn, "bn", sb, risk, eq0)
    res_b, _ = L.run_replay(w, pn, "bn", sb, risk, eq0)
    live = L.daily_live(c, book).pct_change().dropna()
    def day(res):
        r = res.returns[res.returns.index >= pd.Timestamp("2026-11-18", tz="UTC")]
        r.index = r.index + pd.Timedelta(hours=4) - pd.Timedelta(microseconds=1)
        return (1 + r).groupby(r.index.floor("D") + pd.Timedelta(days=1)).prod() - 1
    db, dm = day(res_b), day(res_m)
    days = live.index.intersection(db.index); days = days[days > pd.Timestamp("2026-11-18", tz="UTC")]
    out[book] = {"min_source": "exchange_info" if info else "flat $5 (no exchange_info helper)", "days": len(days),
                 "last_target_gross": round(float(last.abs().sum()), 3), "last_held_gross_after_min": round(float(last[held].abs().sum()), 3),
                 "n_targets": int((last != 0).sum()), "n_above_min": int(held.sum()), "btc_target_usd": round(float(last.get("BTC", 0) * eq0), 1),
                 "ret_live%": round(100 * float((1 + live.reindex(days)).prod() - 1), 2),
                 "ret_replay_band%": round(100 * float((1 + db.reindex(days)).prod() - 1), 2), "corr_band": round(float(live.reindex(days).corr(db.reindex(days))), 2),
                 "ret_replay_symbol_min%": round(100 * float((1 + dm.reindex(days)).prod() - 1), 2), "corr_symbol_min": round(float(live.reindex(days).corr(dm.reindex(days))), 2)}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/lvb_b.json", "w"), indent=1)
