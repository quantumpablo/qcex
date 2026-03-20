"""
app/pages/2_Futures_Pricer.py
=============================
Futures pricing via Schwartz-Smith 2-factor model.
Interactive term structure, convenience yield, contango/backwardation analysis.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import fetch_prices, compute_stats, build_term_structure, TICKERS
from models.schwartz_smith import (
    generate_synthetic_data, kalman_filter, price_futures, half_life,
    PARAM_NAMES
)

st.set_page_config(page_title="QCEX · Futures Pricer", page_icon="◈", layout="wide")
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{font-family:'IBM Plex Mono',monospace!important;background:#07090d;color:#b8ccb8}
  .stApp{background:#07090d}
  section[data-testid="stSidebar"]{background:#070c0a;border-right:1px solid #0f1f0f}
  h1,h2,h3{color:#f5d060!important;font-family:'IBM Plex Mono',monospace!important}
  [data-testid="metric-container"]{background:#070c07;border:1px solid #0f1f0f;border-radius:4px;padding:8px 12px}
  [data-testid="metric-container"] label{color:#3a3a1a!important;font-size:10px}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{color:#f5d060!important}
  .eq-box{background:#100e00;border-left:3px solid #f5d060;padding:8px 14px;font-size:11px;color:#f5d060;margin:6px 0;border-radius:0 4px 4px 0}
</style>""", unsafe_allow_html=True)

LAYOUT = dict(
    paper_bgcolor="#07090d", plot_bgcolor="#07090d",
    font=dict(family="IBM Plex Mono", color="#3a3a1a", size=10),
    xaxis=dict(gridcolor="#100e00"), yaxis=dict(gridcolor="#100e00"),
    margin=dict(l=50, r=20, t=30, b=40),
)

# ── Preset parameters (calibrated) ────────────────────────────────────────────
PRESETS = {
    "cocoa": dict(kappa=0.80, mu_xi=0.03, sigma_chi=0.38, sigma_xi=0.18,
                  rho=-0.25, lambda_chi=-0.10, lambda_xi=-0.05, r=0.053, u=0.025),
    "gas":   dict(kappa=2.10, mu_xi=0.00, sigma_chi=0.55, sigma_xi=0.22,
                  rho=-0.15, lambda_chi=-0.08, lambda_xi=-0.03, r=0.038, u=0.015),
    "uranium":dict(kappa=0.30, mu_xi=0.05, sigma_chi=0.28, sigma_xi=0.15,
                   rho=-0.10, lambda_chi=-0.05, lambda_xi=-0.02, r=0.053, u=0.008),
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='color:#a0800a;font-size:9px;letter-spacing:2px;margin-bottom:8px'>FUTURES PRICER</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", ["cocoa","gas","uranium"],
                              format_func=lambda x: TICKERS[x]["name"])
    st.markdown("---")
    st.markdown("<div style='color:#a0800a;font-size:9px;letter-spacing:1px;margin-bottom:6px'>SCHWARTZ-SMITH PARAMS</div>", unsafe_allow_html=True)
    p = PRESETS[commodity].copy()
    kappa     = st.slider("κ  (mean-rev speed)",  0.1, 5.0,  float(p["kappa"]),  0.05)
    mu_xi     = st.slider("μξ (long-term drift)", -0.2, 0.2,  float(p["mu_xi"]),  0.01)
    sigma_chi = st.slider("σχ (short-term vol)",   0.05, 1.5,  float(p["sigma_chi"]), 0.01)
    sigma_xi  = st.slider("σξ (long-term vol)",    0.02, 0.8,  float(p["sigma_xi"]),  0.01)
    rho_ss    = st.slider("ρ  (correlation)",      -0.95, 0.95, float(p["rho"]),   0.05)
    lambda_chi= st.slider("λχ (S-T risk prem.)",  -1.0, 1.0,  float(p["lambda_chi"]), 0.01)
    lambda_xi = st.slider("λξ (L-T risk prem.)",  -0.5, 0.5,  float(p["lambda_xi"]),  0.01)
    r_rate    = st.slider("r  (risk-free rate)",    0.0, 0.10, float(p["r"]),  0.005)
    u_cost    = st.slider("u  (storage cost)",      0.0, 0.05, float(p["u"]),  0.001)

params = dict(kappa=kappa, mu_xi=mu_xi, sigma_chi=sigma_chi, sigma_xi=sigma_xi,
              rho=rho_ss, lambda_chi=lambda_chi, lambda_xi=lambda_xi)

# ── Load spot ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats   = load(commodity)
spot    = stats["spot"]
unit    = TICKERS[commodity]["unit"]
hl      = half_life(kappa)

st.markdown("## 📈 FUTURES PRICER — SCHWARTZ-SMITH 2-FACTOR")

# ── Key metrics ────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Spot", f"{spot:,.2f} {unit}")
c2.metric("Half-life χ", f"{hl*12:.1f} meses", f"κ = {kappa:.2f}")
c3.metric("Vol corto plazo", f"{sigma_chi*100:.0f}%")
c4.metric("Vol largo plazo", f"{sigma_xi*100:.0f}%")
c5.metric("Correlación ρ", f"{rho_ss:.2f}")

st.markdown("---")

# ── Build term structure ───────────────────────────────────────────────────────
alpha_lr = np.log(spot)  # long-run mean = current spot (simplification)
ts = build_term_structure(spot, r_rate, u_cost, kappa, alpha_lr,
                           sigma_chi, lambda_chi)
contango = ts["futures"].iloc[-1] > ts["futures"].iloc[0]
structure_label = "▲ CONTANGO" if contango else "▼ BACKWARDATION"
structure_color = "#ff9944" if contango else "#4aff99"

col_chart, col_table = st.columns([2, 1])

with col_chart:
    st.markdown(f"### CURVA DE FUTUROS &nbsp;<span style='color:{structure_color};font-size:12px'>{structure_label}</span>", unsafe_allow_html=True)
    fig = make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35],
                        shared_xaxes=True, vertical_spacing=0.08)
    # Futures curve
    fig.add_trace(go.Scatter(
        x=ts["label"], y=ts["futures"],
        name="Futures (model)", mode="lines+markers",
        line=dict(color="#f5d060", width=2.5),
        marker=dict(size=8, color="#f5d060"),
    ), row=1, col=1)
    fig.add_hline(y=spot, line_dash="dot", line_color="#3a3a1a",
                  annotation_text=f"Spot {spot:.2f}", row=1, col=1)
    # Convenience yield
    fig.add_trace(go.Bar(
        x=ts["label"], y=ts["cy"],
        name="Conv. Yield (%)",
        marker_color=[("#4aff99" if v >= 0 else "#ff5544") for v in ts["cy"]],
        opacity=0.8,
    ), row=2, col=1)
    fig.add_hline(y=0, line_color="#1a1a0a", row=2, col=1)
    fig.update_layout(**LAYOUT, height=420, showlegend=True,
                      legend=dict(bgcolor="#070c07", bordercolor="#1a1a0a"))
    fig.update_yaxes(title_text=unit, row=1, col=1,
                     title_font=dict(color="#3a3a1a", size=9))
    fig.update_yaxes(title_text="CY (%)", row=2, col=1,
                     title_font=dict(color="#3a3a1a", size=9))
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("### TERM STRUCTURE")
    display = ts[["label","futures","basis","cy"]].copy()
    display.columns = ["Maturity","Futures","Basis","CY (%)"]
    display["Futures"] = display["Futures"].apply(lambda x: f"{x:,.2f}")
    display["Basis"]   = display["Basis"].apply(lambda x: f"{x:+,.2f}")
    display["CY (%)"]  = display["CY (%)"].apply(lambda x: f"{x:+.3f}%")
    st.dataframe(display, hide_index=True, use_container_width=True)

    st.markdown(f"""
    <div style='background:#0a0a00;border:1px solid #1a1a0a;border-left:3px solid #f5d060;
      padding:10px;border-radius:0 4px 4px 0;margin-top:12px;font-size:10px'>
      <div style='color:#f5d060;font-size:9px;letter-spacing:1px;margin-bottom:6px'>MODELO</div>
      <div style='color:#3a3a1a;line-height:1.6'>
        ln F(t,T) = e<sup>-κτ</sup>χ + ξ + A(τ)<br>
        Half-life χ = <strong style='color:#f5d060'>{hl*12:.1f} meses</strong><br>
        CY = r + u − (1/T)·ln(F/S)
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Monte Carlo paths ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### SIMULACIÓN MONTE CARLO — PATHS DE PRECIO SPOT")

col_mc, col_params = st.columns([3, 1])
with col_params:
    n_paths = st.select_slider("Número de paths", [100, 500, 1000, 5000], value=500)
    horizon = st.slider("Horizonte (años)", 0.5, 3.0, 1.0, 0.25)

with col_mc:
    from models.schwartz_smith import simulate_paths
    chi0, xi0 = 0.0, np.log(spot)
    sim = simulate_paths(params, chi0, xi0, T_years=horizon, dt=1/52,
                         n_paths=min(n_paths, 1000), seed=42)
    pcts   = np.percentile(sim["spot"], [5, 25, 50, 75, 95], axis=0)
    times  = sim["times"]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=times, y=pcts[4], name="P95",
        line=dict(color="#f5d06044", width=1), showlegend=False))
    fig2.add_trace(go.Scatter(x=times, y=pcts[0], name="5–95%",
        fill="tonexty", fillcolor="#f5d06015",
        line=dict(color="#f5d06044", width=1)))
    fig2.add_trace(go.Scatter(x=times, y=pcts[3], name="P75",
        line=dict(color="#f5d06088", width=1), showlegend=False))
    fig2.add_trace(go.Scatter(x=times, y=pcts[1], name="25–75%",
        fill="tonexty", fillcolor="#f5d06028",
        line=dict(color="#f5d06088", width=1)))
    fig2.add_trace(go.Scatter(x=times, y=pcts[2], name="Mediana",
        line=dict(color="#f5d060", width=2)))
    fig2.add_hline(y=np.exp(xi0), line_dash="dash", line_color="#3a3a1a",
                   annotation_text="Equil. L-T = exp(ξ₀)")
    fig2.update_layout(**LAYOUT, height=300,
                       xaxis_title="Años", yaxis_title=unit)
    st.plotly_chart(fig2, use_container_width=True)

S_T = sim["spot"][:, -1]
st.markdown(f"""
<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:8px'>
  {''.join([f"""<div style='background:#0a0a00;border:1px solid #1a1a0a;padding:10px;border-radius:4px;text-align:center'>
    <div style='color:#3a3a1a;font-size:8px;letter-spacing:1px'>{label}</div>
    <div style='color:#f5d060;font-size:14px;font-weight:600'>{val}</div></div>"""
    for label, val in [
      ("E[S_T]",   f"{np.mean(S_T):,.1f}"),
      ("Median",   f"{np.median(S_T):,.1f}"),
      ("Std",      f"{np.std(S_T):,.1f}"),
      ("P5",       f"{np.percentile(S_T, 5):,.1f}"),
      ("P95",      f"{np.percentile(S_T, 95):,.1f}"),
    ]])}
</div>
""", unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top: 1px solid #0F1F0F; padding-top: 14px; margin-top: 32px;
  display: flex; justify-content: space-between; align-items: center;">
  <div style="color: #4AFF99; font-size: 11px; font-weight: 600; letter-spacing: 2px;">QCEX</div>
  <div style="color: #0F2A0F; font-size: 8px; letter-spacing: 1px;">
    by <strong style="color: #1A3A1A;">QuantumPablo</strong> · Commodity Derivatives · Quant Finance
  </div>
</div>
""", unsafe_allow_html=True)

