import pandas as pd
import numpy as np
from datetime import time

class SignalGenerator:
    """
    Signal Generator for BB SMA Reversion Strategy

    Entry Signal (Buy):
    - Previous price was above the lower Bollinger Band: Pt-1 > LowerBand(t-1)
    - Current price crosses below or touches the lower band: Pt <= LowerBandt
    - This indicates an oversold condition where price has dropped to or below the lower band

    Exit Conditions:
    - Take-Profit: Pt >= SMA20 (price has returned to the mean)
    - Stop-Loss: Unrealized profit <= -2 points
    - Time-Based Exit: No overnight positions (close at ATC session)
    """

    def __init__(self, trading_start=time(9, 15), trading_end=time(14, 30)):
        if isinstance(trading_start, str):
            hours, minutes = map(int, trading_start.split(':'))
            self.trading_start = time(hours, minutes)
        else:
            self.trading_start = trading_start

        if isinstance(trading_end, str):
            hours, minutes = map(int, trading_end.split(':'))
            self.trading_end = time(hours, minutes)
        else:
            self.trading_end = trading_end

    def generate_signals(self, df):
        """
        Generate buy/sell signals based on Bollinger Bands crossover

        Entry conditions:
        - Buy: Pt-1 > LowerBand(t-1) AND Pt <= LowerBandt
        - (Price was above lower band, now crosses to or below it - oversold)

        Args:
            df: DataFrame with 'close', 'lower_band', 'sma' columns

        Returns:
            DataFrame with added 'buy_signal', 'sell_signal' columns
        """
        result_df = df.copy()

        result_df['buy_signal'] = 0
        result_df['sell_signal'] = 0

        # Entry Signal: Price crosses below or touches lower Bollinger Band
        # Previous price was above lower band: Pt-1 > LowerBand(t-1)
        # Current price is at or below lower band: Pt <= LowerBandt
        result_df['prev_price_above_lower'] = result_df['close'].shift(1) > result_df['lower_band'].shift(1)
        result_df['curr_price_at_lower'] = result_df['close'] <= result_df['lower_band']

        # Combined entry signal
        result_df['buy_signal'] = (
            (result_df['prev_price_above_lower']) &
            (result_df['curr_price_at_lower']) &
            self._is_within_trading_hours(result_df['datetime'])
        )

        result_df['buy_signal'] = result_df['buy_signal'].astype(int)

        # Clean up intermediate columns
        result_df.drop(['prev_price_above_lower', 'curr_price_at_lower'], axis=1, inplace=True)

        return result_df

    def _is_within_trading_hours(self, datetimes):
        """Check if datetime is within trading hours"""
        return (datetimes.dt.time >= self.trading_start) & (datetimes.dt.time <= self.trading_end)
