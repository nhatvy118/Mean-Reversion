# BBSmaReversion

## Abstract

This project implements a mean reversion trading strategy for VN30 Index Futures (VN30F1M) based on Bollinger Bands and SMA20. The strategy identifies oversold conditions when price touches or crosses below the lower Bollinger Band, expecting price to revert to its mean ( the short term.

SMA20) in## 1. Introduction

This project explores the application of mean reversion trading strategies to the VN30 Index Futures market (VN30F1M). Mean reversion strategies operate on the principle to revert to their that asset prices tend historical mean or average over time. When prices deviate significantly from this mean—reaching oversold conditions—they create potential trading opportunities as the market corrects itself.

The system is built with a modular architecture:
- Data loading and processing for VN30F1M futures
- Technical indicator calculation (SMA, Bollinger Bands)
- Signal generation based on band crossovers
- Backtesting engine with precise entry and exit execution
- Performance evaluation using standard financial metrics

## 2. Trading Hypotheses

### Hypothesis

When the price of an asset drops significantly below its moving average—specifically touching or crossing the Lower Bollinger Band—it is considered statistically 'oversold.' We expect the price to revert to its mean (the 20-period SMA) in the short term, particularly when the short-term moving average is relatively flat, indicating a non-trending market.

### Target Market

| Attribute | Value |
|-----------|-------|
| **Ticker** | VN30F1M (VN30 Index Futures) |
| **Timeframe** | 15-minute (configurable: 5min, 15min, 30min, 1h) |
| **Strategy Type** | Mean Reversion |
| **Trading Hours** | 09:15 - 14:45 |

### Entry Conditions

**Buy Signal (Long Position)**:
- Previous price was above the lower Bollinger Band: Pt-1 > LowerBand(t-1)
- Current price crosses to or below the lower band: Pt <= LowerBand(t)
- This indicates an oversold condition where price has dropped to or below the lower band

### Exit Conditions

| Exit Type | Condition |
|-----------|-----------|
| **Take-Profit** | Exit when price reaches or exceeds SMA20 (price has returned to the mean) |
| **Stop-Loss** | Exit when unrealized loss reaches -2 points |
| **Time-Based Exit** | No positions remain overnight; close at ATC session (14:45) |

### Order Execution

| Parameter | Value |
|-----------|-------|
| Position Size | 1 contract per trade |
| Entry Order | Limit Order at current price Pt |

## 3. Data

### 3.1 Data Collection

The system retrieves tick-by-tick data for VN30 Index Futures from a PostgreSQL database using the `DataLoader` class.

1. Queries active front-month contract data by joining:
   - `quote.matched` table: price and timestamp data
   - `quote.futurecontractcode` table: contract mapping information
   - `quote.total` table: volume data

2. Database configuration (config/database.json):
```json
{
  "host": "api.algotrade.vn",
  "port": 5432,
  "database": "algotradeDB",
  "user": "cs408_2026",
  "password": "xaHfeq-gesfof-hance2"
}
```

### 3.2 Data Processing

The `DataProcessor` class handles the transformation of raw tick data:
1. **OHLCV Generation**: Converts tick data to configurable timeframe candles
2. **Trading Hours Filtering**: Restricts data to regular trading hours (09:15-14:45)
3. **Technical Indicator Calculation**: Adds SMA and Bollinger Bands

| Indicator | Formula |
|-----------|---------|
| SMA (20) | Simple Moving Average of last 20 periods |
| Upper Band | SMA + (2.0 × Std Dev) |
| Lower Band | SMA - (2.0 × Std Dev) |

## 4. Implementation

### 4.1 Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd BBSmaReversion
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
# or
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Database is pre-configured (config/database.json already exists)

### 4.2 How to Run

#### Option 1: Run as Python Script

```bash
# Step 4: In-sample Backtesting
python src/run_backtest.py

# Step 5: Optimization
python src/run_optimization.py

# Step 6: Out-of-sample Backtesting
python src/run_outsample_backtest.py
```

#### Option 2: Run as Jupyter Notebook

```bash
jupyter notebook notebooks/run_backtest.ipynb
```

```bash
# Step 4: In-sample Backtesting only
python src/run_backtest.py

# Step 5: Optimization only
python src/run_optimization.py

# Step 6: Out-of-sample Backtesting only
python src/run_outsample_backtest.py
```

#### Using Jupyter Notebook
```bash
jupyter notebook notebooks/run_backtest.ipynb
```

### 4.3 Configuration

Strategy parameters are configured in `config/strategy_config.json`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| bb_window | 20 | Bollinger Bands window period |
| bb_std | 2.0 | Standard deviation multiplier |
| sma_window | 20 | SMA period |
| default_timeframe | 15min | Candle timeframe |
| stop_loss_points | 2 | Stop loss in points |
| max_positions_per_day | 1 | Maximum trades per day |

## 5. In-sample Backtesting (Step 4)

### 5.1 Parameters

| Parameter | Value |
|-----------|-------|
| Period | 2024-01-01 to 2024-06-30 |
| BB Window | 20 |
| BB Std | 1.8 |
| Timeframe | 15min |
| Stop-Loss | 2 points |

### 5.2 Results

> Results will be generated when running `python src/run_all_steps.py`

| Metric | Value |
|--------|-------|
| Total Trades | ≥30 (target) |
| Win Rate | TBD |
| Total Return | TBD |
| Sharpe Ratio | TBD |
| Max Drawdown | TBD |
| Profit Factor | TBD |

**Trade Distribution by Exit Reason:**
- Take-Profit: TBD
- Stop-Loss: TBD
- Market Close: TBD

Results saved to: `runs/insample/insample_results.json`

## 6. Optimization (Step 5)

### 6.1 Method

Grid search optimization over parameter space:

| Parameter | Range |
|-----------|-------|
| bb_window | [15, 20, 25] |
| bb_std | [1.5, 1.8, 2.0] |

**Objective Function:** Sharpe Ratio

### 6.2 Results

> Results will be generated when running `python src/run_all_steps.py`

**Optimization Results (sorted by Sharpe Ratio):**

| bb_window | bb_std | Total Trades | Sharpe Ratio | Return | Win Rate |
|-----------|--------|--------------|--------------|--------|----------|
| TBD | TBD | TBD | TBD | TBD | TBD |

**Best Parameters:**
```json
{
  "bb_window": TBD,
  "bb_std": TBD,
  "timeframe": "15min"
}
```

Results saved to:
- `runs/optimization/optimization_results.csv`
- `runs/optimization/best_params.json`

## 7. Out-of-sample Backtesting (Step 6)

### 7.1 Parameters

| Parameter | Value |
|-----------|-------|
| Period | 2024-07-01 to 2024-12-31 |
| BB Window | From optimization |
| BB Std | From optimization |
| Timeframe | 15min |

### 7.2 Results

> Results will be generated when running `python src/run_all_steps.py`

| Metric | Value |
|--------|-------|
| Total Trades | ≥30 (target) |
| Win Rate | TBD |
| Total Return | TBD |
| Sharpe Ratio | TBD |
| Max Drawdown | TBD |
| Profit Factor | TBD |

**Trade Distribution by Exit Reason:**
- Take-Profit: TBD
- Stop-Loss: TBD
- Market Close: TBD

Results saved to:
- `runs/outsample/outsample_trades.csv`
- `runs/outsample/outsample_results.json`

## 8. Conclusion

The BB SMA Reversion strategy provides a systematic approach to trading VN30F1M futures based on mean reversion principles. The strategy aims to capture profits when price reverts to its mean after reaching oversold conditions.

### Key Features:
- Clear entry signal based on Bollinger Bands crossover
- Fixed stop-loss of 2 points
- Take-profit at SMA20 (mean reversion target)
- No overnight positions

### Areas for Improvement:
- Parameter optimization with larger search space
- Market condition filters (volatility, trend)
- Adaptive position sizing
- Multiple timeframe analysis

## References

- [Bollinger Bands Definition](https://www.investopedia.com/terms/b/bollingerbands.asp)
- [Mean Reversion Strategy](https://www.investopedia.com/terms/m/meanreversion.asp)
- [PLUTUS Guidelines](https://github.com/algotrade-course/plutus-guideline/)
