"""
data/fetcher.py
===============
Market data fetcher for commodity futures.
Uses yfinance as primary source; falls back to synthetic data
so the app always runs even without internet.

Tickers used:
  Cocoa  : CC=F  (ICE front-month)
  Gas TTF: TTF=F  (note: limited coverage on yf, use NG=F as proxy)
  Uranium: URA   (Sprott ETF as proxy — U3O8 OTC has no yf feed)
  Gold   : GC=F  (benchmark)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Ticker map ────────────────────────────────────────────────────────────────
TICKERS = {
    "cocoa"  : {"spot": "CC=F",  "name": "Cacao ICE",    "unit": "USD/MT",  "currency": "USD"},
    "gas"    : {"spot": "NG=F",  "name": "Gas Nat. TTF", "unit": "USD/MMBtu","currency": "USD"},
    "uranium": {"spot": "URA",   "name": "Uranio U3O8",  "unit": "USD",     "currency": "USD"},
    "gold"   : {"spot": "GC=F",  "name": "Oro COMEX",    "unit": "USD/oz",  "currency": "USD"},
}

# ── Synthetic parameter seeds (calibrated to historical data) ─────────────────
SYNTH_PARAMS = {
    "cocoa"  : {"spot": 9240, "mu": 0.03, "sigma": 0.38, "kappa": 0.8},
    "gas"    : {"spot": 2.85, "mu": 0.00, "sigma": 0.55, "kappa": 2.1},
    "uranium": {"spot": 78.5, "mu": 0.05, "sigma": 0.28, "kappa": 0.3},
    "gold"   : {"spot": 2320, "mu": 0.02, "sigma": 0.15, "kappa": 0.2},
}


def _synth_prices(commodity: str, days: int = 504, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV via mean-reverting log-price process."""
    p  = SYNTH_PARAMS[commodity]
    S0, mu, sigma, kappa = p["spot"], p["mu"], p["sigma"], p["kappa"]
    rng = np.random.default_rng(seed)
    dt  = 1/252
    prices = [S0]
    for _ in range(days - 1):
        drift     = kappa * (np.log(S0) - np.log(prices[-1])) * dt + mu * dt
        diffusion = sigma * np.sqrt(dt) * rng.standard_normal()
        prices.append(prices[-1] * np.exp(drift + diffusion))
    prices = np.array(prices)
    idx = pd.bdate_range(end=datetime.today(), periods=days)
    noise = lambda s: 1 + rng.uniform(-s, s, days)
    df = pd.DataFrame({
        "Open"  : prices * noise(0.003),
        "High"  : prices * (1 + np.abs(rng.normal(0, 0.008, days))),
        "Low"   : prices * (1 - np.abs(rng.normal(0, 0.008, days))),
        "Close" : prices,
        "Volume": rng.integers(1000, 50000, days).astype(float),
    }, index=idx)
    df["Adj Close"] = df["Close"]
    return df


def fetch_prices(commodity: str, period_days: int = 504) -> pd.DataFrame:
    """
    Fetch OHLCV data for a commodity.
    Tries yfinance first; falls back to synthetic on any failure.

    Returns
    -------
    pd.DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
    """
    ticker = TICKERS[commodity]["spot"]
    try:
        import yfinance as yf
        end   = datetime.today()
        start = end - timedelta(days=int(period_days * 1.5))
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 20:
            raise ValueError("Insufficient data")
        # Normalise columns
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        df = df.dropna(subset=["Close"]).tail(period_days)
        df.attrs["source"] = "yfinance"
        return df
    except Exception:
        df = _synth_prices(commodity, days=period_days)
        df.attrs["source"] = "synthetic"
        return df


def get_spot(commodity: str) -> tuple[float, str]:
    """Return (spot_price, source) using most recent close."""
    df = fetch_prices(commodity, period_days=5)
    return float(df["Close"].iloc[-1]), df.attrs.get("source", "synthetic")


def compute_returns(df: pd.DataFrame) -> pd.Series:
    """Log returns from Close prices."""
    return np.log(df["Close"] / df["Close"].shift(1)).dropna()


def rolling_vol(df: pd.DataFrame, window: int = 21) -> pd.Series:
    """Annualised rolling historical volatility."""
    returns = compute_returns(df)
    return returns.rolling(window).std() * np.sqrt(252)


def compute_stats(commodity: str, df: pd.DataFrame | None = None) -> dict:
    """Return dict of key statistics for the commodity."""
    if df is None:
        df = fetch_prices(commodity)
    rets   = compute_returns(df)
    close  = df["Close"]
    vol252 = rolling_vol(df, 252).iloc[-1]
    vol21  = rolling_vol(df, 21).iloc[-1]
    spot   = float(close.iloc[-1])
    prev   = float(close.iloc[-2]) if len(close) > 1 else spot
    return {
        "spot"        : spot,
        "prev_close"  : prev,
        "pct_change"  : (spot / prev - 1) * 100,
        "vol_1m"      : float(vol21)  * 100,
        "vol_1y"      : float(vol252) * 100,
        "ret_1m"      : float((close.iloc[-1] / close.iloc[-22] - 1) * 100) if len(close) > 22 else 0,
        "ret_3m"      : float((close.iloc[-1] / close.iloc[-63] - 1) * 100) if len(close) > 63 else 0,
        "ret_1y"      : float((close.iloc[-1] / close.iloc[-252] - 1) * 100) if len(close) > 252 else 0,
        "high_52w"    : float(close.tail(252).max()),
        "low_52w"     : float(close.tail(252).min()),
        "skewness"    : float(rets.skew()),
        "kurtosis"    : float(rets.kurt()),
        "source"      : df.attrs.get("source", "unknown"),
    }


# ── Synthetic futures term structure ─────────────────────────────────────────
def build_term_structure(spot: float, r: float, u: float,
                         kappa: float, alpha_lr: float, sigma: float,
                         lambda_param: float,
                         maturities: list | None = None) -> pd.DataFrame:
    """
    Build futures term structure using Schwartz 1-factor formula.
    Used when no exchange-listed futures chain is available.
    """
    if maturities is None:
        maturities = [1/12, 2/12, 3/12, 6/12, 9/12, 1.0, 1.5, 2.0, 3.0]
    rows = []
    for T in maturities:
        alpha_star = alpha_lr - lambda_param * sigma / kappa - sigma**2 / (4*kappa)
        A = sigma**2 / (4*kappa) * (1 - np.exp(-2*kappa*T))
        lnF = np.exp(-kappa*T) * np.log(spot) + (1 - np.exp(-kappa*T)) * alpha_star + A
        F = np.exp(lnF)
        cy = r + u - (1/T) * np.log(F/spot) if T > 0 else 0
        lbl = f"{int(T*12)}M" if T < 1 else f"{T:.1f}Y"
        rows.append({"maturity": T, "label": lbl,
                     "futures": round(F, 2), "cy": round(cy*100, 3),
                     "basis": round(F - spot, 2)})
    return pd.DataFrame(rows)
