import pandas as pd
import numpy as np


class PerformanceAnalyzer:
    """Calculate performance metrics for backtest results"""

    def __init__(self, risk_free_rate=0.03):
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(self, trades_df, portfolio_history, initial_balance):
        """Calculate comprehensive performance metrics"""
        if trades_df.empty or len(trades_df) == 0:
            return self._empty_metrics()

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['profit'] > 0]
        losing_trades = trades_df[trades_df['profit'] <= 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        # Profit metrics
        total_profit = trades_df['profit'].sum()
        total_return = total_profit / initial_balance

        # Average win/loss
        avg_win = winning_trades['profit'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['profit'].mean() if len(losing_trades) > 0 else 0

        # Profit Factor
        gross_profit = winning_trades['profit'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['profit'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if total_trades > 0 else 0

        # Drawdown calculation
        portfolio_series = pd.Series(portfolio_history)
        running_max = portfolio_series.cummax()
        drawdown = (portfolio_series - running_max) / running_max
        max_drawdown = drawdown.min()

        # Sharpe Ratio (simplified)
        if len(trades_df) > 1:
            returns = trades_df['profit'] / initial_balance
            sharpe_ratio = (returns.mean() - self.risk_free_rate / 252) / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
        else:
            sharpe_ratio = 0

        # Trade analysis
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict()

        metrics = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'exit_reasons': exit_reasons,
            'final_balance': portfolio_history[-1],
            'initial_balance': initial_balance
        }

        return metrics

    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'expectancy': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'exit_reasons': {},
            'final_balance': 0,
            'initial_balance': 0
        }

    def print_metrics(self, metrics):
        """Print metrics in a readable format"""
        print("\n" + "=" * 50)
        print("BACKTEST PERFORMANCE METRICS")
        print("=" * 50)
        print(f"Total Trades:        {metrics['total_trades']}")
        print(f"Winning Trades:      {metrics['winning_trades']}")
        print(f"Losing Trades:       {metrics['losing_trades']}")
        print(f"Win Rate:            {metrics['win_rate']:.2%}")
        print(f"Total Profit:        {metrics['total_profit']:.2f}")
        print(f"Total Return:        {metrics['total_return']:.2%}")
        print(f"Average Win:         {metrics['avg_win']:.2f}")
        print(f"Average Loss:        {metrics['avg_loss']:.2f}")
        print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
        print(f"Expectancy:          {metrics['expectancy']:.2f}")
        print(f"Max Drawdown:        {metrics['max_drawdown']:.2%}")
        print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
        print(f"Final Balance:       {metrics['final_balance']:.2f}")
        print("-" * 50)
        print("Exit Reasons:")
        for reason, count in metrics['exit_reasons'].items():
            print(f"  {reason}: {count}")
        print("=" * 50 + "\n")
