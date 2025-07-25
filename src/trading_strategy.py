class TradingStrategy:
    """
    Handles the trading logic based on EMA crossover without using pandas.
    """
    def __init__(self, short_ema_period: int = 12, long_ema_period: int = 26):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period

    def analyze_klines(self, klines: list) -> str:
        """
        Analyzes kline data to determine a trading signal (LONG, SHORT, HOLD).
        """
        if len(klines) < self.long_ema_period:
            return "HOLD"

        # Extract close prices from kline data
        close_prices = [float(kline[4]) for kline in klines]
        
        # Calculate EMAs manually
        short_ema = self._calculate_ema(close_prices, self.short_ema_period)
        long_ema = self._calculate_ema(close_prices, self.long_ema_period)
        
        # We need at least two data points to check for a crossover
        if len(short_ema) < 2 or len(long_ema) < 2:
            return "HOLD"
            
        # Get the last two EMA values for checking the crossover
        current_short = short_ema[-1]
        current_long = long_ema[-1]
        prev_short = short_ema[-2]
        prev_long = long_ema[-2]
        
        signal = "HOLD"

        # Check for EMA crossover signals
        # Golden Cross (Buy Signal)
        if prev_short < prev_long and current_short > current_long:
            signal = "LONG"
        # Death Cross (Sell Signal)
        elif prev_short > prev_long and current_short < current_long:
            signal = "SHORT"
        
        return signal

    def _calculate_ema(self, prices: list, period: int) -> list:
        """
        Calculate Exponential Moving Average (EMA) manually without pandas.
        This ensures the function is self-contained and free of heavy dependencies.
        """
        if len(prices) < period:
            return []

        ema_values = []
        # Standard EMA multiplier
        multiplier = 2 / (period + 1)
        
        # Start with a Simple Moving Average (SMA) for the first EMA value
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # Calculate EMA for the rest of the prices
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        # To align the length of EMA list with the original price list for easier indexing,
        # we can pad the beginning. However, for crossover logic, we only need the recent values,
        # so returning the calculated EMAs is sufficient. Here we return a list that
        # corresponds to the prices from `period-1` onwards.
        return ema_values


# Create a single, reusable instance of the strategy class
trading_strategy = TradingStrategy()
