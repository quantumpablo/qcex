"""pages/2_Futures_Pricer.py — QCEX · Fixed MC + light/dark mode"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from data.fetcher import compute_stats, build_term_structure, TICKERS
from models.schwartz_smith import simulate_paths, half_life

st.set_page_config(page_title="QCEX · Futures Pricer", page_icon="◈", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

PRESETS = {
    "cocoa":   dict(kappa=0.80,mu_xi=0.03,sigma_chi=0.38,sigma_xi=0.18,rho=-0.25,lambda_chi=-0.10,lambda_xi=-0.05,r=0.053,u=0.025),
    "gas":     dict(kappa=2.10,mu_xi=0.00,sigma_chi=0.55,sigma_xi=0.22,rho=-0.15,lambda_chi=-0.08,lambda_xi=-0.03,r=0.038,u=0.015),
    "uranium": dict(kappa=0.30,mu_xi=0.05,sigma_chi=0.28,sigma_xi=0.15,rho=-0.10,lambda_chi=-0.05,lambda_xi=-0.02,r=0.053,u=0.008),
}

with st.sidebar:
    st.markdown("<div style='font-size:9px;letter-spacing:2px;margin-bottom:8px'>QCEX · FUTURES PRICER</div>", unsafe_allow_html=True)
    dark = st.toggle("Modo oscuro", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark
    st.markdown("---")
    commodity = st.selectbox("Commodity", ["cocoa","gas","uranium"], format_func=lambda x: TICKERS[x]["name"])
    p = PRESETS[commodity].copy()
    st.markdown("<div style='font-size:9px;letter-spacing:1px;margin:8px 0 4px'>SCHWARTZ-SMITH PARAMS</div>", unsafe_allow_html=True)
    kappa      = st.slider("κ  mean-rev speed",   0.1,  5.0,  float(p["kappa"]),   0.05)
    mu_xi      = st.slider("μξ long-term drift",  -0.2,  0.2,  float(p["mu_xi"]),   0.01)
    sigma_chi  = st.slider("σχ short-term vol",    0.05, 1.5,  float(p["sigma_chi"]),0.01)
    sigma_xi   = st.slider("σξ long-term vol",     0.02, 0.8,  float(p["sigma_xi"]), 0.01)
    rho_ss     = st.slider("ρ  correlation",       -0.95, 0.95, float(p["rho"]),    0.05)
    lambda_chi = st.slider("λχ S-T risk prem.",   -1.0,  1.0,  float(p["lambda_chi"]),0.01)
    lambda_xi  = st.slider("λξ L-T risk prem.",   -0.5,  0.5,  float(p["lambda_xi"]), 0.01)
    r_rate     = st.slider("r  risk-free",          0.0,  0.10, float(p["r"]),      0.005)
    u_cost     = st.slider("u  storage cost",       0.0,  0.05, float(p["u"]),      0.001)

params = dict(kappa=kappa,mu_xi=mu_xi,sigma_chi=sigma_chi,sigma_xi=sigma_xi,
              rho=rho_ss,lambda_chi=lambda_chi,lambda_xi=lambda_xi)

BG,BG2,GRID,TEXT,TEXT2,BORDER,ACC = (
    ("#07090D","#070C07","#100E00","#C8C890","#3A3A1A","#1A1A0A","#F5D060") if dark else
    ("#FAFAF4","#FFFFFF","#E8E8D0","#2A2A0A","#4A4A2A","#CCCC88","#A07800")
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
</style>""", unsafe_allow_html=True)

PL  = dict(paper_bgcolor=BG,plot_bgcolor=BG,font=dict(family="IBM Plex Mono",color=TEXT2,size=10),margin=dict(l=50,r=20,t=35,b=40))
AX  = dict(gridcolor=GRID,showgrid=True,zeroline=False)

@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats = load(commodity)
spot  = stats["spot"]
unit  = TICKERS[commodity]["unit"]
hl    = half_life(kappa)

st.markdown("## FUTURES PRICER — SCHWARTZ-SMITH 2-FACTOR")
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Spot",f"{spot:,.2f} {unit}")
c2.metric("Half-life χ",f"{hl*12:.1f} meses",f"κ={kappa:.2f}")
c3.metric("Vol corto",f"{sigma_chi*100:.0f}%")
c4.metric("Vol largo",f"{sigma_xi*100:.0f}%")
c5.metric("Corr. ρ",f"{rho_ss:.2f}")
st.markdown("---")

alpha_lr = np.log(spot)
ts = build_term_structure(spot,r_rate,u_cost,kappa,alpha_lr,sigma_chi,lambda_chi)
contango = ts["futures"].iloc[-1] > ts["futures"].iloc[0]
slabel   = "▲ CONTANGO" if contango else "▼ BACKWARDATION"
scolor   = "#FF9944" if contango else ACC

col_chart, col_table = st.columns([2,1])

with col_chart:
    st.markdown(f"### CURVA DE FUTUROS &nbsp;<span style='color:{scolor};font-size:12px'>{slabel}</span>",unsafe_allow_html=True)
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2,cols=1,row_heights=[0.65,0.35],shared_xaxes=True,vertical_spacing=0.08)
    fig.add_trace(go.Scatter(x=ts["label"],y=ts["futures"],name="Futures (model)",
        mode="lines+markers",line=dict(color=ACC,width=2.5),marker=dict(size=8,color=ACC)),row=1,col=1)
    fig.add_hline(y=spot,line_dash="dot",line_color=BORDER,
        annotation_text=f"Spot {spot:.2f}",row=1,col=1)
    bar_colors = [ACC if v>=0 else "#FF5544" for v in ts["cy"]]
    fig.add_trace(go.Bar(x=ts["label"],y=ts["cy"],name="Conv. Yield (%)",
        marker_color=bar_colors,opacity=0.8),row=2,col=1)
    fig.add_hline(y=0,line_color=BORDER,row=2,col=1)
    fig.update_layout(**PL,height=420,showlegend=True,
        legend=dict(bgcolor=BG2,bordercolor=BORDER))
    fig.update_yaxes(title_text=unit,row=1,col=1,gridcolor=GRID,zeroline=False)
    fig.update_yaxes(title_text="CY (%)",row=2,col=1,gridcolor=GRID,zeroline=False)
    fig.update_xaxes(gridcolor=GRID,zeroline=False)
    st.plotly_chart(fig,use_container_width=True)

with col_table:
    st.markdown("### TERM STRUCTURE")
    display = ts[["label","futures","basis","cy"]].copy()
    display.columns = ["Maturity","Futures","Basis","CY (%)"]
    display["Futures"] = display["Futures"].apply(lambda x: f"{x:,.2f}")
    display["Basis"]   = display["Basis"].apply(lambda x: f"{x:+,.2f}")
    display["CY (%)"]  = display["CY (%)"].apply(lambda x: f"{x:+.3f}%")
    st.dataframe(display,hide_index=True,use_container_width=True)
    st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};border-left:3px solid {ACC};
      padding:10px;border-radius:0 4px 4px 0;margin-top:12px;font-size:10px;color:{TEXT2}'>
      <div style='color:{ACC};font-size:9px;letter-spacing:1px;margin-bottom:6px'>MODELO</div>
      ln F(t,T) = e<sup>-κτ</sup>χ + ξ + A(τ)<br>
      Half-life χ = <strong style='color:{ACC}'>{hl*12:.1f} meses</strong><br>
      CY = r + u − (1/T)·ln(F/S)
    </div>""",unsafe_allow_html=True)

# ── Monte Carlo ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### SIMULACIÓN MONTE CARLO")

col_mc, col_params = st.columns([3,1])
with col_params:
    n_paths = st.select_slider("Paths", [100,500,1000], value=500)
    horizon = st.slider("Horizonte (años)", 0.5, 3.0, 1.0, 0.25)

with col_mc:
    try:
        chi0, xi0 = 0.0, np.log(max(spot, 0.01))
        sim  = simulate_paths(params, chi0, xi0, T_years=horizon, dt=1/52,
                              n_paths=min(n_paths, 1000), seed=42)
        pcts  = np.percentile(sim["spot"], [5,25,50,75,95], axis=0)
        times = sim["times"]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=times,y=pcts[4],line=dict(color="rgba(245,208,96,0.27)",width=1),showlegend=False))
        fig2.add_trace(go.Scatter(x=times,y=pcts[0],name="5–95%",fill="tonexty",
            fillcolor="rgba(245,208,96,0.08)",line=dict(color="rgba(245,208,96,0.27)",width=1)))
        fig2.add_trace(go.Scatter(x=times,y=pcts[3],line=dict(color="rgba(245,208,96,0.53)",width=1),showlegend=False))
        fig2.add_trace(go.Scatter(x=times,y=pcts[1],name="25–75%",fill="tonexty",
            fillcolor="rgba(245,208,96,0.16)",line=dict(color="rgba(245,208,96,0.53)",width=1)))
        fig2.add_trace(go.Scatter(x=times,y=pcts[2],name="Mediana",
            line=dict(color=ACC,width=2)))
        fig2.add_hline(y=np.exp(xi0),line_dash="dash",line_color=BORDER,
            annotation_text="Equil. L-T")
        fig2.update_layout(**PL,height=300,
            xaxis=dict(**AX,title="Años"),yaxis=dict(**AX,title=unit),
            legend=dict(bgcolor=BG2,bordercolor=BORDER,font=dict(size=9)))
        st.plotly_chart(fig2,use_container_width=True)

        S_T = sim["spot"][:,-1]
        cols_stat = st.columns(5)
        for col, (label, val) in zip(cols_stat, [
            ("E[S_T]",f"{np.mean(S_T):,.1f}"),("Median",f"{np.median(S_T):,.1f}"),
            ("Std",f"{np.std(S_T):,.1f}"),("P5",f"{np.percentile(S_T,5):,.1f}"),
            ("P95",f"{np.percentile(S_T,95):,.1f}")]):
            with col:
                st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};
                  padding:10px;border-radius:4px;text-align:center'>
                  <div style='color:{TEXT2};font-size:8px;letter-spacing:1px'>{label}</div>
                  <div style='color:{ACC};font-size:14px;font-weight:600'>{val}</div>
                </div>""",unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en simulación Monte Carlo: {e}")

st.markdown(f"""<div style="border-top:1px solid {BORDER};padding-top:14px;margin-top:32px;
  display:flex;justify-content:space-between;align-items:center;">
  <div style="color:{ACC};font-size:11px;font-weight:600;letter-spacing:2px;">QCEX</div>
  <div style="color:{TEXT2};font-size:8px;">by <strong>QuantumPablo</strong> · Pablo M. Paniagua</div>
</div>""",unsafe_allow_html=True)
