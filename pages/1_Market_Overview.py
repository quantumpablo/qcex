from __future__ import annotations
"""pages/1_Market_Overview.py — QCEX v4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from theme import LEGEND, CSS, BG, BG2, BG3, ACC, TEXT, TEXT2, BORD, GRID, PLOTLY, ax, footer, COMM_COLORS
from data.fetcher import fetch_prices, compute_returns, rolling_vol, compute_stats, TICKERS
from analytics.risk import vol_cone, drawdown_series, correlation_matrix

st.set_page_config(page_title="QCEX · Market Overview", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div style='color:{ACC};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>MARKET OVERVIEW</div>", unsafe_allow_html=True)
    selected = st.multiselect("Commodities", options=list(TICKERS.keys()),
        default=["cocoa", "gas"], format_func=lambda x: TICKERS[x]["name"])
    period = st.select_slider("Period", options=[63,126,252,504], value=252,
        format_func=lambda x: {63:"3M",126:"6M",252:"1Y",504:"2Y"}[x])
    vol_window = st.slider("Vol window (days)", 10, 63, 21)

if not selected:
    st.warning("Select at least one commodity.")
    st.stop()

@st.cache_data(ttl=3600)
def load_all(commodities, days):
    out = {}
    for c in commodities:
        df = fetch_prices(c, days)
        out[c] = {"df": df, "stats": compute_stats(c, df), "returns": compute_returns(df)}
    return out

with st.spinner("Loading data..."):
    data = load_all(tuple(selected), period)

st.markdown("## MARKET OVERVIEW")

# ── Metrics ───────────────────────────────────────────────────────────────────
for col, c in zip(st.columns(len(selected)), selected):
    s = data[c]["stats"]
    with col:
        st.metric(TICKERS[c]["name"],
            f"{s['spot']:,.2f} {TICKERS[c]['unit']}",
            f"{s['pct_change']:+.2f}% 1d  ·  Vol 1M: {s['vol_1m']:.1f}%",
            delta_color="normal" if s["pct_change"] >= 0 else "inverse")

st.markdown("---")

# ── Price chart ───────────────────────────────────────────────────────────────
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>HISTORICAL PRICES (base 100)</div>", unsafe_allow_html=True)
fig = go.Figure()
for c in selected:
    df = data[c]["df"]; close = df["Close"].dropna()
    fig.add_trace(go.Scatter(x=df.index, y=close/close.iloc[0]*100,
        name=TICKERS[c]["name"],
        line=dict(color=COMM_COLORS.get(c,"#888"), width=1.8),
        hovertemplate="%{x|%Y-%m-%d}<br>Índice: %{y:.1f}<extra></extra>"))
fig.add_hline(y=100, line_dash="dot", line_color=BORD)
fig.update_layout(**PLOTLY, height=300,
    xaxis=ax(), yaxis=ax(),
    legend=dict(bgcolor=BG2, bordercolor=BORD, borderwidth=1))
st.plotly_chart(fig, use_container_width=True)

# ── Vol + Returns ─────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>ROLLING VOL (%)</div>", unsafe_allow_html=True)
    fig2 = go.Figure()
    for c in selected:
        fig2.add_trace(go.Scatter(
            x=data[c]["df"].index,
            y=rolling_vol(data[c]["df"], vol_window)*100,
            name=f"{TICKERS[c]['name']} ({vol_window}d)",
            line=dict(color=COMM_COLORS.get(c,"#888"), width=1.5)))
    fig2.update_layout(**PLOTLY, height=240, xaxis=ax(), yaxis=ax("Vol (%)"))
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>RETURN DISTRIBUTION</div>", unsafe_allow_html=True)
    fig3 = go.Figure()
    for c in selected:
        fig3.add_trace(go.Histogram(x=data[c]["returns"].dropna()*100,
            name=TICKERS[c]["name"], opacity=0.65, nbinsx=50,
            marker_color=COMM_COLORS.get(c,"#888")))
    fig3.update_layout(**PLOTLY, height=240, barmode="overlay",
        xaxis=ax("Retorno diario (%)"), yaxis=ax("Frecuencia"))
    st.plotly_chart(fig3, use_container_width=True)

# ── Stats table ───────────────────────────────────────────────────────────────
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin:16px 0 8px;'>STATISTICS</div>", unsafe_allow_html=True)
def safe(v, fmt=".1f", suffix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return format(v, fmt) + suffix

rows = []
for c in selected:
    s = data[c]["stats"]
    rows.append({
        "Commodity":  TICKERS[c]["name"],
        "Spot":       f"{s['spot']:,.2f}",
        "Vol 1M":     safe(s["vol_1m"]) + "%",
        "Vol 1Y":     safe(s["vol_1y"]) + "%",
        "Ret 1M":     f"{s['ret_1m']:+.1f}%",
        "Ret 3M":     f"{s['ret_3m']:+.1f}%",
        "52W High":   f"{s['high_52w']:,.2f}",
        "52W Low":    f"{s['low_52w']:,.2f}",
        "Skewness":   safe(s["skewness"], ".3f"),
        "Kurtosis":   safe(s["kurtosis"], ".3f"),
        "Source":     s["source"],
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Correlation matrix ────────────────────────────────────────────────────────
if len(selected) > 1:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin:16px 0 8px;'>CORRELATION MATRIX</div>", unsafe_allow_html=True)
    try:
        corr = correlation_matrix({TICKERS[c]["name"]: data[c]["returns"] for c in selected})
        fig4 = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
            colorscale=[[0,"#FF4444"],[0.5,BG3],[1,ACC]],
            zmid=0, zmin=-1, zmax=1,
            text=np.round(corr.values, 3), texttemplate="%{text}",
            textfont=dict(size=13, color=TEXT, family="IBM Plex Mono"),
            showscale=True))
        fig4.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG, height=280,
            font=dict(family="IBM Plex Mono", color=TEXT, size=11),
            margin=dict(l=40, r=20, t=20, b=80),
            xaxis=dict(side="bottom", gridcolor=GRID,
                tickfont=dict(color=TEXT, size=11)),
            yaxis=dict(autorange="reversed", gridcolor=GRID,
                tickfont=dict(color=TEXT, size=11)))
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.error(f"Error en correlación: {e}")

# ── Drawdown + Vol cone ───────────────────────────────────────────────────────
st.markdown("---")
cd, cc = st.columns(2)

with cd:
    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>DRAWDOWN FROM PEAK</div>", unsafe_allow_html=True)
    fig5 = go.Figure()
    for c in selected:
        df = data[c]["df"]; color = COMM_COLORS.get(c, "#888")
        r, g_val, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
        fig5.add_trace(go.Scatter(x=df.index, y=drawdown_series(df["Close"]),
            fill="tozeroy", name=TICKERS[c]["name"],
            line=dict(color=color, width=1),
            fillcolor=f"rgba({r},{g_val},{b},0.12)"))
    fig5.update_layout(**PLOTLY, height=240, xaxis=ax(), yaxis=ax("Drawdown (%)"))
    st.plotly_chart(fig5, use_container_width=True)

with cc:
    if selected:
        cone = vol_cone(data[selected[0]]["returns"])
        color = COMM_COLORS.get(selected[0], ACC)
        r, g_val, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
        if not cone.empty:
            st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>VOL CONE — {TICKERS[selected[0]]['name']}</div>", unsafe_allow_html=True)
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p90"],
                line=dict(color=f"rgba({r},{g_val},{b},0.3)", width=1, dash="dot"), showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p10"],
                fill="tonexty", fillcolor=f"rgba({r},{g_val},{b},0.08)",
                name="P10-P90", line=dict(color=f"rgba({r},{g_val},{b},0.3)", width=1, dash="dot")))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["median"],
                name="Mediana", line=dict(color=color, width=1.5, dash="dash")))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["current"],
                name="Actual", mode="markers+lines",
                marker=dict(size=8, color=ACC, symbol="diamond"),
                line=dict(color=ACC, width=2)))
            fig6.update_layout(**PLOTLY, height=240, xaxis=ax(), yaxis=ax("Vol (%)"))
            st.plotly_chart(fig6, use_container_width=True)


# ── Weather indicators ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>WEATHER & MACRO INDICATORS</div>", unsafe_allow_html=True)

try:
    from data.weather import fetch_weather, compute_weather_indicators
    weather_cols = st.columns(len(selected))
    for col, c in zip(weather_cols, selected):
        with col:
            with st.spinner(f"Loading weather {TICKERS[c]['name']}..."):
                df_w = fetch_weather(c, days=60)
                wi   = compute_weather_indicators(c, df_w)

            impact_color = {"BULLISH":"#FF4455","BEARISH":"#4AFF99","NEUTRAL":GOLD}.get(wi["price_impact"], TEXT2)
            st.markdown(
                f'<div style="background:{BG2};border:1px solid {BORD};border-left:3px solid {impact_color};'
                f'padding:12px 14px;border-radius:0 4px 4px 0;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                f'<span style="color:{TEXT};font-size:9px;font-weight:600;">{TICKERS[c]["name"]}</span>'
                f'<span style="background:{impact_color}22;color:{impact_color};font-size:7px;'
                f'letter-spacing:1px;padding:2px 7px;border-radius:2px;border:1px solid {impact_color}44;">'
                f'{wi["price_impact"]}</span></div>'
                f'<div style="color:{TEXT2};font-size:8px;margin-bottom:8px;font-style:italic;">{wi["summary"][:80]}...</div>'
                f'</div>',
                unsafe_allow_html=True)

            for ind in wi["indicators"]:
                arrow = "↑" if ind["trend"] == "up" else ("↓" if ind["trend"] == "down" else "→")
                st.markdown(
                    f'<div style="background:{BG3};border:1px solid {BORD};padding:7px 10px;'
                    f'border-radius:3px;margin-bottom:4px;display:flex;justify-content:space-between;'
                    f'align-items:center;">'
                    f'<div>'
                    f'<div style="color:{TEXT2};font-size:8px;">{ind["name"]}</div>'
                    f'<div style="color:{TEXT2};font-size:8px;font-style:italic;">{ind["impact"]}</div>'
                    f'</div>'
                    f'<span style="color:{ind["color"]};font-size:12px;font-weight:600;">'
                    f'{arrow} {ind["value"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True)

            src_color = ACC if wi["source"] == "open-meteo" else GOLD
            st.markdown(f'<div style="color:{src_color};font-size:7px;margin-top:4px;">● {wi["source"].upper()} · {wi["location"]}</div>', unsafe_allow_html=True)
except Exception as e:
    st.info(f"Indicadores meteorológicos no disponibles: {e}")


st.markdown(footer("Market Overview"), unsafe_allow_html=True)
