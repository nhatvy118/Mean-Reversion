import json
import os
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


def run_backtest(start_date='2024-01-01', end_date='2024-12-01',
                 bb_window=20, bb_std=2.0, timeframe='15min',
                 use_enhanced_signal=False):
    """Run the backtest

    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        bb_window: Bollinger Bands window period
        bb_std: Bollinger Bands standard deviation multiplier
        timeframe: Timeframe for candles (5min, 15min, 30min, 1h)
        use_enhanced_signal: Use enhanced signal generation for more trades

    Returns:
        results: Backtest results with trades
        metrics: Performance metrics
        df_signals: DataFrame with signals
    """

    # Load configuration
    config = load_config()
    initial_balance = config['backtest']['initial_capital']
    commission = config['backtest']['commission']
    stop_loss_points = config['risk_management']['stop_loss_points']
    max_positions_per_day = config['risk_management']['max_positions_per_day']

    # Load data from database
    print(f"Loading data from database: {start_date} to {end_date}")
    loader = DataLoader()
    tick_data = loader.get_active_contract_data(start_date, end_date)

    if tick_data.empty:
        raise ValueError("No data loaded from database")

    # Resample to OHLCV
    processor = DataProcessor()
    ohlcv_df = processor.resample_to_ohlcv(tick_data, timeframe=timeframe)
    print(f"Loaded {len(ohlcv_df)} candles")

    # Add indicators (Bollinger Bands)
    df_with_indicators = processor.add_indicators(ohlcv_df, bb_window=bb_window, bb_std=bb_std)

    # Prepare for backtest
    df_prepared = processor.prepare_data_for_backtest(df_with_indicators)

    # Generate signals
    signal_generator = SignalGenerator()
    df_signals = signal_generator.generate_signals(df_prepared, use_enhanced=use_enhanced_signal)

    # Drop rows with NaN in key columns
    df_signals = df_signals.dropna(subset=['sma', 'lower_band', 'buy_signal'])

    # Run backtest
    backtest_engine = BacktestEngine(
        initial_balance=initial_balance,
        commission=commission,
        stop_loss_points=stop_loss_points,
        max_positions_per_day=max_positions_per_day
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


def run_insample_backtest():
    """Step 4: In-sample Backtesting"""
    print("\n" + "="*60)
    print("STEP 4: IN-SAMPLE BACKTESTING")
    print("="*60)

    # In-sample period: 2024-01-01 to 2024-06-30 (6 months)
    results, metrics, df = run_backtest(
        start_date='2024-01-01',
        end_date='2024-06-30',
        bb_window=20,
        bb_std=2.0,
        timeframe='5min',
        use_enhanced_signal=True
    )

    total_trades = len(results['trades'])
    print(f"\nTotal trades: {total_trades}")
    if total_trades < 30:
        print("WARNING: In-sample trades less than 30. Consider adjusting parameters (bb_std, timeframe, enhanced signals).")

    return results, metrics, df


def main():
    """Main function to run backtest"""
    print("=" * 60)
    print("BB SMA Reversion Strategy - Backtest")
    print("=" * 60)

    # Run in-sample backtest
    results, metrics, df_signals = run_insample_backtest()

    # Print results
    performance = PerformanceAnalyzer()
    performance.print_metrics(metrics)

    # Print trade summary
    print("\nTrade Summary (first 30 trades):")
    if not results['trades'].empty:
        print(results['trades'].head(30).to_string())

    return results, metrics


if __name__ == "__main__":
    main()
