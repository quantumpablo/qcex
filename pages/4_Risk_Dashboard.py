"""
app/pages/4_Risk_Dashboard.py
==============================
Risk analytics: Historical VaR/CVaR, vol cone,
stress scenarios, drawdown, tail risk.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import fetch_prices, compute_returns, compute_stats, TICKERS
from analytics.risk import (
    historical_var, historical_cvar, parametric_var,
    rolling_var, stress_table, vol_cone, drawdown_series
)

st.set_page_config(page_title="QCEX · Risk Dashboard", page_icon="◈", layout="wide")
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{font-family:'IBM Plex Mono',monospace!important;background:#07090d;color:#b8ccb8}
  .stApp{background:#07090d}
  section[data-testid="stSidebar"]{background:#070c0a;border-right:1px solid #0f1f0f}
  h1,h2,h3{color:#ff7eb3!important;font-family:'IBM Plex Mono',monospace!important}
  [data-testid="metric-container"]{background:#070c07;border:1px solid #1a0a1a;border-radius:4px;padding:8px 12px}
  [data-testid="metric-container"] label{color:#3a1a2a!important;font-size:10px}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{color:#ff7eb3!important}
</style>""", unsafe_allow_html=True)

LAYOUT = dict(
    paper_bgcolor="#07090d", plot_bgcolor="#07090d",
    font=dict(family="IBM Plex Mono", color="#3a1a2a", size=10),
    xaxis=dict(gridcolor="#1a0a1a"), yaxis=dict(gridcolor="#1a0a1a"),
    margin=dict(l=50, r=20, t=30, b=40),
)

with st.sidebar:
    st.markdown("<div style='color:#6a2a4a;font-size:9px;letter-spacing:2px;margin-bottom:8px'>RISK DASHBOARD</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", list(TICKERS.keys()),
                              format_func=lambda x: TICKERS[x]["name"])
    confidence = st.select_slider("Nivel de confianza VaR", [0.95, 0.99, 0.995], value=0.99,
                                   format_func=lambda x: f"{x*100:.1f}%")
    horizon    = st.select_slider("Horizonte VaR (días)", [1, 5, 10, 22], value=1)
    position   = st.number_input("Posición (USD notional)", value=1_000_000, step=100_000)

@st.cache_data(ttl=3600)
def load(c):
    df    = fetch_prices(c, 504)
    rets  = compute_returns(df)
    stats = compute_stats(c, df)
    return df, rets, stats

df, rets, stats = load(commodity)
spot = stats["spot"]

st.markdown("## ⚠️ RISK DASHBOARD")

# ── VaR metrics ────────────────────────────────────────────────────────────────
hvar  = historical_var(rets, confidence, horizon)
cvar  = historical_cvar(rets, confidence, horizon)
pvar  = parametric_var(rets, confidence, horizon)

hvar_usd  = position * hvar
cvar_usd  = position * cvar
pvar_usd  = position * pvar

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(f"Hist. VaR ({confidence*100:.0f}%, {horizon}d)", f"{hvar*100:.2f}%", f"${hvar_usd:,.0f}")
c2.metric(f"CVaR / ES",                                     f"{cvar*100:.2f}%", f"${cvar_usd:,.0f}")
c3.metric(f"Param. VaR (Gauss.)",                           f"{pvar*100:.2f}%", f"${pvar_usd:,.0f}")
c4.metric("Vol 1M (ann.)",   f"{stats['vol_1m']:.1f}%")
c5.metric("Skewness",        f"{stats['skewness']:.3f}",
          "fat left tail" if stats["skewness"] < -0.3 else "approx. normal")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["DISTRIBUCIÓN & VAR", "STRESS TESTING", "ROLLING RISK"])

# ── TAB 1: Distribution ────────────────────────────────────────────────────────
with tab1:
    col_hist, col_qq = st.columns(2)

    with col_hist:
        st.markdown("**DISTRIBUCIÓN DE RETORNOS + VaR**")
        r_pct = rets * 100
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=r_pct, nbinsx=80,
            marker_color="#ff7eb3", opacity=0.7, name="Retornos"))
        fig.add_vline(x=-hvar*100, line_color="#ff2244", line_width=2,
                      annotation_text=f"Hist. VaR {confidence*100:.0f}%",
                      annotation_font_color="#ff2244", annotation_font_size=9)
        fig.add_vline(x=-cvar*100, line_color="#ff6644", line_width=1.5,
                      line_dash="dash",
                      annotation_text="CVaR",
                      annotation_font_color="#ff6644", annotation_font_size=9)
        fig.update_layout(**LAYOUT, height=310, xaxis_title="Retorno diario (%)",
                          yaxis_title="Frecuencia")
        st.plotly_chart(fig, use_container_width=True)

    with col_qq:
        st.markdown("**TAIL RISK: RETORNOS vs NORMAL**")
        from scipy import stats as scipy_stats
        sorted_r = np.sort(rets.dropna())
        n        = len(sorted_r)
        quantiles = scipy_stats.norm.ppf(np.arange(1, n+1) / (n+1),
                                          loc=sorted_r.mean(), scale=sorted_r.std())
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=quantiles*100, y=sorted_r*100,
            mode="markers", name="Datos",
            marker=dict(color="#ff7eb3", size=2, opacity=0.5),
        ))
        lims = [min(quantiles.min(), sorted_r.min())*100,
                max(quantiles.max(), sorted_r.max())*100]
        fig2.add_trace(go.Scatter(
            x=lims, y=lims, name="Normal",
            line=dict(color="#3a1a2a", width=1, dash="dot"),
        ))
        fig2.update_layout(**LAYOUT, height=310,
                           xaxis_title="Cuantiles teóricos normales (%)",
                           yaxis_title="Cuantiles observados (%)")
        st.plotly_chart(fig2, use_container_width=True)

    # VaR comparison table
    st.markdown("**COMPARATIVA VaR POR HORIZONTE Y NIVEL DE CONFIANZA**")
    rows_var = []
    for conf in [0.95, 0.99, 0.995]:
        row = {"Confianza": f"{conf*100:.1f}%"}
        for h in [1, 5, 10]:
            hv = historical_var(rets, conf, h) * 100
            cv = historical_cvar(rets, conf, h) * 100
            row[f"Hist.VaR {h}d (%)"] = f"{hv:.2f}"
            row[f"CVaR {h}d (%)"]     = f"{cv:.2f}"
        rows_var.append(row)
    st.dataframe(pd.DataFrame(rows_var), hide_index=True, use_container_width=True)

# ── TAB 2: Stress ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown("**ESCENARIOS DE STRESS — ANÁLISIS P&L**")
    stress_df = stress_table(commodity, spot)
    stress_df["PnL (USD)"] = (stress_df["pnl"] / stress_df["spot_orig"] * position).round(0)

    fig3 = go.Figure()
    colors = ["#4aff99" if v >= 0 else "#ff2244" for v in stress_df["shock_pct"]]
    fig3.add_trace(go.Bar(
        x=stress_df["name"],
        y=stress_df["shock_pct"],
        marker_color=colors,
        opacity=0.85,
        text=[f"{v:+.0f}%" for v in stress_df["shock_pct"]],
        textposition="outside",
        textfont=dict(size=10, color="#c8d6c8"),
    ))
    fig3.add_hline(y=0, line_color="#3a1a2a")
    fig3.update_layout(**LAYOUT, height=280,
                       xaxis_title="", yaxis_title="Shock (%)",
                       xaxis=dict(tickangle=-15))
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(
        stress_df[["name","shock_pct","spot_orig","spot_shock","PnL (USD)","desc"]]
            .rename(columns={"name":"Escenario","shock_pct":"Shock (%)","spot_orig":"Spot",
                              "spot_shock":"Spot shockeado","desc":"Descripción"}),
        use_container_width=True, hide_index=True,
    )

    st.markdown(f"""<div style='background:#0a0010;border:1px solid #1a0a1a;border-left:3px solid #ff7eb3;
      padding:10px 14px;border-radius:0 4px 4px 0;font-size:10px;color:#3a1a2a;margin-top:12px'>
      Peor escenario: P&L = <strong style='color:#ff2244'>
      ${stress_df["PnL (USD)"].min():,.0f}</strong> sobre posición de
      ${position:,.0f} notional ({commodity})
    </div>""", unsafe_allow_html=True)

# ── TAB 3: Rolling risk ────────────────────────────────────────────────────────
with tab3:
    col_rvar, col_dd = st.columns(2)

    with col_rvar:
        st.markdown("**ROLLING VaR (252d window)**")
        rvar = rolling_var(rets, window=252, confidence=confidence, horizon=horizon) * 100
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=df.index[-len(rvar):], y=rvar,
            name=f"VaR {confidence*100:.0f}%",
            line=dict(color="#ff7eb3", width=1.5),
            fill="tozeroy", fillcolor="#ff7eb310",
        ))
        fig4.update_layout(**LAYOUT, height=280,
                           yaxis_title="VaR (%)", xaxis_title="")
        st.plotly_chart(fig4, use_container_width=True)

    with col_dd:
        st.markdown("**DRAWDOWN**")
        dd = drawdown_series(df["Close"])
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(
            x=df.index, y=dd,
            fill="tozeroy", fillcolor="#ff2244",
            line=dict(color="#ff2244", width=1),
            name="Drawdown",
        ))
        fig5.add_hline(y=dd.min(), line_dash="dash", line_color="#ff7eb3",
                       annotation_text=f"Max DD: {dd.min():.1f}%",
                       annotation_font_color="#ff7eb3", annotation_font_size=9)
        fig5.update_layout(**LAYOUT, height=280,
                           yaxis_title="Drawdown (%)", xaxis_title="")
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown("**VOL CONE — PERCENTILES HISTÓRICOS**")
    cone = vol_cone(rets)
    if not cone.empty:
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p90"], name="P90",
            line=dict(color="#ff7eb344", width=1, dash="dot"), showlegend=False))
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p10"], name="P10–P90",
            fill="tonexty", fillcolor="#ff7eb315",
            line=dict(color="#ff7eb344", width=1, dash="dot")))
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p75"], name="P75",
            line=dict(color="#ff7eb388", width=1), showlegend=False))
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p25"], name="P25–P75",
            fill="tonexty", fillcolor="#ff7eb325",
            line=dict(color="#ff7eb388", width=1)))
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["median"], name="Mediana",
            line=dict(color="#ff7eb3", width=1.5, dash="dash")))
        fig6.add_trace(go.Scatter(x=cone["label"], y=cone["current"], name="Vol actual",
            mode="markers+lines",
            marker=dict(size=10, color="#4aff99", symbol="diamond"),
            line=dict(color="#4aff99", width=2)))
        fig6.update_layout(**LAYOUT, height=280,
                           yaxis_title="Vol anualizada (%)",
                           legend=dict(bgcolor="#070c07", bordercolor="#1a0a1a"))
        st.plotly_chart(fig6, use_container_width=True)

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

