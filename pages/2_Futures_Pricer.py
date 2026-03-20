from __future__ import annotations
"""pages/2_Futures_Pricer.py — QCEX v4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from theme import LEGEND, CSS, BG, BG2, BG3, ACC, GOLD, TEXT, TEXT2, BORD, GRID, PLOTLY, ax, footer
from data.fetcher import compute_stats, build_term_structure, TICKERS
from models.schwartz_smith import simulate_paths, half_life

st.set_page_config(page_title="QCEX · Futures Pricer", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

PRESETS = {
    "cocoa":   dict(kappa=0.80,mu_xi=0.03,sigma_chi=0.38,sigma_xi=0.18,rho=-0.25,lambda_chi=-0.10,lambda_xi=-0.05,r=0.053,u=0.025),
    "gas":     dict(kappa=2.10,mu_xi=0.00,sigma_chi=0.55,sigma_xi=0.22,rho=-0.15,lambda_chi=-0.08,lambda_xi=-0.03,r=0.038,u=0.015),
    "uranium": dict(kappa=0.30,mu_xi=0.05,sigma_chi=0.28,sigma_xi=0.15,rho=-0.10,lambda_chi=-0.05,lambda_xi=-0.02,r=0.053,u=0.008),
}

with st.sidebar:
    st.markdown(f"<div style='color:{GOLD};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>FUTURES PRICER</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", ["cocoa","gas","uranium"], format_func=lambda x: TICKERS[x]["name"])
    p = PRESETS[commodity]
    st.markdown("---")
    kappa      = st.slider("κ  mean-rev speed",   0.1,  5.0,  float(p["kappa"]),   0.05)
    mu_xi      = st.slider("μξ long-term drift",  -0.2,  0.2,  float(p["mu_xi"]),   0.01)
    sigma_chi  = st.slider("σχ short-term vol",    0.05, 1.5,  float(p["sigma_chi"]),0.01)
    sigma_xi   = st.slider("σξ long-term vol",     0.02, 0.8,  float(p["sigma_xi"]), 0.01)
    rho_ss     = st.slider("ρ  correlation",       -0.95, 0.95, float(p["rho"]),    0.05)
    lambda_chi = st.slider("λχ S-T risk premium", -1.0,  1.0,  float(p["lambda_chi"]),0.01)
    lambda_xi  = st.slider("λξ L-T risk premium", -0.5,  0.5,  float(p["lambda_xi"]), 0.01)
    r_rate     = st.slider("r  risk-free",          0.0,  0.10, float(p["r"]),      0.005)
    u_cost     = st.slider("u  storage cost",       0.0,  0.05, float(p["u"]),      0.001)

params = dict(kappa=kappa,mu_xi=mu_xi,sigma_chi=sigma_chi,sigma_xi=sigma_xi,
              rho=rho_ss,lambda_chi=lambda_chi,lambda_xi=lambda_xi)

@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats = load(commodity)
spot  = stats["spot"]
unit  = TICKERS[commodity]["unit"]
hl    = half_life(kappa)

st.markdown("## FUTURES PRICER — SCHWARTZ-SMITH 2-FACTOR")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Spot",          f"{spot:,.2f} {unit}")
c2.metric("Half-life χ",   f"{hl*12:.1f} meses", f"κ = {kappa:.2f}")
c3.metric("Short-term vol σχ",  f"{sigma_chi*100:.0f}%")
c4.metric("Long-term vol σξ",  f"{sigma_xi*100:.0f}%")
c5.metric("Correlation ρ", f"{rho_ss:.2f}")
st.markdown("---")

ts = build_term_structure(spot, r_rate, u_cost, kappa, np.log(spot), sigma_chi, lambda_chi)
contango = ts["futures"].iloc[-1] > ts["futures"].iloc[0]
slabel = "▲ CONTANGO" if contango else "▼ BACKWARDATION"
scolor = "#FF9944" if contango else ACC

col_chart, col_table = st.columns([2, 1])

with col_chart:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>FUTURES CURVE &nbsp;<span style='color:{scolor};'>{slabel}</span></div>", unsafe_allow_html=True)
    fig = make_subplots(rows=2, cols=1, row_heights=[0.65,0.35], shared_xaxes=True, vertical_spacing=0.08)
    fig.add_trace(go.Scatter(x=ts["label"], y=ts["futures"], name="Futures",
        mode="lines+markers", line=dict(color=GOLD, width=2.5),
        marker=dict(size=7, color=GOLD)), row=1, col=1)
    fig.add_hline(y=spot, line_dash="dot", line_color=BORD, row=1, col=1)
    bar_colors = [ACC if v >= 0 else "#FF4455" for v in ts["cy"]]
    fig.add_trace(go.Bar(x=ts["label"], y=ts["cy"], name="Conv. Yield %",
        marker_color=bar_colors, opacity=0.85), row=2, col=1)
    fig.add_hline(y=0, line_color=BORD, row=2, col=1)
    fig.update_layout(**PLOTLY, height=400, showlegend=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title_text=unit, row=1, col=1)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title_text="CY (%)", row=2, col=1)
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>TERM STRUCTURE</div>", unsafe_allow_html=True)
    display = ts[["label","futures","basis","cy"]].copy()
    display.columns = ["Maturity","Futures","Basis","CY (%)"]
    display["Futures"] = display["Futures"].apply(lambda x: f"{x:,.2f}")
    display["Basis"]   = display["Basis"].apply(lambda x: f"{x:+,.2f}")
    display["CY (%)"]  = display["CY (%)"].apply(lambda x: f"{x:+.3f}%")
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.markdown(f"""
    <div style="background:{BG3};border:1px solid {BORD};border-left:3px solid {GOLD};
      padding:10px 14px;border-radius:0 4px 4px 0;margin-top:12px;font-size:9px;color:{TEXT2};">
      <div style="color:{GOLD};font-size:8px;letter-spacing:1px;margin-bottom:6px;">MODELO</div>
      ln F(t,T) = e<sup>-&kappa;&tau;</sup>&chi; + &xi; + A(&tau;)<br>
      Half-life &chi; = <strong style="color:{GOLD};">{hl*12:.1f} meses</strong><br>
      CY = r + u &minus; (1/T)&middot;ln(F/S)
    </div>""", unsafe_allow_html=True)

# ── Monte Carlo ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>MONTE CARLO SIMULATION</div>", unsafe_allow_html=True)

col_mc, col_ctrl = st.columns([3, 1])
with col_ctrl:
    n_paths = st.select_slider("Paths", [100,500,1000], value=500)
    horizon = st.slider("Horizon (years)", 0.5, 3.0, 1.0, 0.25)

with col_mc:
    try:
        xi0  = np.log(max(spot, 0.01))
        sim  = simulate_paths(params, 0.0, xi0, T_years=horizon, dt=1/52,
                              n_paths=min(n_paths, 1000), seed=42)
        pcts = np.percentile(sim["spot"], [5,25,50,75,95], axis=0)
        t    = sim["times"]

        r, g_val, b = int(GOLD[1:3],16), int(GOLD[3:5],16), int(GOLD[5:7],16)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=t, y=pcts[4], line=dict(color=f"rgba({r},{g_val},{b},0.25)", width=1), showlegend=False))
        fig2.add_trace(go.Scatter(x=t, y=pcts[0], fill="tonexty", name="5–95%",
            fillcolor=f"rgba({r},{g_val},{b},0.08)", line=dict(color=f"rgba({r},{g_val},{b},0.25)", width=1)))
        fig2.add_trace(go.Scatter(x=t, y=pcts[3], line=dict(color=f"rgba({r},{g_val},{b},0.5)", width=1), showlegend=False))
        fig2.add_trace(go.Scatter(x=t, y=pcts[1], fill="tonexty", name="25–75%",
            fillcolor=f"rgba({r},{g_val},{b},0.15)", line=dict(color=f"rgba({r},{g_val},{b},0.5)", width=1)))
        fig2.add_trace(go.Scatter(x=t, y=pcts[2], name="Mediana",
            line=dict(color=GOLD, width=2)))
        fig2.add_hline(y=np.exp(xi0), line_dash="dash", line_color=BORD,
            annotation_text="Equil. L-T")
        fig2.update_layout(**PLOTLY, height=280,
            xaxis=ax("Años"), yaxis=ax(unit))
        st.plotly_chart(fig2, use_container_width=True)

        S_T = sim["spot"][:, -1]
        stat_cols = st.columns(5)
        for col, (lbl, val) in zip(stat_cols, [
            ("E[S_T]",  f"{np.mean(S_T):,.1f}"),
            ("Median",  f"{np.median(S_T):,.1f}"),
            ("Std",     f"{np.std(S_T):,.1f}"),
            ("P5",      f"{np.percentile(S_T,5):,.1f}"),
            ("P95",     f"{np.percentile(S_T,95):,.1f}"),
        ]):
            with col:
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORD};padding:10px;'
                    f'border-radius:4px;text-align:center;">'
                    f'<div style="color:{TEXT2};font-size:8px;letter-spacing:1px;">{lbl}</div>'
                    f'<div style="color:{GOLD};font-size:14px;font-weight:600;margin-top:4px;">{val}</div>'
                    f'</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en Monte Carlo: {e}")

st.markdown(footer("Futures Pricer"), unsafe_allow_html=True)
