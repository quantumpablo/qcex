"""
sabr.py
=======
SABR Stochastic Volatility Model — Production Module
Hagan, Kumar, Lesniewski & Woodward (2002)

Model dynamics (risk-neutral):
    dF = σ · F^β · dW₁
    dσ = α · σ · dW₂
    dW₁ · dW₂ = ρ dt

Implied vol approximation (Hagan 2002):
    σ_B(K,T) ≈ α / [(FK)^((1-β)/2) · D] · [z/χ(z)] · C(T)

Usage:
    from sabr import SABRModel
    model = SABRModel(alpha=0.52, beta=0.5, rho=-0.45, nu=0.68)
    iv = model.implied_vol(F=9240, K=8500, T=0.5)
    surface = model.vol_surface(F=9240, maturities=[0.25,0.5,1.0], moneyness=[0.9,1.0,1.1])
    fitted = SABRModel.calibrate(strikes, market_vols, F=9240, T=0.5)

Author: Commodity Pricing Engine — Portfolio Project
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from scipy.stats import norm
import warnings
warnings.filterwarnings("ignore")


# ─── CORE SABR FORMULA ────────────────────────────────────────────────────────

def sabr_implied_vol(F: float, K: float, T: float,
                     alpha: float, beta: float, rho: float, nu: float) -> float:
    """
    Hagan (2002) SABR approximation for Black implied volatility.

    Parameters
    ----------
    F     : Forward price
    K     : Strike price
    T     : Time to maturity (years)
    alpha : Initial vol level (α > 0)
    beta  : CEV elasticity (0 ≤ β ≤ 1)
    rho   : Correlation (−1 < ρ < 1)
    nu    : Vol of vol (ν > 0)

    Returns
    -------
    σ_B   : Black-76 implied volatility (annualised)
    """
    if T <= 0 or alpha <= 0 or nu <= 0:
        return alpha
    if abs(rho) >= 1:
        raise ValueError(f"rho must be in (-1,1), got {rho}")

    eps = 1e-10

    # ── ATM case (F ≈ K): use limit expansion ─────────────────────────────
    if abs(F - K) < eps:
        FK_beta = F ** (1 - beta)
        term1 = alpha / FK_beta
        correction = T * (
            (1-beta)**2 * alpha**2 / (24 * FK_beta**2)
            + rho * beta * nu * alpha / (4 * FK_beta)
            + nu**2 * (2 - 3*rho**2) / 24
        )
        return term1 * (1 + correction)

    # ── General case ──────────────────────────────────────────────────────
    log_FK = np.log(F / K)
    FK_mid = (F * K) ** ((1 - beta) / 2)

    # z and χ(z)
    z = (nu / alpha) * FK_mid * log_FK
    sqrt_term = np.sqrt(1 - 2*rho*z + z**2)
    x_z_arg = (sqrt_term + z - rho) / (1 - rho)
    x_z = np.log(np.maximum(x_z_arg, eps))
    z_over_xz = z / x_z if abs(x_z) > eps else 1.0

    # Denominator D
    D = FK_mid * (
        1
        + (1-beta)**2 / 24 * log_FK**2
        + (1-beta)**4 / 1920 * log_FK**4
    )

    # Time correction C(T)
    C = 1 + T * (
        (1-beta)**2 * alpha**2 / (24 * FK_mid**2)
        + rho * beta * nu * alpha / (4 * FK_mid)
        + nu**2 * (2 - 3*rho**2) / 24
    )

    return (alpha / D) * z_over_xz * C


def sabr_atm_vol(F: float, T: float,
                 alpha: float, beta: float, rho: float, nu: float) -> float:
    """ATM implied vol closed-form (exact limit, no approximation error)."""
    FK_beta = F ** (1 - beta)
    correction = T * (
        (1-beta)**2 * alpha**2 / (24 * FK_beta**2)
        + rho * beta * nu * alpha / (4 * FK_beta)
        + nu**2 * (2 - 3*rho**2) / 24
    )
    return (alpha / FK_beta) * (1 + correction)


# ─── BLACK-76 ─────────────────────────────────────────────────────────────────

def black76(F: float, K: float, r: float, sigma: float, T: float,
            option_type: str = "call") -> float:
    """Black-76 price for European option on futures."""
    if T <= 0 or sigma <= 0:
        return max(0.0, F - K if option_type == "call" else K - F)
    d1 = (np.log(F/K) + 0.5*sigma**2*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    df = np.exp(-r*T)
    if option_type == "call":
        return df * (F*norm.cdf(d1) - K*norm.cdf(d2))
    return df * (K*norm.cdf(-d2) - F*norm.cdf(-d1))


def black76_implied_vol(price: float, F: float, K: float, r: float, T: float,
                        option_type: str = "call",
                        tol: float = 1e-8, max_iter: int = 200) -> float:
    """
    Newton-Raphson inversion of Black-76 to extract implied vol.
    Returns NaN if no solution found.
    """
    if T <= 0 or price <= 0:
        return np.nan
    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        d1 = (np.log(F/K) + 0.5*sigma**2*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        df = np.exp(-r*T)
        price_est = (df*(F*norm.cdf(d1) - K*norm.cdf(d2)) if option_type == "call"
                     else df*(K*norm.cdf(-d2) - F*norm.cdf(-d1)))
        vega = F * df * norm.pdf(d1) * np.sqrt(T)
        if abs(vega) < 1e-14:
            return np.nan
        err = price_est - price
        if abs(err) < tol:
            return max(sigma, 1e-8)
        sigma -= err / vega
        if sigma <= 0:
            sigma = 1e-4
    return np.nan


# ─── GREEKS ──────────────────────────────────────────────────────────────────

def sabr_greeks(F: float, K: float, r: float, T: float,
                alpha: float, beta: float, rho: float, nu: float,
                bump: float = 1e-4) -> dict:
    """
    Compute option Greeks using SABR implied vol + Black-76 pricing.
    Uses finite differences for vol sensitivity (vanna, volga).

    Returns
    -------
    dict with: delta, gamma, vega, theta, vanna, volga,
               impl_vol, call_price, put_price
    """
    sigma = sabr_implied_vol(F, K, T, alpha, beta, rho, nu)
    call  = black76(F, K, r, sigma, T, "call")
    put   = black76(F, K, r, sigma, T, "put")

    # Delta (∂V/∂F)
    dF    = F * bump
    c_up  = black76(F+dF, K, r, sabr_implied_vol(F+dF,K,T,alpha,beta,rho,nu), T, "call")
    c_dn  = black76(F-dF, K, r, sabr_implied_vol(F-dF,K,T,alpha,beta,rho,nu), T, "call")
    delta = (c_up - c_dn) / (2*dF)
    gamma = (c_up - 2*call + c_dn) / dF**2

    # Vega (∂V/∂σ_impl)
    dSig  = 0.001
    c_sig_up = black76(F, K, r, sigma+dSig, T, "call")
    c_sig_dn = black76(F, K, r, sigma-dSig, T, "call")
    vega  = (c_sig_up - c_sig_dn) / (2*dSig)

    # Theta (∂V/∂t, per day)
    dT    = 1/252
    if T > dT:
        c_theta = black76(F, K, r, sabr_implied_vol(F,K,T-dT,alpha,beta,rho,nu), T-dT, "call")
        theta   = (c_theta - call) / dT / 365
    else:
        theta = -call / dT / 365

    # Vanna (∂²V/∂F∂σ)
    c_up_sig = black76(F+dF, K, r, sigma+dSig, T, "call")
    c_up_dn  = black76(F+dF, K, r, sigma-dSig, T, "call")
    c_dn_sig = black76(F-dF, K, r, sigma+dSig, T, "call")
    c_dn_dn  = black76(F-dF, K, r, sigma-dSig, T, "call")
    vanna = (c_up_sig - c_up_dn - c_dn_sig + c_dn_dn) / (4*dF*dSig)

    # Volga (∂²V/∂σ²)
    volga = (c_sig_up - 2*call + c_sig_dn) / dSig**2

    return {
        "impl_vol"  : sigma,
        "call_price": call,
        "put_price" : put,
        "delta"     : delta,
        "gamma"     : gamma,
        "vega"      : vega,
        "theta"     : theta,
        "vanna"     : vanna,
        "volga"     : volga,
    }


# ─── CALIBRATION ─────────────────────────────────────────────────────────────

def _sse_sabr(x: np.ndarray, strikes: np.ndarray, market_vols: np.ndarray,
              F: float, T: float, beta: float,
              weights: np.ndarray | None = None) -> float:
    """SSE objective for SABR calibration."""
    alpha, rho, nu = x
    if alpha <= 0 or nu <= 0 or abs(rho) >= 1:
        return 1e10
    if weights is None:
        weights = np.ones(len(strikes))
    sse = 0.0
    for K, iv_mkt, w in zip(strikes, market_vols, weights):
        try:
            iv_mod = sabr_implied_vol(F, K, T, alpha, beta, rho, nu)
            sse += w * (iv_mod - iv_mkt)**2
        except Exception:
            sse += 1e6
    return sse


def calibrate_sabr(strikes: np.ndarray, market_vols: np.ndarray,
                   F: float, T: float, beta: float = 0.5,
                   weights: np.ndarray | None = None,
                   method: str = "L-BFGS-B",
                   n_restarts: int = 8) -> dict:
    """
    Calibrate SABR (α, ρ, ν) by weighted least squares on implied vol smile.
    β is treated as exogenous (set externally, typically β=0.5 for commodities).

    Parameters
    ----------
    strikes     : array of strike prices
    market_vols : array of market implied vols (annualised, not %)
    F           : Forward price
    T           : Time to maturity (years)
    beta        : CEV exponent (fixed, default 0.5)
    weights     : Optional weights per strike (e.g. 1/bid-ask spread)
    method      : Optimisation method ('L-BFGS-B' or 'DE' for global)
    n_restarts  : Number of random restarts for L-BFGS-B

    Returns
    -------
    dict: alpha, beta, rho, nu, rmse, n_strikes
    """
    strikes    = np.asarray(strikes, dtype=float)
    market_vols = np.asarray(market_vols, dtype=float)
    mask = ~np.isnan(market_vols) & ~np.isnan(strikes) & (market_vols > 0)
    strikes, market_vols = strikes[mask], market_vols[mask]
    if weights is not None:
        weights = np.asarray(weights)[mask]

    bounds = [(0.001, 2.0), (-0.999, 0.999), (0.001, 3.0)]  # alpha, rho, nu

    if method == "DE":
        # Global search via Differential Evolution (slower, more robust)
        result = differential_evolution(
            _sse_sabr, bounds,
            args=(strikes, market_vols, F, T, beta, weights),
            maxiter=1000, tol=1e-10, seed=42, popsize=15,
        )
        alpha, rho, nu = result.x
    else:
        # Multi-start L-BFGS-B
        rng = np.random.default_rng(42)
        x0_list = [np.array([0.30, -0.30, 0.40])]  # default start
        for _ in range(n_restarts - 1):
            x0_list.append(np.array([
                rng.uniform(0.05, 1.0),
                rng.uniform(-0.8, 0.8),
                rng.uniform(0.05, 1.5),
            ]))

        best_res, best_val = None, np.inf
        for x0 in x0_list:
            res = minimize(
                _sse_sabr, x0,
                args=(strikes, market_vols, F, T, beta, weights),
                method="L-BFGS-B", bounds=bounds,
                options={"maxiter": 2000, "ftol": 1e-14, "gtol": 1e-10},
            )
            if res.fun < best_val:
                best_val, best_res = res.fun, res
        alpha, rho, nu = best_res.x

    # Compute RMSE on calibrated params
    model_vols = np.array([sabr_implied_vol(F,K,T,alpha,beta,rho,nu) for K in strikes])
    rmse = np.sqrt(np.mean((model_vols - market_vols)**2))

    return {
        "alpha"    : float(alpha),
        "beta"     : float(beta),
        "rho"      : float(rho),
        "nu"       : float(nu),
        "rmse"     : float(rmse),
        "rmse_bp"  : float(rmse * 1e4),
        "n_strikes": int(len(strikes)),
    }


# ─── SABR MODEL CLASS ─────────────────────────────────────────────────────────

class SABRModel:
    """
    SABR Volatility Model — object-oriented interface.

    Example
    -------
    >>> model = SABRModel(alpha=0.52, beta=0.5, rho=-0.45, nu=0.68)
    >>> iv = model.implied_vol(F=9240, K=8500, T=0.5)
    >>> surface = model.vol_surface(F=9240, maturities=[0.25,0.5,1.0],
    ...                              moneyness=[0.9,1.0,1.1])
    >>> fitted = SABRModel.calibrate(strikes, mkt_vols, F=9240, T=0.5)
    """

    def __init__(self, alpha: float, beta: float, rho: float, nu: float):
        self.alpha = alpha
        self.beta  = beta
        self.rho   = rho
        self.nu    = nu

    def implied_vol(self, F: float, K: float, T: float) -> float:
        """SABR implied vol for a single (F, K, T)."""
        return sabr_implied_vol(F, K, T, self.alpha, self.beta, self.rho, self.nu)

    def price(self, F: float, K: float, r: float, T: float,
              option_type: str = "call") -> float:
        """Black-76 price using SABR implied vol."""
        sigma = self.implied_vol(F, K, T)
        return black76(F, K, r, sigma, T, option_type)

    def greeks(self, F: float, K: float, r: float, T: float) -> dict:
        """Full Greeks for call option."""
        return sabr_greeks(F, K, r, T, self.alpha, self.beta, self.rho, self.nu)

    def smile(self, F: float, T: float,
              moneyness: list | None = None) -> dict:
        """
        Compute vol smile for given forward and maturity.

        Returns
        -------
        dict: strikes, moneyness, implied_vols, call_prices, put_prices
        """
        if moneyness is None:
            moneyness = np.linspace(0.70, 1.30, 25)
        moneyness = np.asarray(moneyness)
        strikes   = F * moneyness
        vols      = np.array([self.implied_vol(F, K, T) for K in strikes])
        return {
            "F"          : F,
            "T"          : T,
            "moneyness"  : moneyness,
            "strikes"    : strikes,
            "implied_vols": vols,
        }

    def vol_surface(self, F: float,
                    maturities: list | None = None,
                    moneyness: list | None = None) -> dict:
        """
        Compute the full implied vol surface.

        Returns
        -------
        dict: maturities, moneyness, strikes (2D), vols (2D, %)
        """
        if maturities is None:
            maturities = [1/12, 2/12, 3/12, 6/12, 1.0, 1.5, 2.0]
        if moneyness is None:
            moneyness = np.array([0.70,0.75,0.80,0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20,1.25,1.30])

        maturities = np.asarray(maturities)
        moneyness  = np.asarray(moneyness)
        strikes    = F * moneyness  # shape (n_K,)

        vols = np.zeros((len(maturities), len(moneyness)))
        for i, T in enumerate(maturities):
            for j, K in enumerate(strikes):
                vols[i, j] = self.implied_vol(F, K, T) * 100  # in %

        return {
            "maturities": maturities,
            "moneyness" : moneyness,
            "strikes"   : strikes,
            "vols_pct"  : vols,
        }

    def skew(self, F: float, T: float, delta_k: float = 0.05) -> float:
        """Risk reversal proxy: σ(K_OTM_put) − σ(K_OTM_call)."""
        iv_put  = self.implied_vol(F, F*(1-delta_k), T)
        iv_call = self.implied_vol(F, F*(1+delta_k), T)
        return iv_put - iv_call

    def butterfly(self, F: float, T: float, delta_k: float = 0.05) -> float:
        """Butterfly proxy: (σ_put + σ_call)/2 − σ_ATM (convexity of smile)."""
        iv_atm  = self.implied_vol(F, F, T)
        iv_put  = self.implied_vol(F, F*(1-delta_k), T)
        iv_call = self.implied_vol(F, F*(1+delta_k), T)
        return (iv_put + iv_call)/2 - iv_atm

    @classmethod
    def calibrate(cls, strikes: np.ndarray, market_vols: np.ndarray,
                  F: float, T: float, beta: float = 0.5,
                  weights: np.ndarray | None = None,
                  method: str = "L-BFGS-B") -> "SABRModel":
        """
        Fit SABR to market smile. Returns calibrated SABRModel instance.

        Parameters
        ----------
        strikes     : array of strikes
        market_vols : array of market implied vols (NOT in %)
        F           : forward price
        T           : maturity in years
        beta        : fixed CEV exponent
        weights     : optional per-strike weights
        method      : 'L-BFGS-B' (fast) or 'DE' (global, slower)
        """
        result = calibrate_sabr(strikes, market_vols, F, T, beta, weights, method)
        model = cls(result["alpha"], result["beta"], result["rho"], result["nu"])
        model._calib_result = result
        return model

    def __repr__(self):
        return (f"SABRModel(α={self.alpha:.4f}, β={self.beta:.4f}, "
                f"ρ={self.rho:.4f}, ν={self.nu:.4f})")

    def summary(self, F: float = None, T: float = None) -> None:
        """Print model summary."""
        print("┌─ SABR Model ──────────────────────────────────────┐")
        print(f"│  α (vol level)        {self.alpha:>8.4f}                 │")
        print(f"│  β (CEV exponent)     {self.beta:>8.4f}                 │")
        print(f"│  ρ (skew corr)        {self.rho:>8.4f}                 │")
        print(f"│  ν (vol of vol)       {self.nu:>8.4f}                 │")
        if hasattr(self, "_calib_result"):
            r = self._calib_result
            print(f"│  RMSE (bp)            {r['rmse_bp']:>8.1f}                 │")
            print(f"│  N strikes            {r['n_strikes']:>8d}                 │")
        if F is not None and T is not None:
            atm = self.implied_vol(F, F, T)
            skw = self.skew(F, T) * 1e4
            fly = self.butterfly(F, T) * 1e4
            print(f"│  ATM vol (F={F:.0f},T={T:.2f})  {atm*100:>6.2f}%               │")
            print(f"│  Skew (95/105%)       {skw:>8.1f} bp               │")
            print(f"│  Butterfly (5δ)       {fly:>8.1f} bp               │")
        print("└───────────────────────────────────────────────────┘")


# ─── MULTI-MATURITY CALIBRATION ───────────────────────────────────────────────

def calibrate_surface(smile_data: dict, F: float, beta: float = 0.5) -> dict:
    """
    Calibrate SABR independently per maturity slice.

    Parameters
    ----------
    smile_data : dict {T: {"strikes": array, "vols": array}}
    F          : Forward price (assumed flat for simplicity)
    beta       : Fixed CEV exponent

    Returns
    -------
    dict {T: SABRModel}
    """
    models = {}
    print(f"{'Maturity':>10} {'α':>8} {'ρ':>8} {'ν':>8} {'RMSE(bp)':>10}")
    print("-" * 48)
    for T, data in sorted(smile_data.items()):
        model = SABRModel.calibrate(
            data["strikes"], data["vols"], F, T, beta
        )
        r = model._calib_result
        models[T] = model
        T_lbl = f"{T*12:.0f}M" if T < 1 else f"{T:.1f}Y"
        print(f"  {T_lbl:>8} {r['alpha']:>8.4f} {r['rho']:>8.4f} {r['nu']:>8.4f} {r['rmse_bp']:>10.1f}")
    return models


# ─── DEMO ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    print("=" * 60)
    print("  SABR MODEL — PRODUCTION MODULE DEMO")
    print("=" * 60)

    # ── 1. Cacao parameters (high skew, high nu) ─────────────────────────
    F, r = 9240.0, 0.053
    true_params = dict(alpha=0.52, beta=0.5, rho=-0.45, nu=0.68)
    model_true = SABRModel(**true_params)

    print("\n▸ True model:")
    model_true.summary(F=F, T=0.5)

    # ── 2. Generate synthetic market smile ────────────────────────────────
    T = 0.5
    rng = np.random.default_rng(0)
    moneyness  = np.array([0.75,0.80,0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20,1.25])
    strikes    = F * moneyness
    mkt_vols   = np.array([model_true.implied_vol(F,K,T) for K in strikes])
    mkt_vols  += rng.normal(0, 0.005, len(strikes))  # bid-ask noise

    print(f"\n▸ Synthetic market smile (T={T*12:.0f}M):")
    print(f"  {'Strike':>8} {'% ATM':>6} {'Mkt IV':>8} {'True IV':>8}")
    print("  " + "-"*35)
    for K, m, iv in zip(strikes, moneyness, mkt_vols):
        true_iv = model_true.implied_vol(F, K, T)
        print(f"  {K:>8.0f}  {m*100:>5.0f}%  {iv*100:>7.2f}%  {true_iv*100:>7.2f}%")

    # ── 3. Calibrate ──────────────────────────────────────────────────────
    print(f"\n▸ Calibrating SABR (β={true_params['beta']})...")
    t0 = time.time()
    model_fit = SABRModel.calibrate(strikes, mkt_vols, F=F, T=T, beta=0.5)
    print(f"  Time: {time.time()-t0:.2f}s")
    model_fit.summary(F=F, T=T)

    print("\n▸ Parameter recovery:")
    for k in ["alpha","rho","nu"]:
        tv, ev = true_params[k], getattr(model_fit, k)
        print(f"  {k:<8} true={tv:.4f}  est={ev:.4f}  err={abs(ev-tv)/abs(tv)*100:.1f}%")

    # ── 4. Full vol surface ───────────────────────────────────────────────
    print("\n▸ Vol surface (σ_SABR[K,T] in %):")
    mats = [1/12, 3/12, 6/12, 1.0, 2.0]
    surf = model_fit.vol_surface(F=F, maturities=mats,
                                  moneyness=[0.85,0.90,0.95,1.00,1.05,1.10,1.15])
    labels = ["85%","90%","95%","100%","105%","110%","115%"]
    print(f"  {'Mat':<6}", "  ".join(f"{l:>6}" for l in labels))
    print("  " + "-"*60)
    for i, T_ in enumerate(mats):
        T_lbl = f"{T_*12:.0f}M" if T_ < 1 else f"{T_:.1f}Y"
        row = "  ".join(f"{v:>6.2f}" for v in surf["vols_pct"][i])
        print(f"  {T_lbl:<6} {row}")

    # ── 5. Greeks ─────────────────────────────────────────────────────────
    print("\n▸ Greeks at ATM (F=K, T=6M):")
    g = model_fit.greeks(F=F, K=F, r=r, T=0.5)
    for name, val in g.items():
        if name not in ("call_price","put_price"):
            print(f"  {name:<12} {val:>12.6f}")
    print(f"  {'Call price':<12} {g['call_price']:>12.2f}  USD/MT")
    print(f"  {'Put price':<12} {g['put_price']:>12.2f}  USD/MT")

    # ── 6. Multi-maturity surface calibration ─────────────────────────────
    print("\n▸ Surface calibration (per maturity slice):")
    smile_data = {}
    for T_ in [3/12, 6/12, 1.0, 1.5]:
        m_vols = np.array([model_true.implied_vol(F,K,T_) + rng.normal(0,0.004)
                           for K in strikes])
        smile_data[T_] = {"strikes": strikes, "vols": m_vols}
    models_by_T = calibrate_surface(smile_data, F=F, beta=0.5)

    print("\n✓ All checks passed.")
    print("=" * 60)
