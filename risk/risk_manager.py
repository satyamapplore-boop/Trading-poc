class RiskManager:
    def __init__(
        self,
        capital: float = 100_000,
        risk_per_trade: float = 0.02,
        stop_type: str = "trailing",
        fixed_stop_pct: float = 0.05,
        trailing_stop_pct: float = 0.04,
        atr_multiplier: float = 2.0,
    ):
        if stop_type not in ("fixed", "trailing", "dynamic"):
            raise ValueError(f"stop_type must be 'fixed', 'trailing', or 'dynamic', got '{stop_type}'")

        self.capital           = capital
        self.risk_per_trade    = risk_per_trade
        self.stop_type         = stop_type
        self.fixed_stop_pct    = fixed_stop_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.atr_multiplier    = atr_multiplier

        self.position      = None
        self.entry_price   = None
        self.stop_price    = None
        self.highest_price = None

    # ------------------------------------------------------------------

    def calculate_position_size(self, entry_price: float, stop_price: float) -> float:
        risk_amount       = self.capital * self.risk_per_trade
        stop_distance_pct = abs(entry_price - stop_price) / entry_price
        if stop_distance_pct == 0:
            raise ValueError("entry_price and stop_price are identical; cannot size position")
        size_btc = risk_amount / (stop_distance_pct * entry_price)
        return round(size_btc, 6)

    # ------------------------------------------------------------------

    def open_position(self, entry_price: float, atr: float = None) -> dict:
        self.entry_price   = entry_price
        self.highest_price = entry_price

        if self.stop_type == "fixed":
            self.stop_price = entry_price * (1 - self.fixed_stop_pct)
        elif self.stop_type == "trailing":
            self.stop_price = entry_price * (1 - self.trailing_stop_pct)
        elif self.stop_type == "dynamic":
            if atr is not None:
                self.stop_price = entry_price - (self.atr_multiplier * atr)
            else:
                # Fallback to fixed when ATR is unavailable
                self.stop_price = entry_price * (1 - self.fixed_stop_pct)

        size_btc = self.calculate_position_size(entry_price, self.stop_price)
        size_usd = round(size_btc * entry_price, 2)

        self.position = {
            "entry_price": entry_price,
            "stop_price":  self.stop_price,
            "size_btc":    size_btc,
            "size_usd":    size_usd,
        }
        return self.position

    # ------------------------------------------------------------------

    def update_trailing_stop(self, current_price: float) -> None:
        if self.stop_type not in ("trailing", "dynamic"):
            return
        if self.position is None:
            return

        if current_price > self.highest_price:
            self.highest_price = current_price
            new_stop = current_price * (1 - self.trailing_stop_pct)
            if new_stop > self.stop_price:          # never move stop down
                self.stop_price              = new_stop
                self.position["stop_price"]  = new_stop

    # ------------------------------------------------------------------

    def check_stop_triggered(self, current_price: float) -> bool:
        if self.stop_price is None:
            return False
        return current_price <= self.stop_price

    # ------------------------------------------------------------------

    def close_position(self, exit_price: float) -> dict:
        if self.position is None:
            raise RuntimeError("No open position to close")

        size_btc   = self.position["size_btc"]
        pnl_usd    = (exit_price - self.entry_price) * size_btc
        pnl_pct    = ((exit_price - self.entry_price) / self.entry_price) * 100
        self.capital += pnl_usd

        result = {
            "entry_price": self.entry_price,
            "exit_price":  exit_price,
            "size_btc":    size_btc,
            "pnl_usd":     round(pnl_usd, 2),
            "pnl_pct":     round(pnl_pct, 4),
            "stop_was":    self.stop_price,
        }

        self.position      = None
        self.entry_price   = None
        self.stop_price    = None
        self.highest_price = None

        return result


# ----------------------------------------------------------------------
if __name__ == "__main__":
    rm = RiskManager(capital=100_000, stop_type="trailing", trailing_stop_pct=0.04)

    print("Opening position at $65,000 ...")
    pos = rm.open_position(entry_price=65_000)
    print(f"  Position : {pos}")

    prices = [66_000, 67_500, 69_000, 70_000]
    for p in prices:
        rm.update_trailing_stop(p)
        triggered = rm.check_stop_triggered(p)
        print(f"  Price ${p:,} → stop now ${rm.stop_price:,.2f} | triggered={triggered}")

    print("\nClosing position at $68,000 ...")
    result = rm.close_position(exit_price=68_000)
    print(f"  Result   : {result}")
    print(f"  New capital: ${rm.capital:,.2f}")
