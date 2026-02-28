import pandas as pd
import numpy as np
from datetime import datetime, time
import logging
import os

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process raw tick data into OHLCV and add technical indicators"""

    def __init__(self, trading_start=time(9, 0), trading_end=time(15, 0), cache_dir=None):
        self.trading_start = trading_start
        self.trading_end = trading_end

        if cache_dir is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            self.cache_dir = os.path.join(project_root, 'data_cache', 'ohlcv')
        else:
            self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def resample_to_ohlcv(self, df, timeframe='15min'):
        """Resample tick data to OHLCV format"""
        if df.empty:
            logger.warning("Empty DataFrame provided for resampling")
            return pd.DataFrame()

        # Ensure datetime column exists
        if 'datetime' in df.columns:
            df = df.copy()
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

        # Filter trading hours
        trading_hours_mask = self.filter_trading_hours(df.index)
        df_trading = df[trading_hours_mask]

        if df_trading.empty:
            logger.warning("No data within trading hours")
            return pd.DataFrame()

        has_quantity = 'quantity' in df.columns

        # Resample to OHLCV
        ohlcv = pd.DataFrame()
        ohlcv['open'] = df_trading['price'].resample(timeframe).first()
        ohlcv['high'] = df_trading['price'].resample(timeframe).max()
        ohlcv['low'] = df_trading['price'].resample(timeframe).min()
        ohlcv['close'] = df_trading['price'].resample(timeframe).last()

        if has_quantity:
            ohlcv['volume'] = df_trading['quantity'].resample(timeframe).sum()
        else:
            ohlcv['volume'] = df_trading['price'].resample(timeframe).count()

        ohlcv = ohlcv.dropna(subset=['open', 'high', 'low', 'close'])

        # Add ticker symbol if available
        if 'tickersymbol' in df.columns:
            ticker_groups = df_trading['tickersymbol'].resample(timeframe).apply(
                lambda x: x.mode()[0] if not x.empty else np.nan
            )
            ohlcv['tickersymbol'] = ticker_groups

        logger.info(f"Resampled to {len(ohlcv)} {timeframe} candles")

        return ohlcv

    def filter_trading_hours(self, datetimes):
        """Filter data to only include trading hours"""
        times = pd.Series([dt.time() for dt in datetimes], index=datetimes)
        return (times >= self.trading_start) & (times <= self.trading_end)

    def add_indicators(self, df, bb_window=20, bb_std=2.0):
        """Add Bollinger Bands and SMA indicators to OHLCV data"""
        result = df.copy()

        # Calculate SMA (Simple Moving Average)
        result['sma'] = result['close'].rolling(window=bb_window).mean()

        # Calculate Standard Deviation
        result['std'] = result['close'].rolling(window=bb_window).std()

        # Calculate Upper and Lower Bollinger Bands
        result['upper_band'] = result['sma'] + (bb_std * result['std'])
        result['lower_band'] = result['sma'] - (bb_std * result['std'])

        return result

    def prepare_data_for_backtest(self, ohlcv_df):
        """Prepare OHLCV data for backtesting"""
        if ohlcv_df.empty:
            return ohlcv_df

        df = ohlcv_df.copy()

        # Reset index if datetime is index
        if isinstance(df.index, pd.DatetimeIndex):
            df.reset_index(inplace=True)

        # Ensure datetime column exists
        if 'datetime' not in df.columns and 'date' in df.columns:
            df.rename(columns={'date': 'datetime'}, inplace=True)

        # Add date and time columns
        df['date'] = df['datetime'].dt.date
        df['time'] = df['datetime'].dt.time

        return df

    def split_train_test(self, df, train_end_date, test_start_date=None):
        """Split data into train and test sets"""
        if df.empty:
            return df.copy(), df.copy()

        if isinstance(df.index, pd.DatetimeIndex) and 'datetime' not in df.columns:
            df = df.reset_index()

        train_end = pd.to_datetime(train_end_date)

        if test_start_date is None:
            test_start = train_end + pd.Timedelta(days=1)
        else:
            test_start = pd.to_datetime(test_start_date)

        train_df = df[df['datetime'] <= train_end].copy()
        test_df = df[df['datetime'] >= test_start].copy()

        logger.info(f"Split data into {len(train_df)} training samples and {len(test_df)} testing samples")

        return train_df, test_df
