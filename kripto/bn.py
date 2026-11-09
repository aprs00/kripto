"""Minimal Binance USDT-M futures PUBLIC market-data client (read-only, no keys, rate-limit friendly).

Paper trading only (CLAUDE.md HARD RULE 1): there are no keys and no signed endpoints here, so this client
cannot place, cancel or query orders. Only the whitelisted public GET endpoints below can be called.
The server IP is shared: default 1 request/s, far below Binance's 2400 weight/min.
"""
from __future__ import annotations

import time

import requests

URL = "https://fapi.binance.com"
ALLOWED = {"/fapi/v1/exchangeInfo", "/fapi/v1/ticker/24hr", "/fapi/v1/premiumIndex", "/fapi/v1/klines",
           "/fapi/v1/depth", "/fapi/v1/fundingRate"}


class BN:
    def __init__(self, min_interval: float = 1.0, timeout: float = 20.0):
        self.s = requests.Session()
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = 0.0

    def get(self, path: str, params: dict | None = None, retries: int = 6):
        if path not in ALLOWED:
            raise ValueError(f"endpoint not whitelisted (public market data only): {path}")
        delay = 2.0
        for attempt in range(retries):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                r = self.s.get(URL + path, params=params, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (418, 429):  # rate limited / IP ban warning: back off hard
                    time.sleep(max(float(r.headers.get("Retry-After", 60)), 60))
                    continue
                if r.status_code < 500:
                    r.raise_for_status()
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise RuntimeError(f"Binance request failed after {retries} retries: {path} {params}")

    # ---- endpoints -------------------------------------------------------
    def exchange_info(self) -> dict:
        return self.get("/fapi/v1/exchangeInfo")

    def ticker_24h(self) -> list[dict]:
        return self.get("/fapi/v1/ticker/24hr")

    def premium_index(self) -> list[dict]:
        return self.get("/fapi/v1/premiumIndex")

    def klines(self, symbol: str, interval: str, start_ms: int | None = None, limit: int = 1500) -> list[list]:
        p = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_ms is not None:
            p["startTime"] = int(start_ms)
        return self.get("/fapi/v1/klines", p)

    def depth(self, symbol: str, limit: int = 20) -> dict:
        return self.get("/fapi/v1/depth", {"symbol": symbol, "limit": limit})

    def funding_rate(self, symbol: str, start_ms: int, end_ms: int | None = None) -> list[dict]:
        p = {"symbol": symbol, "startTime": int(start_ms), "limit": 1000}
        if end_ms is not None:
            p["endTime"] = int(end_ms)
        return self.get("/fapi/v1/fundingRate", p)
