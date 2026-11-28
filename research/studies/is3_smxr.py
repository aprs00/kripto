"""SMXR: dry-run of the SMX round-to-minimum rule on a COPY of the live ledger with the latest saved targets and live marks.
Writes research/is3/smxr_ab.json. Public read-only requests: HL metaAndAssetCtxs once, Binance premiumIndex once (exchangeInfo cached)."""
import json, shutil, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from kripto import paper as P, venue_bn as V, venue_pair as VP, data
from kripto.hl import HL
from kripto.bn import BN


def main():
    tmp = Path(tempfile.mkdtemp()) / "p.db"
    import sqlite3
    src, dst = sqlite3.connect(f"file:{P.DB}?mode=ro", uri=True), sqlite3.connect(tmp)
    src.backup(dst); src.close(); dst.close()   # consistent snapshot; the live ledger is never written
    cfg, risk = P.load_cfg()
    s = P.Store(tmp)
    hl, bn = HL(min_interval=3.0), BN(min_interval=1.0)
    ctx = {r["name"]: r for r in hl.meta_and_ctxs()}
    hl_marks = {c: float(r["markPx"]) for c, r in ctx.items() if r.get("markPx")}
    sz_dec = {c: int(r["szDecimals"]) for c, r in ctx.items()}
    filters = V.symbol_filters(bn)
    bn_marks = {x["symbol"].removesuffix("USDT"): float(x["markPrice"]) for x in bn.premium_index()
                if x["symbol"].endswith("USDT") and x["symbol"].removesuffix("USDT") in filters}
    saved = {n: pd.Series(json.loads(w)) for n, _, w in s.q("select * from targets")}
    before = {b: dict(s.positions(b)) for (b,) in s.q("select name from books")}
    out, caps = {}, []

    def capture(venue, marks, kw):
        def reb(book, tgt, reason):
            eq = P.book_equity(s, book, marks)[0]
            P.rebalance(None, s, book, tgt, marks, sz_dec, reason, fill=lambda c, d: (marks[c], marks[c], 0.0),
                        round_min=book.startswith("small:"), **kw)
        return reb
    hl_kw = {}
    bn_kw = dict(round_size=lambda c, d: V.round_step(d, filters.get(c, {}).get("step", 0.0)),
                 min_notional=lambda c: filters.get(c, {}).get("min_notional", 5.0),
                 step=lambda c: filters.get(c, {}).get("step", 0.0), fee_rate=V.TAKER_FEE_BN)
    for venue, marks, kw, main in (("hl", hl_marks, hl_kw, "main"), ("bn", bn_marks, bn_kw, "main_bn")):
        entries = {n: sc for n, sc in cfg.items() if P.venue_of(sc) == venue}
        strat_w = {n: saved[n] for n in entries if n in saved and entries[n].get("status") != "retired"}
        P.run_books(s, entries, risk, marks, strat_w, "DRYRUN", main, capture(venue, marks, kw))
    # pair books: targets rounded with the shipped pair rule (no trading in the copy: report targets only)
    pm = {}
    for col in set().union(*[set(saved[n].index) for n in saved if n.endswith("@pair")] or [set()]):
        c, v = VP.leg(col)
        pm[col] = hl_marks.get(c, 0.0) if v == "hl" else bn_marks.get(data.hl_to_bn(c), 0.0)
    rows = []
    for (b,) in s.q("select name from books"):
        if not b.startswith("small:") or P.book_venue(b) == "pair":
            continue
        venue = P.book_venue(b)
        marks = hl_marks if venue == "hl" else bn_marks
        big = b.removeprefix("small:")
        big = big if s.q("select 1 from books where name=?", big) else f"shadow:{big}"
        def gross(book, pos):
            eq = P.book_equity(s, book, marks)[0]
            g = {c: abs(z) * marks.get(c, 0.0) / eq for c, z in pos.items() if abs(z) > 0}
            return eq, g
        eq_s, g_now = gross(b, before.get(b, {}))
        _, g_new = gross(b, s.positions(b))
        _, g_big = gross(big, s.positions(big))
        tw = max(g_new.values()) if g_new else 0.0
        if tw > risk["max_asset_weight"] + 1e-6 or sum(g_new.values()) > risk["max_gross"]:
            caps.append({"book": b, "max_w": round(tw, 3), "coin": max(g_new, key=g_new.get), "gross": round(sum(g_new.values()), 3)})
        fills = s.q("select coalesce(sum(abs(size*px)),0), coalesce(sum(fee),0), count(*) from fills where book=? and reason='bar DRYRUN'", b)[0]
        rows.append({"book": b, "big": big, "eq": round(eq_s, 2), "names_now": len(g_now), "names_new": len(g_new), "names_big": len(g_big),
                     "gross_now": round(sum(g_now.values()), 3), "gross_new": round(sum(g_new.values()), 3), "gross_big": round(sum(g_big.values()), 3),
                     "deployed_now": round(sum(g_now.values()) / max(sum(g_big.values()), 1e-9), 2),
                     "deployed_new": round(sum(g_new.values()) / max(sum(g_big.values()), 1e-9), 2),
                     "max_w_new": round(tw, 3), "traded": round(fills[0], 2), "fees": round(fills[1], 4), "n_fills": fills[2]})
    pair = []
    for n in saved:
        if not n.endswith("@pair") or cfg.get(n, {}).get("status") == "retired":
            continue
        for b in (f"small:{n}",):
            eq = P.book_equity(s, b, pm)[0] if s.q("select 1 from books where name=?", b) else risk["small_equity"]
            t = P.apply_risk(saved[n], risk)
            def mn(col):
                c, v = VP.leg(col)
                return P.MIN_NOTIONAL if v == "hl" else filters.get(data.hl_to_bn(c), {}).get("min_notional", 5.0)
            def st(col):
                c, v = VP.leg(col)
                return 10.0 ** -sz_dec.get(c, 4) if v == "hl" else filters.get(data.hl_to_bn(c), {}).get("step", 0.0)
            old = VP.whole_pairs(t, eq, mn)
            new = VP.whole_pairs(VP.round_pairs_to_min(t, eq, lambda x: P.effective_min(mn(x), st(x), pm.get(x, 0.0))), eq, mn)
            pair.append({"book": b, "eq": round(eq, 2), "legs_target": int((t != 0).sum()), "legs_old_rule": int((old != 0).sum()),
                         "legs_new": int((new != 0).sum()), "gross_target": round(float(t.abs().sum()), 3),
                         "gross_old": round(float(old.abs().sum()), 3), "gross_new": round(float(new.abs().sum()), 3),
                         "max_w_new": round(float(new.abs().max()) if len(new) else 0.0, 3)})
    # effective minimum above the per-name cap at $200
    se = risk["small_equity"]
    big_min = sorted([(c, round(P.effective_min(f.get("min_notional", 5.0), f.get("step", 0.0), bn_marks[c]), 2))
                      for c, f in filters.items() if c in bn_marks], key=lambda x: -x[1])
    over = [x for x in big_min if x[1] > risk["max_asset_weight"] * se]
    hl_over = [(c, round(P.effective_min(P.MIN_NOTIONAL, 10.0 ** -sz_dec[c], hl_marks[c]), 2)) for c in hl_marks if c in sz_dec
               and P.effective_min(P.MIN_NOTIONAL, 10.0 ** -sz_dec[c], hl_marks[c]) > risk["max_asset_weight"] * se]
    res = {"books": rows, "pair": pair, "cap_breaches": caps, "bn_effmin_over_cap": over[:20], "hl_effmin_over_cap": hl_over,
           "bn_effmin_top10": big_min[:10]}
    Path("research/is3/smxr_ab.json").write_text(json.dumps(res, indent=1))
    print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(pair).to_string()); print("caps", caps); print("bn over cap", over[:20]); print("hl over cap", hl_over)
    print("bn top10", big_min[:10])


if __name__ == "__main__":
    main()
