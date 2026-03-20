"""
analytics/backtest.py — QCEX Backtesting Engine
================================================
Multi-strategy backtesting framework for commodity prices.

Strategies implemented:
  1. Trend Following   — EMA crossover (fast/slow)
  2. Mean Reversion    — Bollinger Bands (buy oversold, sell overbought)
  3. Weather-Driven    — ENSO proxy for cocoa, HDD anomaly for gas
  4. Momentum          — 1M vs 3M return ranking (cross-asset)
  5. Combined Optimal  — Equal-weight ensemble of all signals

Metrics: Sharpe Ratio, Max Drawdown, Win Rate, Total PnL, Calmar Ratio
"""
from __future__ import annotations
from typing import Optional, Dict, Tuple
import numpy as np
import pandas as pd


# ── Signal generators ─────────────────────────────────────────────────────────

def signal_trend(prices: pd.Series,
                 fast: int = 20,
                 slow: int = 60) -> pd.Series:
    """
    EMA crossover trend-following signal.
    +1 = long (fast EMA > slow EMA)
    -1 = short (fast EMA < slow EMA)
     0 = no position
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    raw = np.where(ema_fast > ema_slow, 1.0, -1.0)
    sig = pd.Series(raw, index=prices.index)
    return sig.shift(1).fillna(0)  # avoid look-ahead bias


def signal_mean_reversion(prices: pd.Series,
                           window: int = 20,
                           n_std: float = 1.5) -> pd.Series:
    """
    Bollinger Band mean-reversion signal.
    +1 = long  (price below lower band — oversold)
    -1 = short (price above upper band — overbought)
     0 = neutral (inside bands)
    """
    ma  = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = ma + n_std * std
    lower = ma - n_std * std
    sig = pd.Series(0.0, index=prices.index)
    sig[prices < lower] =  1.0
    sig[prices > upper] = -1.0
    return sig.shift(1).fillna(0)


def signal_momentum(prices: pd.Series,
                    lookback: int = 21) -> pd.Series:
    """
    Simple price momentum signal.
    +1 if return over lookback > 0 (upward momentum)
    -1 if return over lookback < 0 (downward momentum)
    """
    ret = prices.pct_change(lookback)
    sig = np.sign(ret)
    return sig.shift(1).fillna(0)


def signal_weather(prices: pd.Series,
                   commodity: str) -> pd.Series:
    """
    Weather-based signal using seasonal patterns.
    - Cocoa: long in months following dry season (ENSO proxy)
    - Gas:   long in winter months (high HDD season)
    - Other: flat (no weather driver)
    """
    sig = pd.Series(0.0, index=prices.index)
    months = pd.Series(prices.index.month, index=prices.index)

    if commodity == "cocoa":
        # Go long in Apr-Jun (post dry season, supply uncertainty)
        # Go short in Oct-Dec (main harvest, supply peak)
        sig[months.isin([4, 5, 6])]  =  1.0
        sig[months.isin([10, 11, 12])] = -1.0
    elif commodity == "gas":
        # Go long Oct-Feb (winter heating season)
        # Go short Apr-Aug (injection season, low demand)
        sig[months.isin([10, 11, 12, 1, 2])] =  1.0
        sig[months.isin([4, 5, 6, 7, 8])]    = -1.0
    # uranium: no seasonal pattern

    return sig.shift(1).fillna(0)


def signal_volatility_breakout(prices: pd.Series,
                                window: int = 20,
                                threshold: float = 1.5) -> pd.Series:
    """
    ATR-based volatility breakout.
    Long when price breaks out above recent high by > threshold * ATR.
    """
    high = prices.rolling(window).max()
    atr  = prices.pct_change().abs().rolling(window).mean() * prices
    sig  = pd.Series(0.0, index=prices.index)
    sig[prices > high.shift(1) + threshold * atr.shift(1)] =  1.0
    sig[prices < prices.rolling(window).min().shift(1)]    = -1.0
    return sig.shift(1).fillna(0)


# ── Portfolio construction ────────────────────────────────────────────────────

def combine_signals(*signals: pd.Series,
                    weights: Optional[list] = None) -> pd.Series:
    """
    Combine multiple signals into one composite signal.
    Default: equal weighting, output in [-1, +1].
    """
    df = pd.concat(signals, axis=1).fillna(0)
    if weights is None:
        weights = [1.0 / len(signals)] * len(signals)
    w = np.array(weights)
    composite = df.values @ w
    # Clip to [-1, 1]
    return pd.Series(np.clip(composite, -1, 1), index=df.index)


# ── Backtest engine ───────────────────────────────────────────────────────────

def run_backtest(prices: pd.Series,
                 signal: pd.Series,
                 transaction_cost: float = 0.001,
                 initial_capital: float = 100_000.0) -> pd.DataFrame:
    """
    Run a backtest given a price series and a position signal.

    Parameters
    ----------
    prices           : daily close prices
    signal           : position signal in [-1, +1], already shifted (no look-ahead)
    transaction_cost : one-way cost as fraction of price (default 0.1%)
    initial_capital  : starting capital in USD

    Returns
    -------
    DataFrame with columns:
        price, signal, returns, strategy_returns, gross_pnl,
        cumulative_pnl, drawdown, position_change
    """
    prices = prices.dropna()
    signal = signal.reindex(prices.index).fillna(0)

    # Daily log returns of the asset
    asset_ret = np.log(prices / prices.shift(1)).fillna(0)

    # Position changes → transaction costs
    pos_change  = signal.diff().abs().fillna(0)
    tc_cost     = pos_change * transaction_cost

    # Strategy daily return
    strat_ret   = signal.shift(1).fillna(0) * asset_ret - tc_cost

    # Cumulative P&L
    cum_ret     = strat_ret.cumsum()
    cum_pnl     = initial_capital * (np.exp(cum_ret) - 1)

    # Drawdown
    running_max = cum_pnl.cummax()
    drawdown    = (cum_pnl - running_max) / (initial_capital + running_max.abs()) * 100

    df = pd.DataFrame({
        "price"          : prices,
        "signal"         : signal,
        "asset_ret"      : asset_ret,
        "strategy_ret"   : strat_ret,
        "cum_pnl"        : cum_pnl,
        "drawdown"       : drawdown,
        "pos_change"     : pos_change,
    })
    return df


# ── Performance metrics ───────────────────────────────────────────────────────

def compute_metrics(bt: pd.DataFrame,
                    initial_capital: float = 100_000.0,
                    risk_free: float = 0.04) -> dict:
    """
    Compute comprehensive performance metrics from backtest results.
    """
    rets = bt["strategy_ret"].dropna()

    # Annualised return
    n_days   = len(rets)
    ann_ret  = float(rets.sum() * 252 / n_days) if n_days > 0 else 0.0

    # Annualised volatility
    ann_vol  = float(rets.std() * np.sqrt(252)) if len(rets) > 1 else 0.0

    # Sharpe ratio
    daily_rf = risk_free / 252
    sharpe   = float((rets.mean() - daily_rf) / rets.std() * np.sqrt(252)) \
               if rets.std() > 0 else 0.0

    # Sortino ratio (downside deviation)
    neg_rets = rets[rets < 0]
    down_vol = float(neg_rets.std() * np.sqrt(252)) if len(neg_rets) > 1 else 0.001
    sortino  = float((ann_ret - risk_free) / down_vol) if down_vol > 0 else 0.0

    # Max drawdown
    max_dd   = float(bt["drawdown"].min())

    # Calmar ratio
    calmar   = float(ann_ret / abs(max_dd) * 100) if max_dd != 0 else 0.0

    # Win rate
    daily_pnl = rets
    win_rate  = float((daily_pnl > 0).sum() / len(daily_pnl) * 100) if len(daily_pnl) > 0 else 0.0

    # Total PnL
    total_pnl = float(bt["cum_pnl"].iloc[-1]) if len(bt) > 0 else 0.0
    total_ret = float(total_pnl / initial_capital * 100)

    # Number of trades
    n_trades  = int((bt["pos_change"] > 0.1).sum())

    # Best / worst day
    best_day  = float(rets.max() * 100)
    worst_day = float(rets.min() * 100)

    return {
        "ann_return"  : ann_ret * 100,
        "ann_vol"     : ann_vol * 100,
        "sharpe"      : sharpe,
        "sortino"     : sortino,
        "max_drawdown": max_dd,
        "calmar"      : calmar,
        "win_rate"    : win_rate,
        "total_pnl"   : total_pnl,
        "total_return": total_ret,
        "n_trades"    : n_trades,
        "best_day"    : best_day,
        "worst_day"   : worst_day,
        "n_days"      : n_days,
    }


# ── Multi-strategy runner ─────────────────────────────────────────────────────

STRATEGY_PARAMS = {
    "Trend Following": {
        "fn"    : lambda p, c: signal_trend(p, fast=20, slow=60),
        "color" : "#F5D060",
        "desc"  : "EMA crossover (20/60d). Long when fast > slow.",
    },
    "Mean Reversion": {
        "fn"    : lambda p, c: signal_mean_reversion(p, window=20, n_std=1.5),
        "color" : "#5BAEFF",
        "desc"  : "Bollinger Bands (20d, 1.5σ). Contrarian.",
    },
    "Momentum": {
        "fn"    : lambda p, c: signal_momentum(p, lookback=21),
        "color" : "#FF7EB3",
        "desc"  : "1-month price momentum. Long if up, short if down.",
    },
    "Weather-Driven": {
        "fn"    : lambda p, c: signal_weather(p, c),
        "color" : "#4AFF99",
        "desc"  : "Seasonal patterns. Cocoa: ENSO proxy. Gas: HDD.",
    },
    "Vol Breakout": {
        "fn"    : lambda p, c: signal_volatility_breakout(p, window=20),
        "color" : "#C8A8FF",
        "desc"  : "ATR breakout above recent high (20d window).",
    },
    "Combined (Equal Weight)": {
        "fn"    : lambda p, c: combine_signals(
                    signal_trend(p),
                    signal_mean_reversion(p),
                    signal_momentum(p),
                    signal_weather(p, c),
                    signal_volatility_breakout(p),
                  ),
        "color" : "#FFFFFF",
        "desc"  : "Equal-weight ensemble of all 5 strategies.",
    },
}


def run_all_strategies(prices: pd.Series,
                       commodity: str,
                       initial_capital: float = 100_000.0,
                       transaction_cost: float = 0.001) -> dict:
    """
    Run all strategies on a price series and return results dict.

    Returns
    -------
    dict: {strategy_name: {"bt": DataFrame, "metrics": dict}}
    """
    results = {}
    for name, cfg in STRATEGY_PARAMS.items():
        try:
            sig = cfg["fn"](prices, commodity)
            bt  = run_backtest(prices, sig,
                               transaction_cost=transaction_cost,
                               initial_capital=initial_capital)
            metrics = compute_metrics(bt, initial_capital)
            results[name] = {
                "bt"      : bt,
                "metrics" : metrics,
                "color"   : cfg["color"],
                "desc"    : cfg["desc"],
            }
        except Exception as e:
            results[name] = {"error": str(e)}

    return results


def benchmark_buy_hold(prices: pd.Series,
                       initial_capital: float = 100_000.0) -> dict:
    """Buy-and-hold benchmark for comparison."""
    sig = pd.Series(1.0, index=prices.index)
    bt  = run_backtest(prices, sig, transaction_cost=0.0,
                       initial_capital=initial_capital)
    return {"bt": bt, "metrics": compute_metrics(bt, initial_capital),
            "color": "#444444", "desc": "Buy & Hold (benchmark)"}
