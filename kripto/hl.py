"""Minimal Hyperliquid public /info client (read-only, no keys, rate-limit friendly)."""
from __future__ import annotations

import time

import requests

URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


class HL:
    def __init__(self, min_interval: float = 3.0, timeout: float = 30.0):
        self.s = requests.Session()
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = 0.0

    def post(self, body: dict, retries: int = 8):
        delay = 2.0
        for attempt in range(retries):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                r = self.s.post(URL, json=body, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
                if r.status_code not in (429, 500, 502, 503, 504):
                    r.raise_for_status()
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise RuntimeError(f"HL request failed after {retries} retries: {body}")

    # ---- endpoints -------------------------------------------------------
    def meta_and_ctxs(self) -> list[dict]:
        meta, ctxs = self.post({"type": "metaAndAssetCtxs"})
        out = []
        for a, c in zip(meta["universe"], ctxs):
            out.append({**a, **c})
        return out

    def all_mids(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.post({"type": "allMids"}).items()}

    def l2_book(self, coin: str) -> dict:
        return self.post({"type": "l2Book", "coin": coin})

    def candles(self, coin: str, interval: str, start_ms: int, end_ms: int) -> list[dict]:
        """Paginates forward. HL only serves the most recent ~5000 candles per interval."""
        step = INTERVAL_MS[interval] * 4000
        out, t = [], start_ms
        while t < end_ms:
            chunk = self.post({"type": "candleSnapshot",
                               "req": {"coin": coin, "interval": interval,
                                       "startTime": t, "endTime": min(t + step, end_ms)}})
            out.extend(chunk)
            t = t + step
        dedup = {c["t"]: c for c in out}
        return [dedup[k] for k in sorted(dedup)]

    def funding_history(self, coin: str, start_ms: int, end_ms: int | None = None) -> list[dict]:
        out, t = [], start_ms
        end_ms = end_ms or int(time.time() * 1000)
        while t < end_ms:
            chunk = self.post({"type": "fundingHistory", "coin": coin, "startTime": t, "endTime": end_ms})
            if not chunk:
                break
            out.extend(chunk)
            nt = chunk[-1]["time"] + 1
            if nt <= t or len(chunk) < 500:
                break
            t = nt
        return out
