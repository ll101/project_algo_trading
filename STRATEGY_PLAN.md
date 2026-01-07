# Trend Following Trading Strategy Implementation Plan

## Overview
This document outlines the plan for implementing trend-following trading strategies with experimentation, optimization, and comparison capabilities.

## Current Architecture Analysis

### Design Decision: Separation of Strategy Classes and Backtesting Scripts

**Current Structure:**
- `src/strategy/` - Strategy class definitions (e.g., `strategies.py`)
- `src/backtest/` - Backtesting scripts (e.g., `trend_following_1.py`)
- `src/data/` - Data ingestion from TimescaleDB

### Assessment of Current Design

**Strengths:**
1. **Separation of Concerns**: Strategy logic is separated from execution/testing logic
2. **Reusability**: Strategy classes can be used in multiple backtesting scenarios
3. **Testability**: Strategies can be unit tested independently
4. **Modularity**: Easy to add new strategies without modifying backtesting infrastructure

**Weaknesses & Improvements Needed:**
1. **Data Access Layer Missing**: No abstraction for fetching data from TimescaleDB
2. **Strategy Base Class**: No common interface/base class for strategies
3. **Configuration Management**: No standardized way to pass parameters
4. **Results Storage**: No mechanism to store backtest results for comparison
5. **Indicator Management**: No centralized indicator calculation/management
6. **Optimization Framework**: No standardized optimization workflow

## Recommended Architecture

### Proposed File Structure

```
src/
├── data/                    # Existing - Data ingestion
│   ├── db_connection.py
│   ├── db_ingestion.py
│   └── alpaca_ingestion.py
│
├── strategy/                # Strategy definitions
│   ├── __init__.py
│   ├── base.py              # Base strategy class
│   ├── indicators.py        # Indicator utilities (wrapper around talib)
│   ├── trend_following/     # Trend following strategies
│   │   ├── __init__.py
│   │   ├── moving_average_crossover.py
│   │   ├── macd_strategy.py
│   │   ├── bollinger_bands.py
│   │   ├── adx_strategy.py
│   │   └── dual_moving_average.py
│   └── utils.py             # Strategy utilities
│
├── backtest/                # Backtesting infrastructure
│   ├── __init__.py
│   ├── data_loader.py       # Load data from TimescaleDB
│   ├── backtest_engine.py   # Wrapper around backtesting library
│   ├── optimizer.py         # Optimization framework
│   ├── results.py           # Results storage and comparison
│   ├── scripts/             # Individual backtest scripts
│   │   ├── run_trend_following.py
│   │   └── compare_strategies.py
│   └── reports/             # Generated reports/plots
│
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── config.py            # Configuration management
    └── logging_config.py    # Logging setup
```

## Implementation Plan

### Phase 1: Foundation Layer

#### 1.1 Data Access Layer (`src/backtest/data_loader.py`)
**Purpose**: Abstract data fetching from TimescaleDB

**Key Functions:**
- `load_bars_from_db(symbol, start_date, end_date, timeframe)` → Returns DataFrame
- `load_multiple_symbols(symbols, start_date, end_date)` → Returns dict of DataFrames
- `get_available_symbols()` → Returns list of symbols in database
- `validate_data_quality(df)` → Checks for gaps, missing data

**Design Considerations:**
- Use pandas DataFrames for compatibility with backtesting library
- Handle timezone conversions (UTC from DB to local if needed)
- Cache frequently accessed data
- Support different timeframes (minute, hour, day)

#### 1.2 Base Strategy Class (`src/strategy/base.py`)
**Purpose**: Common interface for all strategies

**Key Components:**
```python
class BaseStrategy(Strategy):
    # Common parameters
    # Common indicator initialization
    # Common utility methods
    # Standardized signal generation
```

**Benefits:**
- Consistent interface for all strategies
- Shared functionality (position sizing, risk management)
- Easier to add new strategies
- Standardized parameter handling

#### 1.3 Indicator Utilities (`src/strategy/indicators.py`)
**Purpose**: Wrapper around talib for consistent indicator calculation

**Key Functions:**
- `calculate_rsi(data, period)` → RSI indicator
- `calculate_macd(data, fast, slow, signal)` → MACD indicator
- `calculate_bollinger_bands(data, period, std_dev)` → Bollinger Bands
- `calculate_adx(data, period)` → ADX (trend strength)
- `calculate_ema(data, period)` → Exponential Moving Average
- `calculate_sma(data, period)` → Simple Moving Average
- `calculate_atr(data, period)` → Average True Range (for stops)

**Benefits:**
- Consistent API across all strategies
- Error handling for edge cases
- Caching of expensive calculations
- Validation of input data

### Phase 2: Trend Following Strategies

#### 2.1 Moving Average Crossover Strategy
**Indicators**: Fast SMA, Slow SMA
**Logic**: 
- Buy when fast MA crosses above slow MA (golden cross)
- Sell when fast MA crosses below slow MA (death cross)

**Parameters to Optimize:**
- Fast MA period (5-50)
- Slow MA period (20-200)
- Stop loss percentage
- Take profit percentage

#### 2.2 MACD Strategy
**Indicators**: MACD line, Signal line, Histogram
**Logic**:
- Buy when MACD crosses above signal line
- Sell when MACD crosses below signal line
- Optional: Filter by histogram strength

**Parameters to Optimize:**
- Fast period (8-20)
- Slow period (20-50)
- Signal period (5-15)
- Histogram threshold

#### 2.3 Bollinger Bands Strategy
**Indicators**: Upper band, Lower band, Middle band (SMA)
**Logic**:
- Buy when price touches lower band (oversold)
- Sell when price touches upper band (overbought)
- Optional: Trend filter (only trade in direction of trend)

**Parameters to Optimize:**
- Period (10-30)
- Standard deviation multiplier (1.5-3.0)
- Trend filter period

#### 2.4 ADX Trend Following Strategy
**Indicators**: ADX (trend strength), +DI, -DI
**Logic**:
- Buy when ADX > threshold AND +DI > -DI (strong uptrend)
- Sell when ADX > threshold AND -DI > +DI (strong downtrend)

**Parameters to Optimize:**
- ADX period (10-30)
- ADX threshold (20-40)
- DI period

#### 2.5 Dual Moving Average with Trend Filter
**Indicators**: Fast EMA, Slow EMA, Long-term SMA (trend filter)
**Logic**:
- Only trade when price is above/below long-term SMA
- Use fast/slow EMA for entry/exit signals

**Parameters to Optimize:**
- Fast EMA period
- Slow EMA period
- Trend filter period (50-200)

### Phase 3: Backtesting Infrastructure

#### 3.1 Backtest Engine Wrapper (`src/backtest/backtest_engine.py`)
**Purpose**: Standardize backtesting execution

**Key Functions:**
- `run_backtest(strategy_class, data, cash, commission, **params)` → Returns results
- `run_optimization(strategy_class, data, param_ranges, maximize_metric)` → Returns optimization results
- `compare_strategies(strategies, data, metrics)` → Returns comparison DataFrame

**Features:**
- Standardized commission and slippage models
- Consistent cash management
- Result formatting and validation

#### 3.2 Optimizer Framework (`src/backtest/optimizer.py`)
**Purpose**: Systematic parameter optimization

**Key Functions:**
- `grid_search(strategy, data, param_grid)` → Grid search optimization
- `random_search(strategy, data, param_distributions, n_iter)` → Random search
- `bayesian_optimization(strategy, data, param_bounds)` → Bayesian optimization (optional)

**Optimization Metrics:**
- Sharpe Ratio
- Sortino Ratio
- Return/Max Drawdown ratio
- Total Return
- Win Rate
- Profit Factor

**Features:**
- Parallel execution for faster optimization
- Early stopping for unpromising parameter sets
- Result caching to avoid re-computation

#### 3.3 Results Management (`src/backtest/results.py`)
**Purpose**: Store, compare, and analyze backtest results

**Key Components:**
- `BacktestResult` class: Stores single backtest result
- `ResultsDatabase`: Store results in database or file
- `ResultsComparator`: Compare multiple strategy results
- `ResultsVisualizer`: Generate charts and reports

**Storage Options:**
1. **Database Table**: Store in TimescaleDB for historical tracking
2. **JSON Files**: For quick access and version control
3. **CSV Export**: For analysis in external tools

**Comparison Metrics:**
- Side-by-side performance metrics
- Equity curves overlay
- Drawdown comparison
- Trade analysis comparison

### Phase 4: Experimentation Framework

#### 4.1 Configuration Management (`src/utils/config.py`)
**Purpose**: Centralized configuration for experiments

**Configuration Structure:**
```python
{
    "experiment_name": "trend_following_v1",
    "date_range": {
        "start": "2025-07-01",
        "end": "2025-12-31"
    },
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "strategies": [
        {
            "name": "MACross",
            "class": "MovingAverageCrossover",
            "params": {...},
            "optimize": True,
            "param_ranges": {...}
        }
    ],
    "backtest_settings": {
        "cash": 100000,
        "commission": 0.001,
        "slippage": 0.0005
    }
}
```

#### 4.2 Experiment Runner (`src/backtest/experiment_runner.py`)
**Purpose**: Execute and manage multiple experiments

**Features:**
- Load configuration from file
- Run multiple strategies in parallel
- Track experiment metadata (date, version, git commit)
- Generate experiment reports
- Compare experiment results

### Phase 5: Integration with TimescaleDB

#### 5.1 Data Loading from Database
**Implementation:**
```python
# In data_loader.py
def load_bars_from_db(symbol, start_date, end_date):
    query = """
        SELECT time, open, high, low, close, volume
        FROM trading.bars b
        JOIN trading.stock s ON b.stock_id = s.id
        WHERE s.symbol = %s
        AND b.time BETWEEN %s AND %s
        ORDER BY b.time
    """
    # Execute query, return DataFrame in backtesting library format
```

**Data Format:**
- Must match backtesting library's expected format
- Columns: Open, High, Low, Close, Volume
- Index: DatetimeIndex
- Timezone-aware timestamps

#### 5.2 Results Storage in Database
**Optional Table Structure:**
```sql
CREATE TABLE trading.backtest_results (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(100),
    strategy_name VARCHAR(100),
    symbol VARCHAR(20),
    start_date DATE,
    end_date DATE,
    parameters JSONB,
    metrics JSONB,  -- Sharpe, Return, Drawdown, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Design Improvements

### 1. Add Strategy Base Class
**Current**: Each strategy is independent
**Improved**: All strategies inherit from `BaseStrategy`

**Benefits:**
- Consistent interface
- Shared functionality (risk management, position sizing)
- Easier to add new strategies
- Standardized parameter validation

### 2. Data Access Abstraction
**Current**: Direct database queries in backtest scripts
**Improved**: `DataLoader` class abstracts data access

**Benefits:**
- Reusable data loading logic
- Consistent data format
- Easy to switch data sources (DB, CSV, API)
- Data quality validation

### 3. Configuration-Driven Experiments
**Current**: Hard-coded parameters in scripts
**Improved**: YAML/JSON configuration files

**Benefits:**
- Reproducible experiments
- Version control for configurations
- Easy parameter tweaking
- Batch experiment execution

### 4. Results Persistence
**Current**: Results only in memory/console
**Improved**: Store results in database or files

**Benefits:**
- Historical comparison
- Track strategy performance over time
- Reproducible analysis
- Share results with team

### 5. Indicator Management
**Current**: Direct talib calls in strategies
**Improved**: Centralized indicator utilities

**Benefits:**
- Consistent indicator calculation
- Error handling
- Performance optimization (caching)
- Easy to add custom indicators

### 6. Optimization Framework
**Current**: Manual optimization in scripts
**Improved**: Standardized optimization framework

**Benefits:**
- Consistent optimization methodology
- Parallel execution
- Result comparison
- Automated parameter selection

## Trend Following Strategy Implementation Details

### Common Trend Following Indicators

1. **Moving Averages** (SMA, EMA)
   - Identify trend direction
   - Crossover signals
   - Support/resistance levels

2. **MACD** (Moving Average Convergence Divergence)
   - Trend momentum
   - Crossover signals
   - Divergence detection

3. **ADX** (Average Directional Index)
   - Trend strength (not direction)
   - Filter weak trends
   - Combine with directional indicators

4. **Bollinger Bands**
   - Volatility-based entries
   - Mean reversion within trend
   - Breakout detection

5. **ATR** (Average True Range)
   - Dynamic stop loss placement
   - Position sizing based on volatility
   - Risk management

### Strategy Template Structure

```python
class TrendFollowingStrategy(BaseStrategy):
    # Parameters (optimizable)
    fast_period = 20
    slow_period = 50
    stop_loss_pct = 0.02
    
    def init(self):
        # Calculate indicators
        self.fast_ma = self.I(talib.EMA, self.data.Close, self.fast_period)
        self.slow_ma = self.I(talib.EMA, self.data.Close, self.slow_period)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, 
                         self.data.Close, 14)
    
    def next(self):
        # Entry logic
        if crossover(self.fast_ma, self.slow_ma):
            self.buy()
        
        # Exit logic
        if crossover(self.slow_ma, self.fast_ma):
            self.position.close()
        
        # Risk management
        if self.position:
            # Dynamic stop loss based on ATR
            stop_price = self.position.entry_price * (1 - self.stop_loss_pct)
            if self.data.Close[-1] < stop_price:
                self.position.close()
```

## Optimization Strategy

### Parameter Ranges for Trend Following

**Moving Average Crossover:**
- Fast period: 5-50 (step: 5)
- Slow period: 20-200 (step: 10)
- Stop loss: 0.01-0.05 (step: 0.01)

**MACD:**
- Fast period: 8-20 (step: 2)
- Slow period: 20-50 (step: 5)
- Signal period: 5-15 (step: 2)

**Bollinger Bands:**
- Period: 10-30 (step: 5)
- Std dev: 1.5-3.0 (step: 0.25)

### Optimization Workflow

1. **Define Parameter Space**: Set ranges for each parameter
2. **Select Optimization Method**: Grid search, random search, or Bayesian
3. **Choose Objective Function**: Sharpe ratio, Return/Drawdown, etc.
4. **Run Optimization**: Execute with parallel processing
5. **Analyze Results**: Identify best parameters and sensitivity
6. **Validate**: Test on out-of-sample data
7. **Store Results**: Save for future comparison

## Comparison Framework

### Metrics to Compare

1. **Performance Metrics:**
   - Total Return (%)
   - Annualized Return (%)
   - Sharpe Ratio
   - Sortino Ratio
   - Calmar Ratio (Return/Max Drawdown)

2. **Risk Metrics:**
   - Maximum Drawdown (%)
   - Volatility (%)
   - Value at Risk (VaR)
   - Expected Shortfall

3. **Trade Statistics:**
   - Total Trades
   - Win Rate (%)
   - Average Win/Loss
   - Profit Factor
   - Average Trade Duration

4. **Visual Comparisons:**
   - Equity curves
   - Drawdown charts
   - Trade distribution
   - Monthly returns heatmap

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create base strategy class
- [ ] Implement data loader from TimescaleDB
- [ ] Create indicator utilities wrapper
- [ ] Set up configuration management

### Phase 2: Core Strategies (Week 2)
- [ ] Moving Average Crossover
- [ ] MACD Strategy
- [ ] Bollinger Bands Strategy
- [ ] ADX Strategy

### Phase 3: Backtesting Infrastructure (Week 3)
- [ ] Backtest engine wrapper
- [ ] Optimizer framework
- [ ] Results storage and comparison
- [ ] Visualization utilities

### Phase 4: Experimentation (Week 4)
- [ ] Experiment runner
- [ ] Configuration system
- [ ] Batch execution
- [ ] Results analysis tools

### Phase 5: Testing & Refinement (Week 5)
- [ ] Unit tests for strategies
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Documentation

## Recommended Improvements

### 1. Strategy Factory Pattern
Create a factory to instantiate strategies from configuration:
```python
strategy = StrategyFactory.create("MACross", params={...})
```

### 2. Parameter Validation
Add validation for strategy parameters:
- Range checks
- Type validation
- Dependency validation (e.g., fast_period < slow_period)

### 3. Walk-Forward Analysis
Implement walk-forward optimization:
- Train on historical data
- Test on forward data
- Rolling window optimization

### 4. Portfolio-Level Backtesting
Extend to test multiple symbols simultaneously:
- Portfolio-level risk management
- Correlation analysis
- Diversification benefits

### 5. Real-Time Integration
Prepare for live trading:
- Signal generation from strategies
- Order execution interface
- Performance monitoring

## Conclusion

The current separation of strategy classes and backtesting scripts is **sound** and follows good software engineering principles. The main improvements needed are:

1. **Abstraction layers** for data access and strategy execution
2. **Standardization** through base classes and utilities
3. **Experimentation framework** for systematic testing
4. **Results management** for comparison and analysis
5. **Integration** with TimescaleDB for data loading and result storage

This architecture will enable efficient experimentation, optimization, and comparison of trend-following strategies while maintaining code quality and reusability.

