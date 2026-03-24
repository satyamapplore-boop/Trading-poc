import pandas as pd
import pandas_ta as ta


def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["ema9"]  = ta.ema(df["close"], length=9)
    df["ema21"] = ta.ema(df["close"], length=21)
    df["rsi"]   = ta.rsi(df["close"], length=14)
    df["atr"]   = ta.atr(df["high"], df["low"], df["close"], length=14)

    prev_above = df["ema9"].shift(1) > df["ema21"].shift(1)
    curr_above = df["ema9"] > df["ema21"]

    df["crossover_up"]   = (~prev_above) & curr_above
    df["crossover_down"] = prev_above & (~curr_above)

    df["rsi_prev"] = df["rsi"].shift(1)
    df["rsi_crossdown_75"] = (df["rsi_prev"] >= 75) & (df["rsi"] < 75)
    
    buy  = df["crossover_up"]   & df["rsi"].between(40, 70)
    sell = df["crossover_down"] | df["rsi_crossdown_75"]

    df["signal"] = 0
    df.loc[buy,  "signal"] =  1
    df.loc[sell, "signal"] = -1

    return df


# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from data.fetch_data import BTCDataFetcher

    raw = BTCDataFetcher().fetch(timeframe="4h", limit=1000)
    df  = apply_strategy(raw)

    buys  = (df["signal"] ==  1).sum()
    sells = (df["signal"] == -1).sum()
    print(f"Total BUY  signals: {buys}")
    print(f"Total SELL signals: {sells}")
    print()
    print(df[["close", "ema9", "ema21", "rsi", "atr", "signal"]].tail(10))
