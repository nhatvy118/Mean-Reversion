import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.run_backtest import run_backtest
from src.backtest.performance import PerformanceAnalyzer


def run_outsample_backtest(best_params=None):
    """Step 6: Out-of-sample Backtesting

    Test the optimized parameters on unseen data.

    Args:
        best_params: Dictionary with optimized parameters

    Returns:
        results: Backtest results
        metrics: Performance metrics
    """
    print("\n" + "="*60)
    print("STEP 6: OUT-OF-SAMPLE BACKTESTING")
    print("="*60)

    # Load best parameters if not provided
    if best_params is None:
        params_path = 'runs/optimization/best_params.json'
        if os.path.exists(params_path):
            with open(params_path, 'r') as f:
                best_params = json.load(f)
            print(f"Loaded best parameters from {params_path}")
        else:
            # Use default parameters
            best_params = {
                'bb_window': 20,
                'bb_std': 2.0,
                'timeframe': '5min'
            }
            print("Using default parameters (no optimization results found)")

    # Out-of-sample period: 2024-07-01 to 2024-12-31
    # This is AFTER the in-sample period (2024-01-01 to 2024-06-30)
    print(f"\nOut-of-sample period: 2024-07-01 to 2024-12-31")
    print(f"Parameters: bb_window={best_params['bb_window']}, bb_std={best_params['bb_std']}")

    results, metrics, df = run_backtest(
        start_date='2024-07-01',
        end_date='2024-12-31',
        bb_window=best_params['bb_window'],
        bb_std=best_params['bb_std'],
        timeframe=best_params.get('timeframe', '5min'),
        use_enhanced_signal=True
    )

    total_trades = len(results['trades'])
    print(f"\nTotal out-of-sample trades: {total_trades}")
    if total_trades < 30:
        print("WARNING: Out-of-sample trades less than 30. Consider adjusting parameters (bb_std, timeframe, enhanced signals).")

    # Print performance metrics
    performance = PerformanceAnalyzer()
    performance.print_metrics(metrics)

    # Save results
    output_dir = 'runs/outsample'
    os.makedirs(output_dir, exist_ok=True)

    if not results['trades'].empty:
        results['trades'].to_csv(f'{output_dir}/outsample_trades.csv', index=False)

    # Save metrics
    metrics_output = {
        'period': {
            'start': '2024-07-01',
            'end': '2024-12-31'
        },
        'parameters': best_params,
        'metrics': {
            'total_trades': metrics['total_trades'],
            'winning_trades': metrics['winning_trades'],
            'losing_trades': metrics['losing_trades'],
            'win_rate': metrics['win_rate'],
            'total_profit': metrics['total_profit'],
            'total_return': metrics['total_return'],
            'avg_win': metrics['avg_win'],
            'avg_loss': metrics['avg_loss'],
            'profit_factor': metrics['profit_factor'],
            'expectancy': metrics['expectancy'],
            'max_drawdown': metrics['max_drawdown'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'final_balance': metrics['final_balance']
        },
        'exit_reasons': metrics['exit_reasons']
    }

    with open(f'{output_dir}/outsample_results.json', 'w') as f:
        json.dump(metrics_output, f, indent=2)

    print(f"\nResults saved to {output_dir}/")

    return results, metrics


def main():
    """Main function to run out-of-sample backtest"""
    results, metrics = run_outsample_backtest()

    # Print trade summary
    print("\nOut-of-sample Trade Summary:")
    if not results['trades'].empty:
        print(results['trades'].to_string())

    return results, metrics


if __name__ == "__main__":
    main()
