"""Refresh all datasets. Usage: python -m scripts.download [hl|bn|all] [--funding-since 2024-07-01]"""
import argparse, sys
from kripto import data
from kripto.hl import HL

ap = argparse.ArgumentParser()
ap.add_argument("what", nargs="?", default="all")
ap.add_argument("--funding-since", default="2024-07-01")
ap.add_argument("--top", type=int, default=0, help="limit HL coins to top-N by volume (0=all)")
a = ap.parse_args()
log = lambda m: print(m, flush=True)
if a.what in ("hl", "all"):
    hl = HL()
    uni = data.hl_universe(hl)
    coins = list(uni["name"])
    if a.top:
        coins = coins[: a.top]
    log(f"HL coins: {len(coins)}")
    for iv in ("1d", "4h", "1h"):
        data.hl_update_candles(coins, iv, hl, log)
    data.hl_update_funding(coins, a.funding_since, hl, log)
if a.what in ("bn", "all"):
    data.bn_download(data.BN_SYMBOLS, log=log)
log("DONE")
