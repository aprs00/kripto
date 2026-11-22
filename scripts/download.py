"""Refresh datasets. Usage: python -m scripts.download [hl|bn|all|bnall|bn100|metrics] [--funding-since 2024-07-01]
`all` = hl + bn (nightly). `bnall` = every Binance USDT perp incl. delisted, daily bars (weekly, incremental)."""
import argparse, os, sys
from kripto import data
from kripto.hl import HL

ap = argparse.ArgumentParser()
ap.add_argument("what", nargs="?", default="all")
ap.add_argument("--funding-since", default="2024-07-01")
ap.add_argument("--metrics-max", type=int, default=15000, help="metrics coin-day files per run (T5b backfill; 0 = skip)")
ap.add_argument("--top", type=int, default=0, help="limit HL coins to top-N by volume (0=all)")
ap.add_argument("--funding-extra", type=int, default=8, help="per run, also start funding history for this many coins that\n"
                "have none yet (listing shorts and the cross-venue pair book need funding beyond the top-N)")
a = ap.parse_args()
log = lambda m: print(m, flush=True)
if a.what in ("hl", "all"):
    hl = HL(min_interval=float(os.environ.get("KRIPTO_HL_INTERVAL", "3.0")))
    uni = data.hl_universe(hl)
    coins = list(uni["name"])                      # all perps incl. delisted -> no survivorship bias
    top = coins[: a.top] if a.top else coins
    log(f"HL coins: {len(coins)} (top {len(top)} for 1h candles + funding)")
    for iv in ("1d", "4h"):
        data.hl_update_candles(coins, iv, hl, log)
    data.hl_update_candles(top, "1h", hl, log)
    # Funding beyond the top-N: keep every coin that already has a file current (1 call each), and each night start a
    # few more (full history = ~40 calls). A coin that returns nothing is not retried for 30 days.
    import json, time
    fdir = data.DATA / "hl" / "funding"
    fdir.mkdir(parents=True, exist_ok=True)
    tried_p = fdir / "_tried.json"
    tried = json.loads(tried_p.read_text()) if tried_p.exists() else {}
    have = [c for c in coins if (fdir / f"{c}.parquet").exists()]
    fresh = [c for c in coins if c not in have and time.time() - tried.get(c, 0) > 30 * 86400][: a.funding_extra]
    data.hl_update_funding(list(dict.fromkeys(top + have + fresh)), a.funding_since, hl, log)
    tried.update({c: time.time() for c in fresh})
    tried_p.write_text(json.dumps(tried))
if a.what in ("bn", "all"):
    data.bn_download(data.BN_SYMBOLS, log=log)
if a.what == "bn100":   # survivorship-free hourly top-100 (data.bn_top_symbols), monthly archives, incremental
    syms = data.bn_top_symbols(100)
    log(f"bn100: {len(syms)} symbols ever in the point-in-time top 100")
    data.bn_download(syms, workers=8, log=log, kdir=data.BN100_DIR, funding=False)
if a.what == "bnall":
    with data.refreshing("bnall"):   # the refresh is alphabetical and takes ~1 h: readers WARN meanwhile (half the coins are older)
        data.bn_download_all_daily(log=log)
        from kripto.bn import BN
        log(f"[bn tradfi] {data.update_bn_tradfi(BN().exchange_info())} new stock/commodity perps excluded")
        data.bn_all_recent(log=log)   # past the last monthly archive (fapi, polite)
if a.what in ("all", "metrics") and a.metrics_max > 0:
    # T5b (2026-11-19): Binance positioning metrics for every coin-day in the point-in-time top 60 since 2021 (survivorship-free),
    # incremental and capped per run so the backfill spreads over nights; afterwards it only adds the newest days.
    try:
        data.bn_download_metrics(data.bn_metrics_targets(60, "2021-01-01"), max_files=a.metrics_max, log=log)
    except Exception as e:                  # never fail the nightly price refresh because of this
        log(f"[metrics] FAILED: {e!r}")
log("DONE")
