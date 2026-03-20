"""pages/4_Risk_Dashboard.py — QCEX · Fixed + light/dark mode"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats as scipy_stats
from data.fetcher import fetch_prices, compute_returns, compute_stats, TICKERS
from analytics.risk import (historical_var, historical_cvar, parametric_var,
    rolling_var, stress_table, vol_cone, drawdown_series)

st.set_page_config(page_title="QCEX · Risk Dashboard", page_icon="◈", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

with st.sidebar:
    st.markdown("<div style='font-size:9px;letter-spacing:2px;margin-bottom:8px'>QCEX · RISK DASHBOARD</div>",unsafe_allow_html=True)
    dark = st.toggle("Modo oscuro", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark
    st.markdown("---")
    commodity   = st.selectbox("Commodity", list(TICKERS.keys()), format_func=lambda x: TICKERS[x]["name"])
    confidence  = st.select_slider("Confianza VaR", [0.95,0.99,0.995], value=0.99,
                    format_func=lambda x: f"{x*100:.1f}%")
    horizon     = st.select_slider("Horizonte (días)", [1,5,10,22], value=1)
    position    = st.number_input("Posición (USD notional)", value=1_000_000, step=100_000)

BG,BG2,GRID,TEXT,TEXT2,BORDER,ACC = (
    ("#07090D","#070C07","#1A0A1A","#C8B8C8","#3A1A2A","#1A0A1A","#FF7EB3") if dark else
    ("#FDF4F8","#FFFFFF","#F0D0E0","#2A0A1A","#5A2A3A","#DDAACC","#C01060")
)
st.markdown(f"""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{{font-family:'IBM Plex Mono',monospace!important;background:{BG};color:{TEXT}}}
  .stApp{{background:{BG}}}
  section[data-testid="stSidebar"]{{background:{BG2};border-right:1px solid {BORDER}}}
  h1,h2,h3{{color:{ACC}!important;font-family:'IBM Plex Mono',monospace!important}}
  [data-testid="metric-container"]{{background:{BG2};border:1px solid {BORDER};border-radius:4px;padding:8px 12px}}
  [data-testid="metric-container"] label{{color:{TEXT2}!important;font-size:10px}}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{{color:{ACC}!important}}
</style>""",unsafe_allow_html=True)

PL = dict(paper_bgcolor=BG,plot_bgcolor=BG,font=dict(family="IBM Plex Mono",color=TEXT2,size=10),margin=dict(l=50,r=20,t=35,b=40))
AX = dict(gridcolor=GRID,showgrid=True,zeroline=False)

@st.cache_data(ttl=3600)
def load(c):
    df    = fetch_prices(c, 504)
    rets  = compute_returns(df)
    stats = compute_stats(c, df)
    return df, rets, stats

df, rets, stats = load(commodity)
spot = stats["spot"]

st.markdown("## RISK DASHBOARD")

hvar = historical_var(rets, confidence, horizon)
cvar = historical_cvar(rets, confidence, horizon)
pvar = parametric_var(rets, confidence, horizon)

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(f"Hist. VaR {confidence*100:.0f}%", f"{hvar*100:.2f}%", f"${position*hvar:,.0f}")
c2.metric("CVaR / ES",                         f"{cvar*100:.2f}%", f"${position*cvar:,.0f}")
c3.metric("VaR Gaussiano",                     f"{pvar*100:.2f}%", f"${position*pvar:,.0f}")
c4.metric("Vol 1M (ann.)",  f"{stats['vol_1m']:.1f}%")
c5.metric("Skewness",       f"{stats['skewness']:.3f}",
    "cola izquierda" if stats['skewness']<-0.3 else "aprox. normal")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["DISTRIBUCIÓN & VAR","STRESS TESTING","ROLLING RISK"])

# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    col_hist, col_qq = st.columns(2)
    with col_hist:
        st.markdown("**DISTRIBUCIÓN DE RETORNOS + VaR**")
        r_pct = rets.dropna() * 100
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=r_pct,nbinsx=80,marker_color=ACC,opacity=0.7,name="Retornos"))
        fig.add_vline(x=-hvar*100, line_color="#FF2244", line_width=2,
            annotation_text=f"Hist. VaR {confidence*100:.0f}%",
            annotation_font_color="#FF2244", annotation_font_size=9)
        fig.add_vline(x=-cvar*100, line_color="#FF6644", line_width=1.5, line_dash="dash",
            annotation_text="CVaR", annotation_font_color="#FF6644", annotation_font_size=9)
        fig.update_layout(**PL,height=300,
            xaxis=dict(**AX,title="Retorno diario (%)"),
            yaxis=dict(**AX,title="Frecuencia"))
        st.plotly_chart(fig,use_container_width=True)

    with col_qq:
        st.markdown("**Q-Q PLOT vs NORMAL**")
        try:
            sorted_r = np.sort(rets.dropna().values)
            n = len(sorted_r)
            quantiles = scipy_stats.norm.ppf(np.arange(1,n+1)/(n+1),
                loc=sorted_r.mean(), scale=sorted_r.std())
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=quantiles*100, y=sorted_r*100,
                mode="markers", name="Datos",
                marker=dict(color=ACC,size=2,opacity=0.5)))
            lims = [min(quantiles.min(),sorted_r.min())*100,
                    max(quantiles.max(),sorted_r.max())*100]
            fig2.add_trace(go.Scatter(x=lims,y=lims,name="Normal",
                line=dict(color=BORDER,width=1,dash="dot")))
            fig2.update_layout(**PL,height=300,
                xaxis=dict(**AX,title="Cuantiles teóricos normales (%)"),
                yaxis=dict(**AX,title="Cuantiles observados (%)"),
                legend=dict(bgcolor=BG2,bordercolor=BORDER))
            st.plotly_chart(fig2,use_container_width=True)
        except Exception as e:
            st.error(f"Error en Q-Q plot: {e}")

    st.markdown("**COMPARATIVA VaR POR HORIZONTE**")
    rows_var = []
    for conf in [0.95,0.99,0.995]:
        row = {"Confianza":f"{conf*100:.1f}%"}
        for h in [1,5,10]:
            hv = historical_var(rets,conf,h)*100
            cv = historical_cvar(rets,conf,h)*100
            row[f"VaR {h}d (%)"] = f"{hv:.2f}"
            row[f"CVaR {h}d (%)"] = f"{cv:.2f}"
        rows_var.append(row)
    st.dataframe(pd.DataFrame(rows_var),hide_index=True,use_container_width=True)

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("**ESCENARIOS DE STRESS — P&L**")
    try:
        stress_df = stress_table(commodity, spot)
        stress_df["PnL (USD)"] = (stress_df["pnl"]/stress_df["spot_orig"]*position).round(0)

        fig3 = go.Figure()
        colors = ["#4AFF99" if v>=0 else "#FF2244" for v in stress_df["shock_pct"]]
        fig3.add_trace(go.Bar(x=stress_df["name"],y=stress_df["shock_pct"],
            marker_color=colors,opacity=0.85,
            text=[f"{v:+.0f}%" for v in stress_df["shock_pct"]],
            textposition="outside", textfont=dict(size=10,color=TEXT)))
        fig3.add_hline(y=0,line_color=BORDER)
        fig3.update_layout(**PL,height=280,
            xaxis=dict(gridcolor=GRID,zeroline=False,tickangle=-15),
            yaxis=dict(gridcolor=GRID,zeroline=False,title="Shock (%)"))
        st.plotly_chart(fig3,use_container_width=True)

        st.dataframe(
            stress_df[["name","shock_pct","spot_orig","spot_shock","PnL (USD)","desc"]]
                .rename(columns={"name":"Escenario","shock_pct":"Shock (%)","spot_orig":"Spot",
                    "spot_shock":"Spot shockeado","desc":"Descripción"}),
            use_container_width=True, hide_index=True)

        worst = stress_df["PnL (USD)"].min()
        st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};border-left:3px solid {ACC};
          padding:10px 14px;border-radius:0 4px 4px 0;font-size:10px;color:{TEXT2};margin-top:12px'>
          Peor escenario: P&L = <strong style='color:#FF2244'>${worst:,.0f}</strong>
          sobre posición de ${position:,.0f} notional
        </div>""",unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en stress testing: {e}")

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    col_rvar, col_dd = st.columns(2)

    with col_rvar:
        st.markdown("**ROLLING VAR (252d)**")
        try:
            rvar = rolling_var(rets, window=252, confidence=confidence, horizon=horizon)*100
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df.index[-len(rvar):], y=rvar,
                name=f"VaR {confidence*100:.0f}%",
                line=dict(color=ACC,width=1.5),
                fill="tozeroy", fillcolor="rgba(255,126,179,0.09)"))
            fig4.update_layout(**PL,height=280,
                xaxis=dict(**AX),yaxis=dict(**AX,title="VaR (%)"))
            st.plotly_chart(fig4,use_container_width=True)
        except Exception as e:
            st.error(f"Error en rolling VaR: {e}")

    with col_dd:
        st.markdown("**DRAWDOWN**")
        try:
            dd = drawdown_series(df["Close"])
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(x=df.index, y=dd,
                fill="tozeroy", fillcolor="#FF2244",
                line=dict(color="#FF2244",width=1), name="Drawdown"))
            fig5.add_hline(y=dd.min(), line_dash="dash", line_color=ACC,
                annotation_text=f"Max DD: {dd.min():.1f}%",
                annotation_font_color=ACC, annotation_font_size=9)
            fig5.update_layout(**PL,height=280,
                xaxis=dict(**AX),yaxis=dict(**AX,title="Drawdown (%)"))
            st.plotly_chart(fig5,use_container_width=True)
        except Exception as e:
            st.error(f"Error en drawdown: {e}")

    st.markdown("**VOL CONE**")
    try:
        cone = vol_cone(rets)
        if not cone.empty:
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p90"],
                line=dict(color="rgba(255,126,179,0.27)",width=1,dash="dot"),showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p10"],
                fill="tonexty",fillcolor="rgba(255,126,179,0.08)",name="P10–P90",
                line=dict(color="rgba(255,126,179,0.27)",width=1,dash="dot")))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p75"],
                line=dict(color="rgba(255,126,179,0.53)",width=1),showlegend=False))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["p25"],
                fill="tonexty",fillcolor="rgba(255,126,179,0.15)",name="P25–P75",
                line=dict(color="rgba(255,126,179,0.53)",width=1)))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["median"],
                name="Mediana",line=dict(color=ACC,width=1.5,dash="dash")))
            fig6.add_trace(go.Scatter(x=cone["label"],y=cone["current"],
                name="Vol actual",mode="markers+lines",
                marker=dict(size=10,color="#4AFF99",symbol="diamond"),
                line=dict(color="#4AFF99",width=2)))
            fig6.update_layout(**PL,height=280,
                xaxis=dict(**AX),yaxis=dict(**AX,title="Vol ann. (%)"),
                legend=dict(bgcolor=BG2,bordercolor=BORDER))
            st.plotly_chart(fig6,use_container_width=True)
    except Exception as e:
        st.error(f"Error en vol cone: {e}")

st.markdown(f"""<div style="border-top:1px solid {BORDER};padding-top:14px;margin-top:32px;
  display:flex;justify-content:space-between;align-items:center;">
  <div style="color:{ACC};font-size:11px;font-weight:600;letter-spacing:2px;">QCEX</div>
  <div style="color:{TEXT2};font-size:8px;">by <strong>QuantumPablo</strong> · Pablo M. Paniagua</div>
</div>""",unsafe_allow_html=True)
