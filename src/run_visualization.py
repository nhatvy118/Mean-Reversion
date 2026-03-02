import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.run_backtest import run_backtest
from src.visualization.backtest import BacktestVisualizer


def visualize_results():
    """Visualize backtest results"""

    print("="*60)
    print("VISUALIZATION")
    print("="*60)

    # Run backtest to get results
    results, metrics, df = run_backtest(
        start_date='2024-01-01',
        end_date='2024-06-30',
        bb_window=20,
        bb_std=2.0,
        timeframe='15min',
        use_enhanced_signal=False
    )

    # Create visualizer
    save_dir = 'readme_results'
    viz = BacktestVisualizer(save_dir=save_dir)

    # 1. Equity Curve
    print("Plotting equity curve...")
    viz.plot_equity_curve(
        results['portfolio_history'],
        title='Equity Curve - In-Sample Backtest',
        save_path=f'{save_dir}/equity_curve.png'
    )

    # 2. Candlestick with signals - use only the trades data
    print("Plotting candlestick chart...")
    # Filter df to only have relevant columns
    plot_df = df[['datetime', 'open', 'high', 'low', 'close', 'sma', 'upper_band', 'lower_band', 'buy_signal']].copy()
    viz.plot_candlestick_with_signals(
        plot_df,
        results['trades'],
        title='Backtest Chart - Entry/Exit Signals',
        save_path=f'{save_dir}/backtest_chart.png'
    )

    # 3. Trade distribution
    print("Plotting trade distribution...")
    viz.plot_trade_distribution(
        results['trades'],
        title='Trade Profit/Loss Distribution',
        save_path=f'{save_dir}/trade_distribution.png'
    )

    # 4. Exit analysis
    print("Plotting exit analysis...")
    viz.plot_exit_analysis(
        results['trades'],
        title='Exit Reason Analysis',
        save_path=f'{save_dir}/exit_analysis.png'
    )

    print(f"\nAll charts saved to {save_dir}/")


if __name__ == "__main__":
    visualize_results()
