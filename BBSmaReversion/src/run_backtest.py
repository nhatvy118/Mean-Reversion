import json
import os
import pandas as pd
import numpy as np
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.strategy.signal_generator import SignalGenerator
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance import PerformanceAnalyzer


def load_config():
    """Load strategy configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'strategy_config.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def generate_dummy_data(start_date='2024-01-01', end_date='2024-06-01', timeframe='15min'):
    """Generate dummy OHLCV data for testing when database is not available"""
    print("Generating dummy data for testing...")

    # Generate date range for trading hours only
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    trading_dates = [d for d in dates if d.weekday() < 5]  # Only weekdays

    candles = []
    base_price = 1350  # Base price for VN30F1M

    for date in trading_dates:
        # Morning session: 09:15 - 11:30
        for hour in range(9, 12):
            for minute in [0, 15, 30, 45]:
                if hour == 9 and minute < 15:
                    continue

                # Skip lunch break: 11:30 - 13:00
                if hour == 11 and minute > 30:
                    continue

                # Afternoon session: 13:00 - 14:45
                if hour == 14 and minute > 45:
                    continue

                dt = pd.Timestamp(year=date.year, month=date.month, day=date.day,
                                  hour=hour, minute=minute)

                # Generate random price with some mean-reverting tendency
                change = np.random.randn() * 2
                base_price = base_price + change

                open_price = base_price + np.random.randn() * 0.5
                high_price = max(open_price, base_price) + abs(np.random.randn()) * 1
                low_price = min(open_price, base_price) - abs(np.random.randn()) * 1
                close_price = base_price
                volume = np.random.randint(100, 1000)

                candles.append({
                    'datetime': dt,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

    df = pd.DataFrame(candles)
    print(f"Generated {len(df)} candles")
    return df


def run_backtest(start_date='2024-01-01', end_date='2024-06-01',
                 bb_window=20, bb_std=2.0, timeframe='15min',
                 use_dummy_data=True):
    """Run the backtest"""

    # Load configuration
    config = load_config()
    initial_balance = config['backtest']['initial_capital']
    commission = config['backtest']['commission']
    stop_loss_points = config['risk_management']['stop_loss_points']

    # Load data
    if use_dummy_data:
        ohlcv_df = generate_dummy_data(start_date, end_date, timeframe)
    else:
        # Try to load from database
        try:
            loader = DataLoader()
            tick_data = loader.get_active_contract_data(start_date, end_date)

            processor = DataProcessor()
            ohlcv_df = processor.resample_to_ohlcv(tick_data, timeframe=timeframe)
        except Exception as e:
            print(f"Error loading data from database: {e}")
            print("Falling back to dummy data...")
            ohlcv_df = generate_dummy_data(start_date, end_date, timeframe)

    # Add indicators (Bollinger Bands)
    processor = DataProcessor()
    df_with_indicators = processor.add_indicators(ohlcv_df, bb_window=bb_window, bb_std=bb_std)

    # Prepare for backtest
    df_prepared = processor.prepare_data_for_backtest(df_with_indicators)

    # Generate signals
    signal_generator = SignalGenerator()
    df_signals = signal_generator.generate_signals(df_prepared)

    # Drop rows with NaN in key columns
    df_signals = df_signals.dropna(subset=['sma', 'lower_band', 'buy_signal'])

    # Run backtest
    backtest_engine = BacktestEngine(
        initial_balance=initial_balance,
        commission=commission,
        stop_loss_points=stop_loss_points
    )
    results = backtest_engine.run_backtest(df_signals)

    # Calculate performance metrics
    performance = PerformanceAnalyzer(risk_free_rate=config['backtest']['risk_free_rate'])
    metrics = performance.calculate_metrics(
        results['trades'],
        results['portfolio_history'],
        initial_balance
    )

    return results, metrics, df_signals


def main():
    """Main function to run backtest"""
    print("=" * 60)
    print("BB SMA Reversion Strategy - Backtest")
    print("=" * 60)

    # Default parameters from config
    config = load_config()
    bb_window = config['parameters']['bb_window']
    bb_std = config['parameters']['bb_std']
    timeframe = config['parameters']['default_timeframe']

    # Run backtest with default parameters
    results, metrics, df_signals = run_backtest(
        start_date='2024-01-01',
        end_date='2024-06-01',
        bb_window=bb_window,
        bb_std=bb_std,
        timeframe=timeframe,
        use_dummy_data=True  # Set to False when database is available
    )

    # Print results
    performance = PerformanceAnalyzer()
    performance.print_metrics(metrics)

    # Print trade summary
    print("\nTrade Summary:")
    if not results['trades'].empty:
        print(results['trades'].to_string())

    return results, metrics


if __name__ == "__main__":
    main()
