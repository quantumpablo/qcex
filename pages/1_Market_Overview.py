"""
app/pages/1_Market_Overview.py
==============================
Market Overview page: spot prices, historical returns,
rolling vol, correlation matrix, vol cone.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from data.fetcher import fetch_prices, compute_returns, rolling_vol, compute_stats, TICKERS
from analytics.risk import vol_cone, drawdown_series, max_drawdown, correlation_matrix

st.set_page_config(page_title="QCEX · Market Overview", page_icon="◈", layout="wide")

# ── Shared CSS (minimal repeat) ───────────────────────────────────────────────
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{font-family:'IBM Plex Mono',monospace!important;background:#07090d;color:#b8ccb8}
  .stApp{background:#07090d}
  section[data-testid="stSidebar"]{background:#070c0a;border-right:1px solid #0f1f0f}
  h1,h2,h3{color:#4aff99!important;font-family:'IBM Plex Mono',monospace!important}
  [data-testid="metric-container"]{background:#070c07;border:1px solid #0f1f0f;border-radius:4px;padding:8px 12px}
  [data-testid="metric-container"] label{color:#1a3a1a!important;font-size:10px;letter-spacing:1px}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{color:#4aff99!important}
</style>""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#07090d", plot_bgcolor="#07090d",
    font=dict(family="IBM Plex Mono", color="#3a5a3a", size=10),
    xaxis=dict(gridcolor="#0a180a", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#0a180a", showgrid=True, zeroline=False),
    margin=dict(l=40, r=20, t=30, b=40),
)

COMM_COLORS = {"cocoa": "#d4a85a", "gas": "#4a9eff", "uranium": "#4aff99", "gold": "#ffe566"}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='color:#2a5a2a;font-size:9px;letter-spacing:2px;margin-bottom:8px'>MARKET OVERVIEW</div>", unsafe_allow_html=True)
    selected = st.multiselect(
        "Commodities", options=list(TICKERS.keys()),
        default=["cocoa", "gas"],
        format_func=lambda x: TICKERS[x]["name"],
    )
    period = st.select_slider("Período histórico", options=[63, 126, 252, 504], value=252,
                               format_func=lambda x: {63:"3M",126:"6M",252:"1Y",504:"2Y"}[x])
    vol_window = st.slider("Ventana vol rolling (días)", 10, 63, 21)

if not selected:
    st.warning("Selecciona al menos un commodity.")
    st.stop()

st.markdown("## 📊 MARKET OVERVIEW")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_all(commodities, period_days):
    data = {}
    for c in commodities:
        df   = fetch_prices(c, period_days)
        stats = compute_stats(c, df)
        rets  = compute_returns(df)
        data[c] = {"df": df, "stats": stats, "returns": rets}
    return data

with st.spinner("Cargando datos..."):
    data = load_all(tuple(selected), period)

# ── Spot price metrics ─────────────────────────────────────────────────────────
st.markdown("### SPOT PRICES")
cols = st.columns(len(selected))
for col, c in zip(cols, selected):
    s = data[c]["stats"]
    color = "normal" if s["pct_change"] >= 0 else "inverse"
    with col:
        st.metric(
            label=TICKERS[c]["name"],
            value=f"{s['spot']:,.2f} {TICKERS[c]['unit']}",
            delta=f"{s['pct_change']:+.2f}% 1d | Vol 1M: {s['vol_1m']:.1f}%",
            delta_color=color,
        )
        src_color = "#2a4a2a" if s["source"] == "yfinance" else "#4a3a00"
        st.markdown(f"<div style='font-size:8px;color:{src_color}'>● {s['source'].upper()}</div>", unsafe_allow_html=True)

# ── Price chart ────────────────────────────────────────────────────────────────
st.markdown("### PRECIOS HISTÓRICOS (normalizados base 100)")
fig = go.Figure()
for c in selected:
    df    = data[c]["df"]
    close = df["Close"]
    normd = close / close.iloc[0] * 100
    fig.add_trace(go.Scatter(
        x=df.index, y=normd,
        name=TICKERS[c]["name"],
        line=dict(color=COMM_COLORS.get(c, "#ffffff"), width=1.5),
        hovertemplate="%{x|%Y-%m-%d}<br>Idx: %{y:.1f}<extra></extra>",
    ))
fig.add_hline(y=100, line_dash="dot", line_color="#1a3a1a", line_width=1)
fig.update_layout(**PLOTLY_LAYOUT, height=320,
                  legend=dict(bgcolor="#070c07", bordercolor="#0f1f0f", borderwidth=1))
st.plotly_chart(fig, use_container_width=True)

# ── Rolling vol + returns ──────────────────────────────────────────────────────
col_vol, col_rets = st.columns(2)

with col_vol:
    st.markdown("### VOL ROLLING HISTÓRICA (%)")
    fig2 = go.Figure()
    for c in selected:
        df  = data[c]["df"]
        rvol = rolling_vol(df, vol_window) * 100
        fig2.add_trace(go.Scatter(
            x=df.index, y=rvol,
            name=f"{TICKERS[c]['name']} ({vol_window}d)",
            line=dict(color=COMM_COLORS.get(c, "#ffffff"), width=1.5),
        ))
    fig2.update_layout(**PLOTLY_LAYOUT, height=260)
    st.plotly_chart(fig2, use_container_width=True)

with col_rets:
    st.markdown("### DISTRIBUCIÓN DE RETORNOS")
    fig3 = go.Figure()
    for c in selected:
        rets = data[c]["returns"] * 100
        fig3.add_trace(go.Histogram(
            x=rets, name=TICKERS[c]["name"],
            opacity=0.6, nbinsx=50,
            marker_color=COMM_COLORS.get(c, "#ffffff"),
        ))
    fig3.update_layout(**PLOTLY_LAYOUT, height=260, barmode="overlay",
                       xaxis_title="Retorno diario (%)")
    st.plotly_chart(fig3, use_container_width=True)

# ── Statistics table ───────────────────────────────────────────────────────────
st.markdown("### ESTADÍSTICAS")
rows = []
for c in selected:
    s = data[c]["stats"]
    rows.append({
        "Commodity"   : TICKERS[c]["name"],
        "Spot"        : f"{s['spot']:,.2f}",
        "Vol 1M (%)"  : f"{s['vol_1m']:.1f}",
        "Vol 1Y (%)"  : f"{s['vol_1y']:.1f}",
        "Ret 1M (%)"  : f"{s['ret_1m']:+.1f}",
        "Ret 3M (%)"  : f"{s['ret_3m']:+.1f}",
        "Ret 1Y (%)"  : f"{s['ret_1y']:+.1f}",
        "52W High"    : f"{s['high_52w']:,.2f}",
        "52W Low"     : f"{s['low_52w']:,.2f}",
        "Skewness"    : f"{s['skewness']:.3f}",
        "Kurt. (ex)"  : f"{s['kurtosis']:.3f}",
        "Source"      : s["source"],
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Correlation matrix ─────────────────────────────────────────────────────────
if len(selected) > 1:
    st.markdown("### MATRIZ DE CORRELACIÓN (retornos log diarios)")
    rets_dict = {TICKERS[c]["name"]: data[c]["returns"] for c in selected}
    corr = correlation_matrix(rets_dict)
    fig4 = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale=[[0,"#ff4444"],[0.5,"#070c07"],[1,"#4aff99"]],
        zmid=0, zmin=-1, zmax=1,
        text=np.round(corr.values, 3),
        texttemplate="%{text}",
        textfont=dict(size=12, color="#c8d6c8", family="IBM Plex Mono"),
        hoverongaps=False,
    ))
    fig4.update_layout(**PLOTLY_LAYOUT, height=280,
                       xaxis=dict(side="bottom"), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Drawdown & vol cone ────────────────────────────────────────────────────────
st.markdown("### DRAWDOWN + VOL CONE")
col_dd, col_cone = st.columns(2)

with col_dd:
    fig5 = go.Figure()
    for c in selected:
        df = data[c]["df"]
        dd = drawdown_series(df["Close"])
        fig5.add_trace(go.Scatter(
            x=df.index, y=dd,
            fill="tozeroy", name=TICKERS[c]["name"],
            line=dict(color=COMM_COLORS.get(c, "#ffffff"), width=1),
            fillcolor=COMM_COLORS.get(c, "#ffffff") + "22",
        ))
    fig5.update_layout(**PLOTLY_LAYOUT, height=250,
                       yaxis_title="Drawdown (%)", title_text="DRAWDOWN DESDE MÁXIMO")
    st.plotly_chart(fig5, use_container_width=True)

with col_cone:
    if selected:
        c0    = selected[0]
        cone  = vol_cone(data[c0]["returns"])
        color = COMM_COLORS.get(c0, "#4aff99")
        if not cone.empty:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p90"], name="P90",
                line=dict(color=color+"55", width=1, dash="dot"), showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p10"], name="P10",
                fill="tonexty", fillcolor=color+"15",
                line=dict(color=color+"55", width=1, dash="dot"), showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["median"], name="Mediana",
                line=dict(color=color, width=1.5, dash="dash")))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["current"], name="Actual",
                mode="markers+lines", marker=dict(size=8, color=color),
                line=dict(color=color, width=2)))
            fig6.update_layout(**PLOTLY_LAYOUT, height=250,
                               yaxis_title="Vol (%)", title_text=f"VOL CONE — {TICKERS[c0]['name']}")
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

