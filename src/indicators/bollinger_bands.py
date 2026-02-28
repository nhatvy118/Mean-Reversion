import pandas as pd
import numpy as np

class BollingerBands:
    """Calculate Bollinger Bands and SMA indicators"""

    def __init__(self, window=20, num_std=2.0):
        self.window = window
        self.num_std = num_std

    def calculate(self, df):
        """
        Calculate Bollinger Bands and SMA

        Args:
            df: DataFrame with 'close' column

        Returns:
            DataFrame with added columns: 'sma', 'upper_band', 'lower_band', 'std'
        """
        result = df.copy()

        # Calculate SMA (Simple Moving Average)
        result['sma'] = result['close'].rolling(window=self.window).mean()

        # Calculate Standard Deviation
        result['std'] = result['close'].rolling(window=self.window).std()

        # Calculate Upper and Lower Bollinger Bands
        result['upper_band'] = result['sma'] + (self.num_std * result['std'])
        result['lower_band'] = result['sma'] - (self.num_std * result['std'])

        return result
