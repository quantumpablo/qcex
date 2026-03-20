"""
analytics/risk.py
=================
Risk analytics: Historical VaR, CVaR, stress scenarios,
correlation matrix, rolling metrics.
"""

from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


# ── VaR / CVaR ───────────────────────────────────────────────────────────────

def historical_var(returns: pd.Series, confidence: float = 0.99,
                   horizon: int = 1) -> float:
    """
    Historical VaR at given confidence level, scaled to horizon (days).
    Returns positive number (loss expressed as positive).
    """
    scaled = returns * np.sqrt(horizon)
    return float(-np.percentile(scaled.dropna(), (1 - confidence) * 100))


def historical_cvar(returns: pd.Series, confidence: float = 0.99,
                    horizon: int = 1) -> float:
    """Expected Shortfall (CVaR) — mean of losses beyond VaR threshold."""
    scaled = returns * np.sqrt(horizon)
    var    = historical_var(returns, confidence, horizon)
    tail   = scaled[scaled < -var]
    return float(-tail.mean()) if len(tail) > 0 else var


def parametric_var(returns: pd.Series, confidence: float = 0.99,
                   horizon: int = 1) -> float:
    """Gaussian VaR: σ · z_α · √horizon."""
    sigma = returns.std()
    z     = stats.norm.ppf(1 - confidence)
    return float(-sigma * z * np.sqrt(horizon))


def rolling_var(returns: pd.Series, window: int = 252,
                confidence: float = 0.99, horizon: int = 1) -> pd.Series:
    """Rolling historical VaR."""
    return returns.rolling(window).apply(
        lambda r: historical_var(pd.Series(r), confidence, horizon), raw=False
    )


# ── Stress scenarios ──────────────────────────────────────────────────────────

STRESS_SCENARIOS = {
    "cocoa": [
        {"name": "El Niño severo", "shock": -0.45,
         "desc": "Sequía extrema Ghana/Costa de Marfil. Similar a 2023-24."},
        {"name": "Normalización oferta", "shock": +0.30,
         "desc": "Recuperación producción después de ciclo de escasez."},
        {"name": "Caída demanda global", "shock": -0.20,
         "desc": "Recesión Europa+USA. Grind industrial cae 10%."},
        {"name": "Crisis divisa XOF", "shock": +0.15,
         "desc": "Devaluación franco CFA → exportaciones más caras."},
        {"name": "Fungal disease (swollen shoot)", "shock": -0.35,
         "desc": "Enfermedad devastadora. Pérdida 30% cosecha."},
    ],
    "gas": [
        {"name": "Invierno frío extremo", "shock": +0.80,
         "desc": "HDD Europa +40% vs media. Demanda calefacción dispara precios."},
        {"name": "Interrupción GNL", "shock": +0.60,
         "desc": "Huelga terminales GNL EEUU. -20% importaciones europeas."},
        {"name": "Verano suave + renovables", "shock": -0.35,
         "desc": "Generación eólica récord. Storage llena al 95% en septiembre."},
        {"name": "Resolución conflicto Rusia", "shock": -0.50,
         "desc": "Reapertura gasoductos rusos. Exceso oferta."},
        {"name": "Crisis storage Q3", "shock": +0.40,
         "desc": "Incidentes técnicos en 5 instalaciones storage EU."},
    ],
    "uranium": [
        {"name": "Accidente nuclear", "shock": -0.40,
         "desc": "Incidente nivel 4-5. Varios países paralizan reactores."},
        {"name": "Política pro-nuclear", "shock": +0.35,
         "desc": "Alemania, Italia anuncian nuevos reactores. +15 GW capacidad."},
        {"name": "Recorte Kazatomprom", "shock": +0.50,
         "desc": "Kazakhstan reduce producción 20%. Representa 43% suministro global."},
        {"name": "SMR rollout", "shock": +0.25,
         "desc": "Small Modular Reactors aprobados en 5 países. Demanda futura."},
        {"name": "Saturación inventarios", "shock": -0.25,
         "desc": "Utilities descargan inventarios estratégicos acumulados."},
    ],
    "gold": [
        {"name": "Crisis financiera sistémica", "shock": +0.30,
         "desc": "Quiebra banco G-SIB. Flight-to-quality masivo."},
        {"name": "Subida tipos Fed +200bp", "shock": -0.20,
         "desc": "Coste oportunidad sube. Salida flujos ETF oro."},
        {"name": "Compras bancos centrales", "shock": +0.15,
         "desc": "China, India duplican reservas. Demanda oficial +500T."},
        {"name": "Deflación + recesión", "shock": +0.25,
         "desc": "Escenario stagflación. Oro como cobertura real."},
        {"name": "Dólar USD +15%", "shock": -0.12,
         "desc": "Rally USD reduce atractivo oro para inversores no-USD."},
    ],
}


def apply_stress(spot: float, scenario: dict) -> dict:
    """Apply a stress scenario to spot price."""
    shocked = spot * (1 + scenario["shock"])
    return {
        "name"    : scenario["name"],
        "shock_pct": scenario["shock"] * 100,
        "spot_orig": spot,
        "spot_shock": shocked,
        "pnl"     : shocked - spot,
        "desc"    : scenario["desc"],
    }


def stress_table(commodity: str, spot: float) -> pd.DataFrame:
    """Return DataFrame of stress test results for a commodity."""
    scenarios = STRESS_SCENARIOS.get(commodity, [])
    rows = [apply_stress(spot, s) for s in scenarios]
    return pd.DataFrame(rows)


# ── Correlation & portfolio ───────────────────────────────────────────────────

def correlation_matrix(returns_dict: Dict[str, pd.Series]) -> pd.DataFrame:
    """Compute correlation matrix from dict of return series."""
    df = pd.DataFrame(returns_dict).dropna()
    return df.corr()


def rolling_correlation(s1: pd.Series, s2: pd.Series,
                        window: int = 60) -> pd.Series:
    """Rolling Pearson correlation between two return series."""
    df = pd.concat([s1, s2], axis=1).dropna()
    return df.iloc[:, 0].rolling(window).corr(df.iloc[:, 1])


# ── Realised vol decomposition ────────────────────────────────────────────────

def vol_cone(returns: pd.Series,
             windows: Optional[list] = None) -> pd.DataFrame:
    """
    Volatility cone: shows percentile distribution of realised vol
    across different horizons.
    """
    if windows is None:
        windows = [5, 10, 21, 63, 126, 252]
    rows = []
    for w in windows:
        rv = returns.rolling(w).std() * np.sqrt(252) * 100
        rv = rv.dropna()
        if len(rv) < 5:
            continue
        rows.append({
            "window"   : w,
            "label"    : f"{w}d",
            "current"  : float(rv.iloc[-1]),
            "min"      : float(rv.min()),
            "p10"      : float(rv.quantile(0.10)),
            "p25"      : float(rv.quantile(0.25)),
            "median"   : float(rv.median()),
            "p75"      : float(rv.quantile(0.75)),
            "p90"      : float(rv.quantile(0.90)),
            "max"      : float(rv.max()),
        })
    return pd.DataFrame(rows)


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Compute drawdown series from price series."""
    roll_max = prices.cummax()
    return (prices - roll_max) / roll_max * 100


def max_drawdown(prices: pd.Series) -> float:
    """Maximum drawdown (as % loss from peak)."""
    return float(drawdown_series(prices).min())
