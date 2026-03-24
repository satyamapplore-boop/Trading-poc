import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone


class BTCDataFetcher:
    TIMEFRAME_MAP = {
        "1h":  {"binance": "1h",  "kraken": 60,   "cryptocompare": "histohour", "cc_agg": 1,  "yf": "1h"},
        "4h":  {"binance": "4h",  "kraken": 240,  "cryptocompare": "histohour", "cc_agg": 4,  "yf": "1h"},
        "1d":  {"binance": "1d",  "kraken": 1440, "cryptocompare": "histoday",  "cc_agg": 1,  "yf": "1d"},
    }

    def fetch(self, timeframe: str = "1h", limit: int = 1000) -> pd.DataFrame:
        if timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Choose from: {list(self.TIMEFRAME_MAP)}")

        for source_name, method in [
            ("Binance",       self._fetch_binance),
            ("Kraken",        self._fetch_kraken),
            ("CryptoCompare", self._fetch_cryptocompare),
            ("Yahoo Finance", self._fetch_yfinance),
        ]:
            try:
                df = method(timeframe, limit)
                if df is not None and not df.empty:
                    print(f"[OK] Source: {source_name} | Candles fetched: {len(df)}")
                    return df
            except Exception as e:
                print(f"[FAIL] {source_name}: {e}")

        raise RuntimeError("All data sources failed. Check your internet connection.")

    # ------------------------------------------------------------------
    # Binance
    # ------------------------------------------------------------------
    def _fetch_binance(self, timeframe: str, limit: int) -> pd.DataFrame:
        tf = self.TIMEFRAME_MAP[timeframe]["binance"]
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": tf, "limit": min(limit, 1000)}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
        return df.astype(float)

    # ------------------------------------------------------------------
    # Kraken
    # ------------------------------------------------------------------
    def _fetch_kraken(self, timeframe: str, limit: int) -> pd.DataFrame:
        interval = self.TIMEFRAME_MAP[timeframe]["kraken"]
        url = "https://api.kraken.com/0/public/OHLC"
        params = {"pair": "XBTUSD", "interval": interval}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        payload = r.json()

        if payload.get("error"):
            raise RuntimeError(payload["error"])

        # Result key is dynamic (e.g. "XXBTZUSD")
        result = payload["result"]
        key = [k for k in result if k != "last"][0]
        rows = result[key]

        df = pd.DataFrame(rows, columns=[
            "timestamp", "open", "high", "low", "close", "vwap", "volume", "count"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
        df = df.astype(float).tail(limit)
        return df

    # ------------------------------------------------------------------
    # CryptoCompare
    # ------------------------------------------------------------------
    def _fetch_cryptocompare(self, timeframe: str, limit: int) -> pd.DataFrame:
        tf_info = self.TIMEFRAME_MAP[timeframe]
        endpoint = tf_info["cryptocompare"]
        agg = tf_info["cc_agg"]

        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}"
        params = {"fsym": "BTC", "tsym": "USD", "limit": min(limit, 2000), "aggregate": agg}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        payload = r.json()

        if payload.get("Response") == "Error":
            raise RuntimeError(payload.get("Message", "CryptoCompare error"))

        rows = payload["Data"]["Data"]
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("timestamp")[["open", "high", "low", "close", "volumefrom"]]
        df = df.rename(columns={"volumefrom": "volume"})
        return df.astype(float)

    # ------------------------------------------------------------------
    # Yahoo Finance
    # ------------------------------------------------------------------
    def _fetch_yfinance(self, timeframe: str, limit: int) -> pd.DataFrame:
        tf = self.TIMEFRAME_MAP[timeframe]["yf"]

        # yfinance caps intraday history; map limit → period string
        if timeframe == "4h":
            # 4h not native in yf — fetch 1h and resample
            period = "60d"
            df_raw = yf.download("BTC-USD", period=period, interval="1h",
                                 auto_adjust=True, progress=False)
            df_raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                              for c in df_raw.columns]
            df = df_raw[["open", "high", "low", "close", "volume"]].resample("4h").agg({
                "open":   "first",
                "high":   "max",
                "low":    "min",
                "close":  "last",
                "volume": "sum",
            }).dropna()
        else:
            period = "730d" if timeframe == "1d" else "60d"
            df_raw = yf.download("BTC-USD", period=period, interval=tf,
                                 auto_adjust=True, progress=False)
            df_raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                              for c in df_raw.columns]
            df = df_raw[["open", "high", "low", "close", "volume"]]

        if not df.index.tzinfo:
            df.index = df.index.tz_localize("UTC")
        df.index.name = "timestamp"
        return df.astype(float).tail(limit)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    fetcher = BTCDataFetcher()
    df = fetcher.fetch(timeframe="4h", limit=1000)
    print(df.tail(5))
