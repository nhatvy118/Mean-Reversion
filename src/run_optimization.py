import json
import os
import sys
import pandas as pd
import numpy as np
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.run_backtest import run_backtest
from src.backtest.performance import PerformanceAnalyzer


def run_optimization():
    """Step 5: Parameter Optimization

    Grid search over parameter space to find optimal parameters.
    """
    print("\n" + "="*60)
    print("STEP 5: OPTIMIZATION")
    print("="*60)

    # Define parameter ranges
    param_grid = {
        'bb_window': [10, 15, 20, 25],
        'bb_std': [1.5, 1.8, 2.0, 2.5],
    }

    # Generate all combinations
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = list(product(*values))

    print(f"Testing {len(combinations)} parameter combinations...")

    results = []
    best_sharpe = -np.inf
    best_params = None
    best_metrics = None

    for i, params in enumerate(combinations):
        bb_window, bb_std = params

        print(f"\n[{i+1}/{len(combinations)}] Testing: bb_window={bb_window}, bb_std={bb_std}")

        # Run backtest with these parameters
        try:
            backtest_results, metrics, _ = run_backtest(
                start_date='2024-01-01',
                end_date='2024-06-30',
                bb_window=bb_window,
                bb_std=bb_std,
                timeframe='15min',
                use_enhanced_signal=False
            )

            num_trades = len(backtest_results['trades'])

            results.append({
                'bb_window': bb_window,
                'bb_std': bb_std,
                'total_trades': num_trades,
                'total_return': metrics['total_return'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'max_drawdown': metrics['max_drawdown'],
            })

            # Track best by Sharpe Ratio
            if metrics['sharpe_ratio'] > best_sharpe and num_trades >= 30:
                best_sharpe = metrics['sharpe_ratio']
                best_params = params
                best_metrics = metrics

            print(f"  Trades: {num_trades}, Sharpe: {metrics['sharpe_ratio']:.2f}, Return: {metrics['total_return']:.2%}")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Save results to DataFrame
    results_df = pd.DataFrame(results)

    # Sort by Sharpe Ratio
    results_df = results_df.sort_values('sharpe_ratio', ascending=False)

    print("\n" + "="*60)
    print("OPTIMIZATION RESULTS")
    print("="*60)
    print(results_df.to_string(index=False))

    # Save to CSV
    output_dir = 'runs/optimization'
    os.makedirs(output_dir, exist_ok=True)
    results_df.to_csv(f'{output_dir}/optimization_results.csv', index=False)

    # Print best parameters
    print("\n" + "="*60)
    print("BEST PARAMETERS (with >= 30 trades)")
    print("="*60)

    # Filter for >= 30 trades
    valid_results = results_df[results_df['total_trades'] >= 30]
    if len(valid_results) > 0:
        best = valid_results.iloc[0]
        print(f"bb_window: {int(best['bb_window'])}")
        print(f"bb_std: {best['bb_std']}")
        print(f"Total Trades: {int(best['total_trades'])}")
        print(f"Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        print(f"Total Return: {best['total_return']:.2%}")
        print(f"Win Rate: {best['win_rate']:.2%}")
        print(f"Max Drawdown: {best['max_drawdown']:.2%}")

        # Save best params
        best_params_dict = {
            'bb_window': int(best['bb_window']),
            'bb_std': float(best['bb_std']),
            'timeframe': '15min',
            'total_trades': int(best['total_trades']),
            'sharpe_ratio': float(best['sharpe_ratio']),
            'total_return': float(best['total_return']),
            'win_rate': float(best['win_rate']),
            'max_drawdown': float(best['max_drawdown'])
        }

        with open(f'{output_dir}/best_params.json', 'w') as f:
            json.dump(best_params_dict, f, indent=2)

        print(f"\nBest parameters saved to {output_dir}/best_params.json")
    else:
        print("No parameter combination achieved >= 30 trades")

    return results_df, best_params


if __name__ == "__main__":
    results_df, best_params = run_optimization()
