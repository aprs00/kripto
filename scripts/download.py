"""Refresh datasets. Usage: python -m scripts.download [hl|bn|all|bnall] [--funding-since 2024-07-01]
`all` = hl + bn (nightly). `bnall` = every Binance USDT perp incl. delisted, daily bars (weekly, incremental)."""
import argparse, os, sys
from kripto import data
from kripto.hl import HL

ap = argparse.ArgumentParser()
ap.add_argument("what", nargs="?", default="all")
ap.add_argument("--funding-since", default="2024-07-01")
ap.add_argument("--top", type=int, default=0, help="limit HL coins to top-N by volume (0=all)")
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
    data.hl_update_funding(top, a.funding_since, hl, log)
if a.what in ("bn", "all"):
    data.bn_download(data.BN_SYMBOLS, log=log)
if a.what == "bnall":
    data.bn_download_all_daily(log=log)
log("DONE")
