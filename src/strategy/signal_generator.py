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

    def __init__(self, trading_start=time(9, 15), trading_end=time(14, 0),
                 entry_before_time=time(14, 0)):
        """
        Initialize SignalGenerator

        Args:
            trading_start: Start of trading hours
            trading_end: End of trading hours
            entry_before_time: Latest time to enter a position (default 14:00 to avoid late entries)
        """
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

        if isinstance(entry_before_time, str):
            hours, minutes = map(int, entry_before_time.split(':'))
            self.entry_before_time = time(hours, minutes)
        else:
            self.entry_before_time = entry_before_time

    def generate_signals(self, df, use_enhanced=False):
        """
        Generate buy/sell signals based on Bollinger Bands

        Entry conditions (enhanced mode):
        - Buy: Price touches or crosses below lower Bollinger Band
        - OR Price is within 0.5 standard deviations of lower band (close to oversold)

        Args:
            df: DataFrame with 'close', 'lower_band', 'sma', 'std' columns
            use_enhanced: Use enhanced signal generation for more trades

        Returns:
            DataFrame with added 'buy_signal', 'sell_signal' columns
        """
        result_df = df.copy()

        result_df['buy_signal'] = 0
        result_df['sell_signal'] = 0

        # Entry Signal 1: Price crosses below or touches lower Bollinger Band
        # Previous price was above lower band: Pt-1 > LowerBand(t-1)
        # Current price is at or below lower band: Pt <= LowerBandt
        result_df['prev_price_above_lower'] = result_df['close'].shift(1) > result_df['lower_band'].shift(1)
        result_df['curr_price_at_lower'] = result_df['close'] <= result_df['lower_band']

        # Entry Signal 2: Enhanced - Price is close to lower band (within 0.5 std)
        if use_enhanced and 'std' in result_df.columns:
            result_df['price_near_lower'] = result_df['close'] <= (result_df['lower_band'] + 0.5 * result_df['std'])
            result_df['prev_price_above_lower_enhanced'] = result_df['close'].shift(1) > (result_df['lower_band'].shift(1) + 0.5 * result_df['std'].shift(1))

            # Combined entry signal (Signal 1 OR Signal 2)
            result_df['buy_signal'] = (
                (
                    (result_df['prev_price_above_lower']) &
                    (result_df['curr_price_at_lower'])
                ) |
                (
                    (result_df['prev_price_above_lower_enhanced']) &
                    (result_df['price_near_lower'])
                )
            ) & self._is_within_trading_hours(result_df['datetime']) & self._is_before_entry_time(result_df['datetime'])
        else:
            # Original signal
            result_df['buy_signal'] = (
                (result_df['prev_price_above_lower']) &
                (result_df['curr_price_at_lower']) &
                self._is_within_trading_hours(result_df['datetime']) &
                self._is_before_entry_time(result_df['datetime'])
            )

        result_df['buy_signal'] = result_df['buy_signal'].astype(int)

        # Clean up intermediate columns
        cols_to_drop = ['prev_price_above_lower', 'curr_price_at_lower']
        if use_enhanced and 'std' in result_df.columns:
            cols_to_drop.extend(['price_near_lower', 'prev_price_above_lower_enhanced'])
        result_df.drop(cols_to_drop, axis=1, inplace=True)

        return result_df

    def _is_within_trading_hours(self, datetimes):
        """Check if datetime is within trading hours"""
        return (datetimes.dt.time >= self.trading_start) & (datetimes.dt.time <= self.trading_end)

    def _is_before_entry_time(self, datetimes):
        """Check if datetime is before the latest entry time"""
        return datetimes.dt.time < self.entry_before_time
