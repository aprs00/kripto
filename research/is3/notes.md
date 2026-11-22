# InSilico third pass: running notes (newest last; think-through per item before its first run)

## M0 (2026-11-22, laptop)
Builder checked on 2021-05-19: 169k micro bars, 24.6k range bars of 0.43%. Not a bug: 8.27M trades, ids and times in order, but 12:00–14:00 UTC the book was torn and trades
bounce 30–40 bp between bid and ask in the same millisecond (realized vol 0.22 on 1-min closes, 0.32 on 1-s). TRAP for M1–M6: in torn minutes range bars are bid-ask bounce.
Every M-form must report results with and without bars that complete in < 1 s (t1 − t0), and entries at the NEXT trade's far side (+spread), not at the bar close.
RAM 1.15 GB peak per worker (busiest day), 3–15 s a day → `--workers 1`, 45-min chunks:
  systemd-run --user --unit is3-m0 -p Nice=19 -p MemoryMax=1800M -p RuntimeMaxSec=2700 --working-directory=$HOME/kripto .venv/bin/python -m scripts.mbars_build BTCUSDT ETHUSDT SOLUSDT --start 2021-01-01 --end 2023-12-31 --workers 1
Progress = number of files in data/bn/mbars/<SYM>/ (1095 each for the explore years).
