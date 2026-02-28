import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

class BacktestEngine:
    """
    Backtest Engine for BB SMA Reversion Strategy

    Exit Conditions:
    - Take-Profit: Pt >= SMA20 (price has returned to the mean)
    - Stop-Loss: Unrealized profit <= -2 points
    - Time-Based Exit: No overnight positions (close at ATC session)
    """

    def __init__(self, initial_balance=100000, commission=0.001, stop_loss_points=2):
        self.initial_balance = float(initial_balance)
        self.commission = float(commission)
        self.stop_loss_points = stop_loss_points

    def run_backtest(self, signals_df):
        """
        Run backtest with the following exit rules:
        1. Take-Profit: Price reaches or exceeds SMA20
        2. Stop-Loss: Unrealized loss >= 2 points
        3. Time-Based Exit: Close position at market close (14:45)
        """
        signals_df = signals_df.copy()

        # Ensure numeric columns
        for col in ['open', 'high', 'low', 'close', 'sma', 'lower_band']:
            if col in signals_df.columns:
                signals_df[col] = signals_df[col].astype(float)

        if 'buy_signal' not in signals_df.columns:
            signals_df['buy_signal'] = 0
        if 'sell_signal' not in signals_df.columns:
            signals_df['sell_signal'] = 0

        df = signals_df.copy()

        portfolio_history = []
        current_balance = self.initial_balance
        portfolio_history.append(current_balance)

        df['position'] = 0
        df['entry_price'] = np.nan
        df['exit_price'] = np.nan
        df['profit'] = 0.0
        df['current_balance'] = current_balance

        # Position tracking
        current_position = 0  # 0 = no position, 1 = long
        entry_price = 0.0
        entry_time = None
        entry_sma = 0.0

        trades_list = []
        trade_id = 0

        daily_positions = 0
        current_date = None
        market_close_time = time(14, 45)

        for i in range(len(df)):
            row = df.iloc[i]

            row_date = row['datetime'].date()
            row_time = row['datetime'].time()

            # Reset daily position count
            if current_date is None or row_date != current_date:
                current_date = row_date
                daily_positions = 0

            # Entry Logic
            if current_position == 0:
                # Only enter long positions (Buy)
                # Check if within trading hours (before 14:30)
                if row['buy_signal'] == 1 and daily_positions < 1 and row_time < time(14, 30):
                    current_position = 1  # Long position
                    entry_price = float(row['close'])
                    entry_time = row['datetime']
                    entry_sma = float(row['sma'])
                    trade_id += 1
                    daily_positions += 1

                    df.at[i, 'position'] = 1
                    df.at[i, 'entry_price'] = entry_price

            # Exit Logic (when holding a position)
            elif current_position != 0:
                df.at[i, 'position'] = current_position

                exit_signal = False
                exit_reason = ""
                exit_price = float(row['close'])
                unrealized_profit = 0.0

                # Calculate unrealized profit for long position
                if current_position == 1:
                    unrealized_profit = exit_price - entry_price

                    # Exit Condition 1: Take-Profit (Price returned to SMA)
                    if exit_price >= entry_sma:
                        exit_signal = True
                        exit_reason = "take_profit"
                        exit_price = exit_price  # Use current close price

                    # Exit Condition 2: Stop-Loss (loss >= 2 points)
                    elif unrealized_profit <= -self.stop_loss_points:
                        exit_signal = True
                        exit_reason = "stop_loss"
                        exit_price = entry_price - self.stop_loss_points  # Close at stop loss price

                    # Exit Condition 3: Market Close (ATC)
                    elif row_time >= market_close_time:
                        exit_signal = True
                        exit_reason = "market_close"
                        exit_price = exit_price  # Close at current price

                # Process exit
                if exit_signal:
                    position_size = 1

                    # Calculate profit for long position
                    if current_position == 1:
                        profit = (exit_price - entry_price) * position_size
                    else:
                        profit = (entry_price - exit_price) * position_size

                    # Apply commission
                    commission_cost = abs(profit) * self.commission
                    net_profit = profit - commission_cost

                    current_balance += net_profit

                    df.at[i, 'exit_price'] = exit_price
                    df.at[i, 'profit'] = net_profit

                    trades_list.append({
                        'trade_id': trade_id,
                        'type': 'buy',
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'exit_time': row['datetime'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'position_size': position_size,
                        'profit': net_profit,
                        'sma_at_entry': entry_sma
                    })

                    current_position = 0

            df.at[i, 'current_balance'] = current_balance
            portfolio_history.append(current_balance)

        trades_df = pd.DataFrame(trades_list)

        backtest_results = {
            'trades': trades_df,
            'portfolio_history': portfolio_history,
            'final_balance': current_balance,
            'total_return': (current_balance - self.initial_balance) / self.initial_balance,
            'backtest_df': df
        }

        return backtest_results
