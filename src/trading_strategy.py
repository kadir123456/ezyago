@@ .. @@
-import pandas as pd
 
 class TradingStrategy:
     """
@@ .. @@
     def analyze_klines(self, klines: list) -> str:
         if len(klines) < self.long_ema_period:
             return "HOLD"
 
-        df = pd.DataFrame(klines, columns=[
-            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
-            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
-            'taker_buy_quote_asset_volume', 'ignore'
-        ])
-        df['close'] = pd.to_numeric(df['close'])
-        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
-        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
-
-        last_row = df.iloc[-1]
-        prev_row = df.iloc[-2]
+        # Extract close prices
+        close_prices = [float(kline[4]) for kline in klines]
+        
+        # Calculate EMAs manually
+        short_ema = self._calculate_ema(close_prices, self.short_ema_period)
+        long_ema = self._calculate_ema(close_prices, self.long_ema_period)
+        
+        # Get last two EMA values
+        current_short = short_ema[-1]
+        current_long = long_ema[-1]
+        prev_short = short_ema[-2]
+        prev_long = long_ema[-2]
+        
         signal = "HOLD"
 
-        if prev_row['short_ema'] < prev_row['long_ema'] and last_row['short_ema'] > last_row['long_ema']:
+        # Check for EMA crossover
+        if prev_short < prev_long and current_short > current_long:
             signal = "LONG"
-        elif prev_row['short_ema'] > prev_row['long_ema'] and last_row['short_ema'] < last_row['long_ema']:
+        elif prev_short > prev_long and current_short < current_long:
             signal = "SHORT"
         
         return signal
+    
+    def _calculate_ema(self, prices: list, period: int) -> list:
+        """Calculate EMA manually without pandas"""
+        if len(prices) < period:
+            return prices
+        
+        ema_values = []
+        multiplier = 2 / (period + 1)
+        
+        # Start with SMA for first value
+        sma = sum(prices[:period]) / period
+        ema_values.append(sma)
+        
+        # Calculate EMA for remaining values
+        for i in range(period, len(prices)):
+            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
+            ema_values.append(ema)
+        
+        # Pad the beginning with the first EMA value
+        result = [ema_values[0]] * (period - 1) + ema_values
+        return result