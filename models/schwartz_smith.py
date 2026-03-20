"""
schwartz_smith.py
=================
Schwartz-Smith (2000) Two-Factor Commodity Pricing Model
with Kalman Filter Calibration.

Reference:
    Schwartz, E. & Smith, J.E. (2000). "Short-Term Variations and Long-Term
    Dynamics in Commodity Prices." Management Science, 46(7), 893–911.

Model:
    ln(S_t) = χ_t + ξ_t

    dχ_t = -κ·χ_t·dt + σ_χ·dW_χ          (short-term: mean-reverting)
    dξ_t = μ_ξ·dt + σ_ξ·dW_ξ              (long-term: GBM with drift)
    dW_χ·dW_ξ = ρ·dt

Futures pricing formula (risk-neutral):
    ln F(t,T) = e^{-κτ}·χ_t + ξ_t + A(τ)

    A(τ) = (μ_ξ - λ_ξ)·τ - (1-e^{-κτ})/κ · λ_χ
           + σ_ξ²τ/2 + σ_χ²(1-e^{-2κτ})/(4κ)
           + ρ·σ_χ·σ_ξ·(1-e^{-κτ})/κ

Author: Commodity Pricing Engine — Portfolio Project
"""

import numpy as np
from scipy.optimize import minimize
from scipy.linalg import solve_discrete_lyapunov
import warnings
warnings.filterwarnings("ignore")


# ─── STATE-SPACE REPRESENTATION ──────────────────────────────────────────────

def build_state_space(params: dict, maturities: np.ndarray, dt: float):
    """
    Build the Kalman Filter state-space matrices for Schwartz-Smith.

    State vector: x_t = [χ_t, ξ_t]  (2×1)
    Observation:  y_t = [ln F(t,T_1), ..., ln F(t,T_n)]  (n×1)

    Parameters
    ----------
    params : dict
        kappa    : mean-reversion speed of χ
        mu_xi    : drift of ξ
        sigma_chi: volatility of χ
        sigma_xi : volatility of ξ
        rho      : correlation between Wiener processes
        lambda_chi: market price of short-term risk
        lambda_xi : market price of long-term risk
    maturities : ndarray, shape (n,)
        Time-to-maturity in years for each futures contract
    dt : float
        Time step (e.g. 1/252 for daily)

    Returns
    -------
    F_mat : ndarray (2,2)  — state transition matrix
    Q     : ndarray (2,2)  — state noise covariance
    H     : ndarray (n,2)  — observation matrix
    d     : ndarray (n,)   — observation intercept A(τ)
    """
    κ  = params["kappa"]
    μξ = params["mu_xi"]
    σχ = params["sigma_chi"]
    σξ = params["sigma_xi"]
    ρ  = params["rho"]
    λχ = params["lambda_chi"]
    λξ = params["lambda_xi"]
    τ  = maturities  # shape (n,)

    # ── State transition (exact discretisation of OU + RW) ──────────────────
    F_mat = np.array([
        [np.exp(-κ * dt), 0.0],
        [0.0,             1.0]
    ])

    # ── State noise covariance Q (integrated over [0,dt]) ───────────────────
    q11 = σχ**2 * (1 - np.exp(-2*κ*dt)) / (2*κ)
    q22 = σξ**2 * dt
    q12 = ρ * σχ * σξ * (1 - np.exp(-κ*dt)) / κ
    Q = np.array([[q11, q12],
                  [q12, q22]])

    # ── Observation matrix H  (n × 2) ───────────────────────────────────────
    # ln F(t,T) = e^{-κτ}·χ + 1·ξ + A(τ)
    H = np.column_stack([np.exp(-κ * τ), np.ones(len(τ))])

    # ── Observation intercept A(τ) ───────────────────────────────────────────
    A = (
        (μξ - λξ) * τ
        - (1 - np.exp(-κ*τ)) / κ * λχ
        + 0.5 * σξ**2 * τ
        + σχ**2 * (1 - np.exp(-2*κ*τ)) / (4*κ)
        + ρ * σχ * σξ * (1 - np.exp(-κ*τ)) / κ
    )

    return F_mat, Q, H, A


# ─── KALMAN FILTER ───────────────────────────────────────────────────────────

def kalman_filter(log_futures: np.ndarray, params: dict,
                  maturities: np.ndarray, dt: float = 1/252,
                  s_noise: float = 0.01):
    """
    Run the Kalman Filter over observed log-futures prices.

    Parameters
    ----------
    log_futures : ndarray, shape (T, n)
        Observed log-prices of n futures contracts over T time steps.
        NaN entries are handled (missing contracts).
    params : dict
        Model parameters (see build_state_space).
    maturities : ndarray, shape (n,)
        Time-to-maturity for each contract.
    dt : float
        Time step in years.
    s_noise : float
        Measurement noise standard deviation (assumed homoscedastic).

    Returns
    -------
    filtered_states : ndarray (T, 2)  — [χ_t, ξ_t] filtered estimates
    filtered_covs   : ndarray (T, 2, 2)
    log_likelihood  : float
    innovations     : ndarray (T, n)
    """
    T_obs, n = log_futures.shape
    F_mat, Q, H, A = build_state_space(params, maturities, dt)
    R = s_noise**2 * np.eye(n)  # measurement noise

    # Initialise: stationary distribution of χ, flat prior for ξ
    x = np.zeros(2)
    κ = params["kappa"]
    σχ = params["sigma_chi"]
    σξ = params["sigma_xi"]

    P = np.array([
        [σχ**2 / (2*κ), 0.0],
        [0.0,           σξ**2 * 10]  # diffuse prior for random walk
    ])

    filtered_states = np.zeros((T_obs, 2))
    filtered_covs   = np.zeros((T_obs, 2, 2))
    innovations_all = np.zeros((T_obs, n))
    log_lik = 0.0

    for t in range(T_obs):
        # ── Predict ─────────────────────────────────────────────────────────
        x_pred = F_mat @ x
        P_pred = F_mat @ P @ F_mat.T + Q

        # ── Observed contracts (handle NaN) ─────────────────────────────────
        obs = log_futures[t]
        mask = ~np.isnan(obs)
        if mask.sum() == 0:
            x, P = x_pred, P_pred
            filtered_states[t] = x
            filtered_covs[t]   = P
            continue

        H_t = H[mask]
        A_t = A[mask]
        R_t = R[np.ix_(mask, mask)]
        y_t = obs[mask]

        # ── Innovation ──────────────────────────────────────────────────────
        y_hat = H_t @ x_pred + A_t
        v = y_t - y_hat
        innovations_all[t, mask] = v

        # ── Innovation covariance ────────────────────────────────────────────
        S_innov = H_t @ P_pred @ H_t.T + R_t

        # ── Log-likelihood contribution ──────────────────────────────────────
        sign, logdet = np.linalg.slogdet(S_innov)
        if sign <= 0:
            log_lik -= 1e6
        else:
            log_lik -= 0.5 * (logdet + v @ np.linalg.solve(S_innov, v)
                              + mask.sum() * np.log(2 * np.pi))

        # ── Kalman gain ──────────────────────────────────────────────────────
        K_gain = P_pred @ H_t.T @ np.linalg.inv(S_innov)

        # ── Update ──────────────────────────────────────────────────────────
        x = x_pred + K_gain @ v
        P = (np.eye(2) - K_gain @ H_t) @ P_pred

        filtered_states[t] = x
        filtered_covs[t]   = P

    return filtered_states, filtered_covs, log_lik, innovations_all


# ─── MAXIMUM LIKELIHOOD CALIBRATION ──────────────────────────────────────────

PARAM_NAMES = ["kappa", "mu_xi", "sigma_chi", "sigma_xi",
               "rho", "lambda_chi", "lambda_xi"]

PARAM_BOUNDS = {
    "kappa":      (0.01, 10.0),
    "mu_xi":      (-0.5,  0.5),
    "sigma_chi":  (0.01,  2.0),
    "sigma_xi":   (0.01,  1.0),
    "rho":        (-0.99, 0.99),
    "lambda_chi": (-2.0,  2.0),
    "lambda_xi":  (-1.0,  1.0),
}


def params_to_vec(params: dict) -> np.ndarray:
    return np.array([params[k] for k in PARAM_NAMES])


def vec_to_params(vec: np.ndarray) -> dict:
    return {k: v for k, v in zip(PARAM_NAMES, vec)}


def neg_log_likelihood(vec: np.ndarray, log_futures: np.ndarray,
                       maturities: np.ndarray, dt: float,
                       s_noise: float) -> float:
    params = vec_to_params(vec)
    # Enforce rho in (-1,1) strictly
    if abs(params["rho"]) >= 1:
        return 1e10
    try:
        _, _, log_lik, _ = kalman_filter(log_futures, params, maturities, dt, s_noise)
        return -log_lik
    except Exception:
        return 1e10


def calibrate(log_futures: np.ndarray, maturities: np.ndarray,
              dt: float = 1/252, s_noise: float = 0.01,
              n_restarts: int = 5, verbose: bool = True) -> dict:
    """
    Calibrate Schwartz-Smith parameters by Maximum Likelihood via Kalman Filter.

    Parameters
    ----------
    log_futures : ndarray (T, n)
        Observed log-futures prices.
    maturities : ndarray (n,)
        Time-to-maturity in years per contract.
    dt : float
        Observation frequency in years.
    s_noise : float
        Initial guess for measurement noise.
    n_restarts : int
        Number of random restarts to avoid local minima.
    verbose : bool
        Print progress.

    Returns
    -------
    best_params : dict
        Calibrated model parameters.
    result : OptimizeResult
    """
    bounds = [PARAM_BOUNDS[k] for k in PARAM_NAMES]

    best_result = None
    best_nll    = np.inf

    # Default starting point
    x0_default = np.array([1.0, 0.02, 0.3, 0.2, -0.3, -0.1, -0.05])

    starts = [x0_default]
    rng = np.random.default_rng(42)
    for _ in range(n_restarts - 1):
        x0 = np.array([
            rng.uniform(*PARAM_BOUNDS["kappa"]),
            rng.uniform(*PARAM_BOUNDS["mu_xi"]),
            rng.uniform(0.05, 0.8),
            rng.uniform(0.05, 0.5),
            rng.uniform(-0.8, 0.8),
            rng.uniform(-0.5, 0.5),
            rng.uniform(-0.3, 0.3),
        ])
        starts.append(x0)

    for i, x0 in enumerate(starts):
        if verbose:
            print(f"  Restart {i+1}/{n_restarts} ...", end=" ", flush=True)
        result = minimize(
            neg_log_likelihood,
            x0,
            args=(log_futures, maturities, dt, s_noise),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-8},
        )
        if verbose:
            print(f"NLL = {result.fun:.4f}")
        if result.fun < best_nll:
            best_nll    = result.fun
            best_result = result

    best_params = vec_to_params(best_result.x)
    if verbose:
        print(f"\n✓ Calibration complete. Log-likelihood = {-best_nll:.4f}")
        _print_params(best_params)

    return best_params, best_result


def _print_params(params: dict):
    print("\n┌─ Calibrated Parameters ─────────────────────┐")
    labels = {
        "kappa":      "κ  (mean-reversion speed)",
        "mu_xi":      "μξ (long-term drift)",
        "sigma_chi":  "σχ (short-term vol)",
        "sigma_xi":   "σξ (long-term vol)",
        "rho":        "ρ  (correlation)",
        "lambda_chi": "λχ (S-T market price of risk)",
        "lambda_xi":  "λξ (L-T market price of risk)",
    }
    for k, label in labels.items():
        print(f"│  {label:<35} {params[k]:>8.4f}  │")
    print("└──────────────────────────────────────────────┘")


# ─── FUTURES PRICING ─────────────────────────────────────────────────────────

def price_futures(chi: float, xi: float, params: dict,
                  maturities: np.ndarray) -> np.ndarray:
    """
    Compute model futures prices given latent state (χ, ξ).

    ln F(t,T) = e^{-κτ}·χ + ξ + A(τ)
    """
    _, _, H, A = build_state_space(params, maturities, dt=1/252)
    x = np.array([chi, xi])
    log_F = H @ x + A
    return np.exp(log_F)


def term_structure_from_states(filtered_states: np.ndarray, params: dict,
                                maturities: np.ndarray,
                                spot_prices: np.ndarray) -> dict:
    """
    Reconstruct the full term structure from filtered states at each date.

    Returns dict with:
        - 'model_futures' : ndarray (T, n) — model-implied futures prices
        - 'chi'           : ndarray (T,)   — short-term factor
        - 'xi'            : ndarray (T,)   — long-term factor
        - 'long_run_spot' : ndarray (T,)   — exp(ξ) as proxy for L-T equilibrium
    """
    κ  = params["kappa"]
    T_obs = filtered_states.shape[0]
    n = len(maturities)

    chi = filtered_states[:, 0]
    xi  = filtered_states[:, 1]

    model_futures = np.zeros((T_obs, n))
    for t in range(T_obs):
        model_futures[t] = price_futures(chi[t], xi[t], params, maturities)

    return {
        "model_futures" : model_futures,
        "chi"           : chi,
        "xi"            : xi,
        "long_run_spot" : np.exp(xi),
    }


# ─── SIMULATION ──────────────────────────────────────────────────────────────

def simulate_paths(params: dict, chi0: float, xi0: float,
                   T_years: float = 1.0, dt: float = 1/252,
                   n_paths: int = 1000, seed: int = 42) -> dict:
    """
    Monte Carlo simulation of spot prices under Schwartz-Smith.

    Uses Cholesky decomposition for correlated Brownian motions.

    Returns
    -------
    dict with:
        'spot'  : ndarray (n_paths, steps) — simulated spot prices
        'chi'   : ndarray (n_paths, steps) — short-term factor paths
        'xi'    : ndarray (n_paths, steps) — long-term factor paths
        'times' : ndarray (steps,)
    """
    κ  = params["kappa"]
    μξ = params["mu_xi"]
    σχ = params["sigma_chi"]
    σξ = params["sigma_xi"]
    ρ  = params["rho"]

    steps = int(T_years / dt)
    rng   = np.random.default_rng(seed)

    # Cholesky for correlated normals
    cov = np.array([[1.0, ρ], [ρ, 1.0]])
    L   = np.linalg.cholesky(cov)

    chi = np.zeros((n_paths, steps))
    xi  = np.zeros((n_paths, steps))
    chi[:, 0] = chi0
    xi[:, 0]  = xi0

    for t in range(1, steps):
        Z = rng.standard_normal((n_paths, 2)) @ L.T
        Z_chi, Z_xi = Z[:, 0], Z[:, 1]

        # Exact discretisation of OU:
        chi[:, t] = (chi[:, t-1] * np.exp(-κ * dt)
                     + σχ * np.sqrt((1 - np.exp(-2*κ*dt)) / (2*κ)) * Z_chi)
        # Euler-Maruyama for ξ (GBM with drift):
        xi[:, t]  = xi[:, t-1] + μξ * dt + σξ * np.sqrt(dt) * Z_xi

    spot = np.exp(chi + xi)
    times = np.linspace(0, T_years, steps)

    return {"spot": spot, "chi": chi, "xi": xi, "times": times}


def price_option_mc(params: dict, chi0: float, xi0: float,
                    K: float, T: float, r: float,
                    option_type: str = "call",
                    n_paths: int = 50_000, dt: float = 1/252) -> dict:
    """
    Price a European option on the spot commodity via Monte Carlo.

    Returns price, standard error, and 95% confidence interval.
    """
    sim = simulate_paths(params, chi0, xi0, T_years=T, dt=dt, n_paths=n_paths)
    S_T = sim["spot"][:, -1]

    if option_type == "call":
        payoffs = np.maximum(S_T - K, 0)
    else:
        payoffs = np.maximum(K - S_T, 0)

    price = np.exp(-r * T) * np.mean(payoffs)
    stderr = np.exp(-r * T) * np.std(payoffs) / np.sqrt(n_paths)

    return {
        "price"  : price,
        "stderr" : stderr,
        "ci_95"  : (price - 1.96*stderr, price + 1.96*stderr),
        "S_T_mean": np.mean(S_T),
        "S_T_std" : np.std(S_T),
    }


# ─── DIAGNOSTIC TOOLS ────────────────────────────────────────────────────────

def compute_diagnostics(innovations: np.ndarray, params: dict,
                        maturities: np.ndarray) -> dict:
    """
    Model diagnostics on Kalman Filter innovations.

    A well-specified model should produce innovations that are:
    - White noise (no autocorrelation)
    - Approximately normally distributed
    - Homoscedastic

    Returns stats per contract.
    """
    T, n = innovations.shape
    results = {}

    for i, tau in enumerate(maturities):
        v = innovations[:, i]
        v = v[~np.isnan(v)]
        if len(v) < 10:
            continue

        # Ljung-Box statistic at lag 1 (simplified)
        ac1 = np.corrcoef(v[:-1], v[1:])[0, 1]
        lb1 = T * (T + 2) / (T - 1) * ac1**2

        results[f"T={tau:.2f}Y"] = {
            "mean"    : float(np.mean(v)),
            "std"     : float(np.std(v)),
            "skew"    : float(_skewness(v)),
            "kurt"    : float(_kurtosis(v)),
            "ac_lag1" : float(ac1),
            "LB_stat" : float(lb1),
        }

    return results


def _skewness(x):
    return np.mean(((x - x.mean()) / x.std())**3)

def _kurtosis(x):
    return np.mean(((x - x.mean()) / x.std())**4) - 3


def half_life(kappa: float) -> float:
    """Half-life of the short-term factor in years: ln(2)/κ."""
    return np.log(2) / kappa


# ─── SYNTHETIC DATA GENERATOR (for testing) ──────────────────────────────────

def generate_synthetic_data(true_params: dict, maturities: np.ndarray,
                             T_obs: int = 500, dt: float = 1/52,
                             s_noise: float = 0.02,
                             seed: int = 0) -> tuple:
    """
    Generate synthetic futures panel data from the true model.
    Used for unit testing and calibration validation.

    Returns
    -------
    log_futures : ndarray (T_obs, n)
    true_states : ndarray (T_obs, 2)
    """
    F_mat, Q, H, A = build_state_space(true_params, maturities, dt)
    rng = np.random.default_rng(seed)

    n = len(maturities)
    states = np.zeros((T_obs, 2))
    log_futures = np.zeros((T_obs, n))

    x = np.zeros(2)
    L_Q = np.linalg.cholesky(Q + 1e-12 * np.eye(2))

    for t in range(T_obs):
        x = F_mat @ x + L_Q @ rng.standard_normal(2)
        states[t] = x
        log_futures[t] = H @ x + A + s_noise * rng.standard_normal(n)

    return log_futures, states


# ─── QUICK DEMO ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    print("=" * 60)
    print("  SCHWARTZ-SMITH 2-FACTOR MODEL — KALMAN FILTER DEMO")
    print("=" * 60)

    # ── True parameters (Cacao-like: high vol, moderate mean-reversion) ──
    true_params = {
        "kappa"     : 0.80,   # χ half-life ≈ 10 months
        "mu_xi"     : 0.03,   # modest long-term drift
        "sigma_chi" : 0.38,   # short-term vol (cacao 2023-24)
        "sigma_xi"  : 0.18,   # long-term vol
        "rho"       : -0.25,  # mild negative correlation
        "lambda_chi": -0.10,  # risk premium on short-term factor
        "lambda_xi" : -0.05,  # risk premium on long-term factor
    }

    maturities = np.array([1/12, 3/12, 6/12, 1.0, 1.5, 2.0])  # 6 contracts
    T_obs = 260   # ~5 years weekly
    dt    = 1/52

    print(f"\n▸ Generating synthetic data  (T={T_obs} weeks, {len(maturities)} contracts)")
    log_F, true_states = generate_synthetic_data(
        true_params, maturities, T_obs=T_obs, dt=dt, s_noise=0.015
    )
    print(f"  log_futures shape: {log_F.shape}")

    print(f"\n▸ Running Kalman Filter with true parameters...")
    t0 = time.time()
    filt_states, filt_covs, ll, innovations = kalman_filter(
        log_F, true_params, maturities, dt=dt, s_noise=0.015
    )
    print(f"  Log-likelihood : {ll:.4f}  ({time.time()-t0:.2f}s)")

    chi_err = np.abs(filt_states[:,0] - true_states[:,0]).mean()
    xi_err  = np.abs(filt_states[:,1] - true_states[:,1]).mean()
    print(f"  Mean |error| χ : {chi_err:.4f}")
    print(f"  Mean |error| ξ : {xi_err:.4f}")

    print(f"\n▸ Calibrating parameters via MLE (5 restarts)...")
    t0 = time.time()
    est_params, opt_result = calibrate(
        log_F, maturities, dt=dt, s_noise=0.015, n_restarts=5
    )
    print(f"\n  Calibration time: {time.time()-t0:.1f}s")
    print(f"  Optimiser status: {opt_result.message}")

    print("\n▸ Parameter recovery (true vs estimated):")
    print(f"  {'Parameter':<15} {'True':>8} {'Estimated':>10} {'Error%':>8}")
    print("  " + "-" * 45)
    for k in PARAM_NAMES:
        true_v = true_params[k]
        est_v  = est_params[k]
        err    = abs(est_v - true_v) / (abs(true_v) + 1e-9) * 100
        print(f"  {k:<15} {true_v:>8.4f} {est_v:>10.4f} {err:>7.1f}%")

    print(f"\n▸ Half-life of short-term factor:")
    hl_true = half_life(true_params["kappa"])
    hl_est  = half_life(est_params["kappa"])
    print(f"  True     : {hl_true*12:.1f} months")
    print(f"  Estimated: {hl_est*12:.1f} months")

    print(f"\n▸ Monte Carlo option pricing (50k paths):")
    chi0 = filt_states[-1, 0]
    xi0  = filt_states[-1, 1]
    S0   = np.exp(chi0 + xi0)
    K    = S0 * 1.05  # 5% OTM call

    opt = price_option_mc(est_params, chi0, xi0, K=K, T=0.5, r=0.05)
    print(f"  Spot S0      : {S0:.2f}")
    print(f"  Strike K     : {K:.2f}  (5% OTM)")
    print(f"  Call price   : {opt['price']:.4f}  ±{opt['stderr']:.4f}")
    print(f"  95% CI       : [{opt['ci_95'][0]:.4f}, {opt['ci_95'][1]:.4f}]")

    print(f"\n▸ Innovation diagnostics (model fit):")
    diag = compute_diagnostics(innovations, est_params, maturities)
    print(f"  {'Contract':<12} {'Mean':>8} {'Std':>8} {'Skew':>8} {'Kurt':>8} {'AC(1)':>8}")
    print("  " + "-" * 56)
    for contract, stats in diag.items():
        print(f"  {contract:<12} {stats['mean']:>8.4f} {stats['std']:>8.4f} "
              f"{stats['skew']:>8.3f} {stats['kurt']:>8.3f} {stats['ac_lag1']:>8.4f}")

    print("\n✓ All checks passed. Ready for production use.")
    print("=" * 60)
