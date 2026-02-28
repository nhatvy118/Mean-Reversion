import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import mplfinance as mpf
import os


class BacktestVisualizer:
    """Visualize backtest results"""

    def __init__(self, save_dir='readme_results'):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def plot_equity_curve(self, portfolio_history, title='Equity Curve', save_path=None):
        """Plot equity curve"""
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(portfolio_history, linewidth=2, color='blue')
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Portfolio Value')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def plot_candlestick_with_signals(self, df, trades_df, title='Backtest Chart', save_path=None):
        """Plot candlestick chart with entry/exit signals"""
        if df.empty:
            print("No data to plot")
            return

        # Prepare data for mplfinance
        plot_df = df.set_index('datetime')
        plot_df.index = pd.DatetimeIndex(plot_df.index)

        # Create signals
        buy_signals = df[df['buy_signal'] == 1].copy()
        sell_signals = df[df['sell_signal'] == 1].copy()

        # Create panels
        fig, axes = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})

        # Price chart
        ax1 = axes[0]
        ax1.plot(plot_df.index, plot_df['sma'], label='SMA20', color='orange', linewidth=1)
        ax1.plot(plot_df.index, plot_df['upper_band'], label='Upper BB', color='red', linestyle='--', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['lower_band'], label='Lower BB', color='green', linestyle='--', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['close'], label='Close', color='blue', linewidth=0.8, alpha=0.7)

        # Mark entry points
        if not trades_df.empty:
            entry_times = pd.to_datetime(trades_df['entry_time'])
            entry_prices = trades_df['entry_price']
            ax1.scatter(entry_times, entry_prices, marker='^', color='green', s=100, label='Entry', zorder=5)

            exit_times = pd.to_datetime(trades_df['exit_time'])
            exit_prices = trades_df['exit_price']
            ax1.scatter(exit_times, exit_prices, marker='v', color='red', s=100, label='Exit', zorder=5)

        ax1.set_ylabel('Price')
        ax1.set_title(title)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Position chart
        ax2 = axes[1]
        ax2.fill_between(plot_df.index, 0, plot_df['position'], alpha=0.5, color='blue', label='Position')
        ax2.set_ylabel('Position')
        ax2.set_xlabel('Date')
        ax2.set_ylim(-0.5, 1.5)
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(['No Position', 'Long'])
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def plot_trade_distribution(self, trades_df, title='Trade Distribution', save_path=None):
        """Plot profit/loss distribution"""
        if trades_df.empty:
            print("No trades to plot")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        profits = trades_df['profit'].values
        colors = ['green' if p > 0 else 'red' for p in profits]

        ax.bar(range(len(profits)), profits, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xlabel('Trade Number')
        ax.set_ylabel('Profit/Loss')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def plot_exit_analysis(self, trades_df, title='Exit Analysis', save_path=None):
        """Plot exit reason distribution"""
        if trades_df.empty:
            print("No trades to plot")
            return

        exit_reasons = trades_df['exit_reason'].value_counts()

        fig, ax = plt.subplots(figsize=(8, 6))

        colors = ['green', 'red', 'blue', 'orange']
        ax.pie(exit_reasons.values, labels=exit_reasons.index, autopct='%1.1f%%',
               colors=colors[:len(exit_reasons)], startangle=90)
        ax.set_title(title)

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def plot_metrics_comparison(self, default_metrics, optimized_metrics, save_path=None):
        """Plot comparison between default and optimized parameters"""
        metrics_names = ['Win Rate', 'Profit Factor', 'Sharpe Ratio', 'Max Drawdown', 'Total Return']
        default_values = [
            default_metrics['win_rate'],
            default_metrics['profit_factor'],
            default_metrics['sharpe_ratio'],
            abs(default_metrics['max_drawdown']),
            default_metrics['total_return']
        ]
        optimized_values = [
            optimized_metrics['win_rate'],
            optimized_metrics['profit_factor'],
            optimized_metrics['sharpe_ratio'],
            abs(optimized_metrics['max_drawdown']),
            optimized_metrics['total_return']
        ]

        x = np.arange(len(metrics_names))
        width = 0.35

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(x - width/2, default_values, width, label='Default', alpha=0.8)
        ax.bar(x + width/2, optimized_values, width, label='Optimized', alpha=0.8)

        ax.set_xlabel('Metric')
        ax.set_ylabel('Value')
        ax.set_title('Performance Metrics Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
