import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.fetch_data import BTCDataFetcher
from strategy.ema_rsi_strategy import apply_strategy
from risk.risk_manager import RiskManager


def run_backtest(
    timeframe: str = "4h",
    capital: float = 100_000,
    stop_type: str = "trailing",
    risk_per_trade: float = 0.02,
) -> dict:
    # ------------------------------------------------------------------ data
    raw = BTCDataFetcher().fetch(timeframe=timeframe, limit=1000)
    df  = apply_strategy(raw).dropna()

    # ------------------------------------------------------------------ init
    rm     = RiskManager(capital=capital, stop_type=stop_type, risk_per_trade=risk_per_trade)
    trades = []
    equity_curve = []
    in_position  = False
    entry_date   = None

    # ------------------------------------------------------------------ loop
    for ts, row in df.iterrows():
        if in_position:
            rm.update_trailing_stop(row["close"])

            stop_hit = rm.check_stop_triggered(row["close"])
            sell_sig = row["signal"] == -1

            if stop_hit or sell_sig:
                result = rm.close_position(row["close"])
                trades.append({
                    "entry_date":  str(entry_date),
                    "exit_date":   str(ts),
                    "entry_price": result["entry_price"],
                    "exit_price":  result["exit_price"],
                    "size_btc":    result["size_btc"],
                    "pnl_usd":     result["pnl_usd"],
                    "pnl_pct":     result["pnl_pct"],
                    "exit_reason": "stop_loss" if stop_hit else "signal",
                })
                in_position = False
                entry_date  = None

        else:
            if row["signal"] == 1:
                atr = row["atr"] if stop_type == "dynamic" else None
                rm.open_position(entry_price=row["close"], atr=atr)
                in_position = True
                entry_date  = ts

        equity_curve.append(rm.capital)

    # ------------------------------------------------------------------ metrics
    final_capital    = rm.capital
    total_return_pct = ((final_capital - capital) / capital) * 100

    wins   = [t for t in trades if t["pnl_usd"] > 0]
    losses = [t for t in trades if t["pnl_usd"] <= 0]

    total_trades   = len(trades)
    winning_trades = len(wins)
    losing_trades  = len(losses)
    win_rate_pct   = (winning_trades / total_trades * 100) if total_trades else 0.0

    total_win_usd  = sum(t["pnl_usd"] for t in wins)
    total_loss_usd = abs(sum(t["pnl_usd"] for t in losses))
    profit_factor  = (total_win_usd / total_loss_usd) if total_loss_usd else float("inf")

    avg_win_usd  = (total_win_usd  / winning_trades) if winning_trades else 0.0
    avg_loss_usd = (total_loss_usd / losing_trades)  if losing_trades  else 0.0

    # max drawdown
    equity_arr = np.array(equity_curve)
    peak       = np.maximum.accumulate(equity_arr)
    drawdowns  = (peak - equity_arr) / peak * 100
    max_drawdown_pct = float(np.max(drawdowns)) if len(drawdowns) else 0.0

    summary = {
        "timeframe":        timeframe,
        "stop_type":        stop_type,
        "risk_per_trade":   risk_per_trade,
        "initial_capital":  capital,
        "final_capital":    round(final_capital, 2),
        "total_return_pct": round(total_return_pct, 4),
        "total_trades":     total_trades,
        "winning_trades":   winning_trades,
        "losing_trades":    losing_trades,
        "win_rate_pct":     round(win_rate_pct, 2),
        "profit_factor":    round(profit_factor, 4),
        "avg_win_usd":      round(avg_win_usd, 2),
        "avg_loss_usd":     round(avg_loss_usd, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
    }

    # ------------------------------------------------------------------ print
    col_w = 28
    print("\n" + "=" * 50)
    print("  BACKTEST SUMMARY")
    print("=" * 50)
    rows = [
        ("Timeframe",         summary["timeframe"]),
        ("Stop type",         summary["stop_type"]),
        ("Risk per trade",    f"{summary['risk_per_trade']*100:.1f}%"),
        ("Initial capital",   f"${summary['initial_capital']:,.2f}"),
        ("Final capital",     f"${summary['final_capital']:,.2f}"),
        ("Total return",      f"{summary['total_return_pct']:.4f}%"),
        ("Max drawdown",      f"{summary['max_drawdown_pct']:.4f}%"),
        ("Total trades",      summary["total_trades"]),
        ("Winning trades",    summary["winning_trades"]),
        ("Losing trades",     summary["losing_trades"]),
        ("Win rate",          f"{summary['win_rate_pct']:.2f}%"),
        ("Profit factor",     f"{summary['profit_factor']:.4f}"),
        ("Avg win",           f"${summary['avg_win_usd']:,.2f}"),
        ("Avg loss",          f"${summary['avg_loss_usd']:,.2f}"),
    ]
    for label, value in rows:
        print(f"  {label:<{col_w}} {value}")
    print("=" * 50 + "\n")

    # ------------------------------------------------------------------ save
    results = {
        "summary":      summary,
        "trades":       trades,
        "equity_curve": [round(v, 2) for v in equity_curve],
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "results", "backtest_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {os.path.normpath(out_path)}")

    return results


# ----------------------------------------------------------------------
if __name__ == "__main__":
    run_backtest()
