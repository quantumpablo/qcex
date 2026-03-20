"""
pages/1_Market_Overview.py — QCEX
Fixed: correlation matrix, NaN stats, light/dark mode toggle
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data.fetcher import fetch_prices, compute_returns, rolling_vol, compute_stats, TICKERS
from analytics.risk import vol_cone, drawdown_series, correlation_matrix

def alpha_color(hex_color, alpha=0.1):
    """Convert hex color + alpha to rgba string safe for Plotly."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"
    except:
        return hex_color


st.set_page_config(page_title="QCEX · Market Overview", page_icon="◈", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

with st.sidebar:
    st.markdown("<div style='font-size:9px;letter-spacing:2px;margin-bottom:8px'>QCEX · MARKET OVERVIEW</div>", unsafe_allow_html=True)
    dark = st.toggle("Modo oscuro", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark
    st.markdown("---")
    selected = st.multiselect("Commodities", options=list(TICKERS.keys()),
        default=["cocoa","gas"], format_func=lambda x: TICKERS[x]["name"])
    period = st.select_slider("Período histórico", options=[63,126,252,504], value=252,
        format_func=lambda x: {63:"3M",126:"6M",252:"1Y",504:"2Y"}[x])
    vol_window = st.slider("Ventana vol rolling (días)", 10, 63, 21)

BG,BG2,GRID,TEXT,TEXT2,BORDER,ACC = (
    ("#07090D","#070C07","#0A180A","#B8CCB8","#3A5A3A","#0F1F0F","#4AFF99") if dark else
    ("#F8FAF8","#FFFFFF","#D8EDD8","#1A2A1A","#3A5A3A","#CCDDCC","#1A6A2A")
)

st.markdown(f"""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{{font-family:'IBM Plex Mono',monospace!important;background:{BG};color:{TEXT}}}
  .stApp{{background:{BG}}}
  section[data-testid="stSidebar"]{{background:{BG2};border-right:1px solid {BORDER}}}
  h1,h2,h3{{color:{ACC}!important;font-family:'IBM Plex Mono',monospace!important}}
  [data-testid="metric-container"]{{background:{BG2};border:1px solid {BORDER};border-radius:4px;padding:8px 12px}}
  [data-testid="metric-container"] label{{color:{TEXT2}!important;font-size:10px;letter-spacing:1px}}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{{color:{ACC}!important}}
</style>""", unsafe_allow_html=True)

PL = dict(paper_bgcolor=BG, plot_bgcolor=BG,
    font=dict(family="IBM Plex Mono", color=TEXT2, size=10),
    margin=dict(l=50,r=20,t=35,b=40))
AX = dict(gridcolor=GRID, showgrid=True, zeroline=False)
COMM_COLORS = {"cocoa":"#D4A85A","gas":"#4A9EFF","uranium":"#4AFF99","gold":"#FFE566"}

if not selected:
    st.warning("Selecciona al menos un commodity.")
    st.stop()

@st.cache_data(ttl=3600)
def load_all(commodities, period_days):
    out = {}
    for c in commodities:
        df = fetch_prices(c, period_days)
        out[c] = {"df":df, "stats":compute_stats(c,df), "returns":compute_returns(df)}
    return out

with st.spinner("Cargando datos..."):
    data = load_all(tuple(selected), period)

st.markdown("## MARKET OVERVIEW")

# ── Metrics ───────────────────────────────────────────────────────────────────
for col, c in zip(st.columns(len(selected)), selected):
    s = data[c]["stats"]
    with col:
        st.metric(TICKERS[c]["name"],
            f"{s['spot']:,.2f} {TICKERS[c]['unit']}",
            f"{s['pct_change']:+.2f}% 1d  |  Vol 1M: {s['vol_1m']:.1f}%",
            delta_color="normal" if s["pct_change"]>=0 else "inverse")
        st.markdown(f"<div style='font-size:8px;color:{ACC if s['source']=='yfinance' else '#AA8800'}'>● {s['source'].upper()}</div>", unsafe_allow_html=True)

st.markdown("---")

# ── Precio histórico ──────────────────────────────────────────────────────────
st.markdown("### PRECIOS HISTÓRICOS (base 100)")
fig = go.Figure()
for c in selected:
    df = data[c]["df"]; close = df["Close"].dropna()
    fig.add_trace(go.Scatter(x=df.index, y=close/close.iloc[0]*100,
        name=TICKERS[c]["name"], line=dict(color=COMM_COLORS.get(c,"#888"),width=1.8),
        hovertemplate="%{x|%Y-%m-%d}<br>Índice: %{y:.1f}<extra></extra>"))
fig.add_hline(y=100, line_dash="dot", line_color=BORDER, line_width=1)
fig.update_layout(**PL, height=300, xaxis=AX, yaxis=AX,
    legend=dict(bgcolor=BG2, bordercolor=BORDER, borderwidth=1))
st.plotly_chart(fig, use_container_width=True)

# ── Vol rolling + retornos ────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("### VOL ROLLING (%)")
    fig2 = go.Figure()
    for c in selected:
        df = data[c]["df"]
        fig2.add_trace(go.Scatter(x=df.index, y=rolling_vol(df,vol_window)*100,
            name=f"{TICKERS[c]['name']} ({vol_window}d)",
            line=dict(color=COMM_COLORS.get(c,"#888"),width=1.5)))
    fig2.update_layout(**PL, height=250, xaxis=AX,
        yaxis=dict(**AX, title="Vol (%)"))
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.markdown("### DISTRIBUCIÓN DE RETORNOS")
    fig3 = go.Figure()
    for c in selected:
        fig3.add_trace(go.Histogram(x=data[c]["returns"].dropna()*100,
            name=TICKERS[c]["name"], opacity=0.65, nbinsx=50,
            marker_color=COMM_COLORS.get(c,"#888")))
    fig3.update_layout(**PL, height=250, barmode="overlay",
        xaxis=dict(**AX, title="Retorno diario (%)"),
        yaxis=dict(**AX, title="Frecuencia"))
    st.plotly_chart(fig3, use_container_width=True)

# ── Estadísticas ──────────────────────────────────────────────────────────────
st.markdown("### ESTADÍSTICAS")
def safe(v, fmt=".1f"):
    if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
    return format(v, fmt)

rows = []
for c in selected:
    s = data[c]["stats"]
    rows.append({"Commodity":TICKERS[c]["name"],"Spot":f"{s['spot']:,.2f}",
        "Vol 1M":safe(s['vol_1m'])+"%","Vol 1Y":safe(s['vol_1y'])+"%",
        "Ret 1M":f"{s['ret_1m']:+.1f}%","Ret 3M":f"{s['ret_3m']:+.1f}%",
        "Ret 1Y":f"{s['ret_1y']:+.1f}%","52W High":f"{s['high_52w']:,.2f}",
        "52W Low":f"{s['low_52w']:,.2f}","Skewness":safe(s['skewness'],".3f"),
        "Kurtosis":safe(s['kurtosis'],".3f"),"Fuente":s["source"]})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Matriz de correlación ─────────────────────────────────────────────────────
if len(selected) > 1:
    st.markdown("### MATRIZ DE CORRELACIÓN")
    try:
        corr = correlation_matrix({TICKERS[c]["name"]:data[c]["returns"] for c in selected})
        fig4 = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
            colorscale=[[0,"#FF4444"],[0.5,BG],[1,ACC]],
            zmid=0, zmin=-1, zmax=1,
            text=np.round(corr.values,3), texttemplate="%{text}",
            textfont=dict(size=13,color=TEXT,family="IBM Plex Mono"),
            hoverongaps=False, showscale=True,
        ))
        fig4.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG, height=300,
            font=dict(family="IBM Plex Mono",color=TEXT,size=11),
            margin=dict(l=40,r=20,t=30,b=80),
            xaxis=dict(side="bottom", gridcolor=GRID, tickfont=dict(color=TEXT,size=11)),
            yaxis=dict(autorange="reversed", gridcolor=GRID, tickfont=dict(color=TEXT,size=11)),
        )
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.error(f"Error en correlación: {e}")

# ── Drawdown + Vol cone ───────────────────────────────────────────────────────
st.markdown("### DRAWDOWN + VOL CONE")
cd, cc = st.columns(2)

with cd:
    fig5 = go.Figure()
    for c in selected:
        df = data[c]["df"]; color = COMM_COLORS.get(c,"#888")
        fig5.add_trace(go.Scatter(x=df.index, y=drawdown_series(df["Close"]),
            fill="tozeroy", name=TICKERS[c]["name"],
            line=dict(color=color,width=1), fillcolor=alpha_color(color, 0.13)))
    fig5.update_layout(**PL, height=250, xaxis=AX,
        yaxis=dict(**AX,title="Drawdown (%)"),
        title=dict(text="DRAWDOWN DESDE MÁXIMO",font=dict(color=TEXT2,size=10)))
    st.plotly_chart(fig5, use_container_width=True)

with cc:
    if selected:
        cone = vol_cone(data[selected[0]]["returns"])
        color = COMM_COLORS.get(selected[0], ACC)
        if not cone.empty:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p90"],
                line=dict(color=alpha_color(color, 0.27),width=1,dash="dot"),showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p10"],
                fill="tonexty",fillcolor=alpha_color(color, 0.1),name="P10–P90",
                line=dict(color=alpha_color(color, 0.27),width=1,dash="dot")))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["median"],
                name="Mediana",line=dict(color=color,width=1.5,dash="dash")))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["current"],
                name="Vol actual",mode="markers+lines",
                marker=dict(size=8,color=ACC),line=dict(color=ACC,width=2)))
            fig6.update_layout(**PL, height=250, xaxis=AX,
                yaxis=dict(**AX,title="Vol (%)"),
                title=dict(text=f"VOL CONE — {TICKERS[selected[0]]['name']}",
                    font=dict(color=TEXT2,size=10)),
                legend=dict(bgcolor=BG2,bordercolor=BORDER,font=dict(size=9)))
            st.plotly_chart(fig6, use_container_width=True)

st.markdown(f"""<div style="border-top:1px solid {BORDER};padding-top:14px;margin-top:32px;
  display:flex;justify-content:space-between;align-items:center;">
  <div style="color:{ACC};font-size:11px;font-weight:600;letter-spacing:2px;">QCEX</div>
  <div style="color:{TEXT2};font-size:8px;letter-spacing:1px;">
    by <strong>QuantumPablo</strong> · Pablo M. Paniagua</div>
</div>""", unsafe_allow_html=True)
