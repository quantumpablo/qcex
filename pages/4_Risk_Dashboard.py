from __future__ import annotations
"""pages/4_Risk_Dashboard.py — QCEX v4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats as scipy_stats
from theme import LEGEND, CSS, BG, BG2, BG3, ACC, PINK, RED, GREEN, TEXT, TEXT2, BORD, GRID, PLOTLY, ax, footer
from data.fetcher import fetch_prices, compute_returns, compute_stats, TICKERS
from analytics.risk import (historical_var, historical_cvar, parametric_var,
    rolling_var, stress_table, vol_cone, drawdown_series)

st.set_page_config(page_title="QCEX · Risk Dashboard", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div style='color:{PINK};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>RISK DASHBOARD</div>", unsafe_allow_html=True)
    commodity  = st.selectbox("Commodity", list(TICKERS.keys()), format_func=lambda x: TICKERS[x]["name"])
    confidence = st.select_slider("VaR Confidence", [0.95,0.99,0.995], value=0.99,
                    format_func=lambda x: f"{x*100:.1f}%")
    horizon    = st.select_slider("Horizon (days)", [1,5,10,22], value=1)
    position   = st.number_input("Position (USD notional)", value=1_000_000, step=100_000)

@st.cache_data(ttl=3600)
def load(c):
    df = fetch_prices(c, 504)
    return df, compute_returns(df), compute_stats(c, df)

df, rets, stats = load(commodity)
spot = stats["spot"]

hvar = historical_var(rets, confidence, horizon)
cvar = historical_cvar(rets, confidence, horizon)
pvar = parametric_var(rets, confidence, horizon)

st.markdown("## RISK DASHBOARD")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(f"Hist. VaR {confidence*100:.0f}%", f"{hvar*100:.2f}%", f"${position*hvar:,.0f}")
c2.metric("CVaR / ES",                         f"{cvar*100:.2f}%", f"${position*cvar:,.0f}")
c3.metric("VaR Gaussiano",                     f"{pvar*100:.2f}%", f"${position*pvar:,.0f}")
c4.metric("Vol 1M",   f"{stats['vol_1m']:.1f}%")
c5.metric("Skewness", f"{stats['skewness']:.3f}",
    "left tail" if stats["skewness"] < -0.3 else "approx. normal")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["DISTRIBUTION & VAR","STRESS TESTING","ROLLING RISK"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    c1h, c2h = st.columns(2)
    with c1h:
        st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>RETURN DISTRIBUTION</div>", unsafe_allow_html=True)
        r_pct = rets.dropna() * 100
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=r_pct, nbinsx=80, marker_color=PINK, opacity=0.75, name="Retornos"))
        fig.add_vline(x=-hvar*100, line_color=RED, line_width=2,
            annotation_text=f"VaR {confidence*100:.0f}%",
            annotation_font_color=RED, annotation_font_size=9)
        fig.add_vline(x=-cvar*100, line_color="#FF8844", line_width=1.5, line_dash="dash",
            annotation_text="CVaR", annotation_font_color="#FF8844", annotation_font_size=9)
        fig.update_layout(**PLOTLY, height=280,
            xaxis=ax("Retorno diario (%)"), yaxis=ax("Frecuencia"))
        st.plotly_chart(fig, use_container_width=True)

    with c2h:
        st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>Q-Q PLOT vs NORMAL</div>", unsafe_allow_html=True)
        try:
            s = np.sort(rets.dropna().values)
            n = len(s)
            q = scipy_stats.norm.ppf(np.arange(1,n+1)/(n+1), loc=s.mean(), scale=s.std())
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=q*100, y=s*100, mode="markers", name="Data",
                marker=dict(color=PINK, size=2, opacity=0.5)))
            lm = [min(q.min(),s.min())*100, max(q.max(),s.max())*100]
            fig2.add_trace(go.Scatter(x=lm, y=lm, name="Normal",
                line=dict(color=BORD, width=1, dash="dot")))
            fig2.update_layout(**PLOTLY, height=280,
                xaxis=ax("Cuantiles teóricos (%)"), yaxis=ax("Cuantiles observados (%)"))
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Q-Q plot: {e}")

    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin:16px 0 8px;'>VaR COMPARISON</div>", unsafe_allow_html=True)
    rows = []
    for conf in [0.95, 0.99, 0.995]:
        row = {"Confianza": f"{conf*100:.1f}%"}
        for h in [1, 5, 10]:
            row[f"VaR {h}d (%)"]  = f"{historical_var(rets,conf,h)*100:.2f}"
            row[f"CVaR {h}d (%)"] = f"{historical_cvar(rets,conf,h)*100:.2f}"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    try:
        stress_df = stress_table(commodity, spot)
        stress_df["PnL (USD)"] = (stress_df["pnl"]/stress_df["spot_orig"]*position).round(0)

        st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>STRESS SCENARIOS</div>", unsafe_allow_html=True)
        bar_colors = [GREEN if v >= 0 else RED for v in stress_df["shock_pct"]]
        fig3 = go.Figure(go.Bar(
            x=stress_df["name"], y=stress_df["shock_pct"],
            marker_color=bar_colors, opacity=0.85,
            text=[f"{v:+.0f}%" for v in stress_df["shock_pct"]],
            textposition="outside",
            textfont=dict(size=10, color=TEXT)))
        fig3.add_hline(y=0, line_color=BORD)
        fig3.update_layout(**PLOTLY, height=280,
            xaxis=dict(gridcolor=GRID, zeroline=False, tickangle=-15,
                tickfont=dict(color=TEXT2, size=9)),
            yaxis=ax("Shock (%)"))
        st.plotly_chart(fig3, use_container_width=True)

        st.dataframe(
            stress_df[["name","shock_pct","spot_orig","spot_shock","PnL (USD)","desc"]]
                .rename(columns={"name":"Escenario","shock_pct":"Shock (%)","spot_orig":"Spot",
                    "spot_shock":"Spot shockeado","desc":"Descripción"}),
            use_container_width=True, hide_index=True)

        worst = stress_df["PnL (USD)"].min()
        st.markdown(
            f'<div style="background:{BG3};border:1px solid {BORD};border-left:3px solid {PINK};'
            f'padding:10px 14px;border-radius:0 4px 4px 0;font-size:9px;color:{TEXT2};margin-top:12px;">'
            f'Worst scenario: P&amp;L = <strong style="color:{RED};">${worst:,.0f}</strong>'
            f' on position of ${position:,.0f} notional</div>',
            unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en stress: {e}")

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    c_rv, c_dd = st.columns(2)

    with c_rv:
        st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>ROLLING VaR (252d window)</div>", unsafe_allow_html=True)
        try:
            rvar = rolling_var(rets, 252, confidence, horizon)*100
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df.index[-len(rvar):], y=rvar,
                name=f"VaR {confidence*100:.0f}%",
                line=dict(color=PINK, width=1.5),
                fill="tozeroy", fillcolor="rgba(255,126,179,0.08)"))
            fig4.update_layout(**PLOTLY, height=260, xaxis=ax(), yaxis=ax("VaR (%)"))
            st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.error(f"Rolling VaR: {e}")

    with c_dd:
        st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>DRAWDOWN</div>", unsafe_allow_html=True)
        try:
            dd = drawdown_series(df["Close"])
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(x=df.index, y=dd,
                fill="tozeroy", fillcolor="rgba(255,68,85,0.12)",
                line=dict(color=RED, width=1), name="Drawdown"))
            fig5.add_hline(y=dd.min(), line_dash="dash", line_color=PINK,
                annotation_text=f"Max DD: {dd.min():.1f}%",
                annotation_font_color=PINK, annotation_font_size=9)
            fig5.update_layout(**PLOTLY, height=260, xaxis=ax(), yaxis=ax("Drawdown (%)"))
            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.error(f"Drawdown: {e}")

    st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin:16px 0 8px;'>VOL CONE</div>", unsafe_allow_html=True)
    try:
        cone = vol_cone(rets)
        if not cone.empty:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p90"],
                line=dict(color="rgba(255,126,179,0.3)", width=1, dash="dot"), showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["p10"],
                fill="tonexty", fillcolor="rgba(255,126,179,0.08)", name="P10-P90",
                line=dict(color="rgba(255,126,179,0.3)", width=1, dash="dot")))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["median"],
                name="Mediana", line=dict(color=PINK, width=1.5, dash="dash")))
            fig6.add_trace(go.Scatter(x=cone["label"], y=cone["current"],
                name="Vol actual", mode="markers+lines",
                marker=dict(size=8, color=ACC, symbol="diamond"),
                line=dict(color=ACC, width=2)))
            fig6.update_layout(**PLOTLY, height=260, xaxis=ax(), yaxis=ax("Vol ann. (%)"))
            st.plotly_chart(fig6, use_container_width=True)
    except Exception as e:
        st.error(f"Vol cone: {e}")

st.markdown(footer("Risk Dashboard"), unsafe_allow_html=True)
