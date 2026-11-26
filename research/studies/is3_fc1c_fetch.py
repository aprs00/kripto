"""FC1C data: backfill HL funding history before 2024-07-01 (public /info fundingHistory) for coins with HL candles before 2024-06,
oldest listings first. Resumable: finished coins go to data/is3/fc1c_fetch_done.json; each coin's file is written once it is complete.
HL client min_interval 4 s (> the 3 s rule; the IP is shared). Usage: python -m research.studies.is3_fc1c_fetch [deadline_min]"""
import json, sys, time
import pandas as pd
from kripto import data
from kripto.hl import HL

SINCE = "2023-05-01"
CUT = int(pd.Timestamp("2024-07-01", tz="UTC").timestamp() * 1000)
DONE = data.DATA / "is3" / "fc1c_fetch_done.json"


def main():
    deadline = time.time() + 60 * float(sys.argv[1] if len(sys.argv) > 1 else 40)
    h = data.load_panel("hl", "1d")["close"]
    fv = h.apply(lambda s: s.first_valid_index()).dropna()
    coins = [c for c in fv.sort_values().index if fv[c] < pd.Timestamp("2024-06-01", tz="UTC")]
    del h
    done = set(json.load(open(DONE))) if DONE.exists() else set()
    hl = HL(min_interval=4.0)
    since_ms = int(pd.Timestamp(SINCE, tz="UTC").timestamp() * 1000)
    fd = data.DATA / "hl" / "funding"
    for i, c in enumerate(coins):
        if c in done:
            continue
        if time.time() > deadline:
            print("deadline; stop", flush=True); break
        p = fd / f"{c}.parquet"
        old = pd.read_parquet(p) if p.exists() else None
        end = int(old["time"].min()) - 1 if old is not None and len(old) else CUT
        rows = hl.funding_history(c, since_ms, min(end, CUT)) if end > since_ms else []
        if rows:
            df = pd.DataFrame(rows)[["time", "fundingRate", "premium"]]
            df["fundingRate"] = df["fundingRate"].astype(float); df["premium"] = df["premium"].astype(float)
            df["time"] = df["time"].astype("int64")
            old = pd.read_parquet(p) if p.exists() else None    # re-read: the hourly trader may have appended rows during the fetch
            if old is not None:
                df = pd.concat([df, old]).drop_duplicates("time", keep="last")
            df.sort_values("time").reset_index(drop=True).to_parquet(p)
        done.add(c); json.dump(sorted(done), open(DONE, "w"))
        print(f"{i+1}/{len(coins)} {c} +{len(rows)} from {pd.to_datetime(rows[0]['time'], unit='ms') if rows else '-'}", flush=True)


if __name__ == "__main__":
    main()
