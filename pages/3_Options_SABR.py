"""
app/pages/3_Options_SABR.py
============================
Options pricing with SABR vol surface + Black-76.
Greeks, smile calibration, 3D surface visualization.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data.fetcher import fetch_prices, compute_stats, TICKERS
from models.sabr import SABRModel, sabr_implied_vol, black76

st.set_page_config(page_title="QCEX · Options · SABR", page_icon="◈", layout="wide")
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{font-family:'IBM Plex Mono',monospace!important;background:#07090d;color:#b8ccb8}
  .stApp{background:#07090d}
  section[data-testid="stSidebar"]{background:#070c0a;border-right:1px solid #0f1f0f}
  h1,h2,h3{color:#7ec8ff!important;font-family:'IBM Plex Mono',monospace!important}
  [data-testid="metric-container"]{background:#070c07;border:1px solid #0a1a2a;border-radius:4px;padding:8px 12px}
  [data-testid="metric-container"] label{color:#1a2a3a!important;font-size:10px}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{color:#7ec8ff!important}
</style>""", unsafe_allow_html=True)

LAYOUT = dict(
    paper_bgcolor="#07090d", plot_bgcolor="#07090d",
    font=dict(family="IBM Plex Mono", color="#2a3a4a", size=10),
    xaxis=dict(gridcolor="#0a1a2a"), yaxis=dict(gridcolor="#0a1a2a"),
    margin=dict(l=50, r=20, t=30, b=40),
)

SABR_PRESETS = {
    "cocoa"  : dict(alpha=0.52, beta=0.5, rho=-0.45, nu=0.68),
    "gas"    : dict(alpha=0.65, beta=0.5, rho=-0.25, nu=0.85),
    "uranium": dict(alpha=0.35, beta=0.5, rho=-0.15, nu=0.42),
}
MATURITIES = {"1M":1/12,"3M":3/12,"6M":0.5,"1Y":1.0,"18M":1.5,"2Y":2.0}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='color:#2a4a6a;font-size:9px;letter-spacing:2px;margin-bottom:8px'>OPTIONS · SABR</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", list(SABR_PRESETS.keys()),
                              format_func=lambda x: TICKERS[x]["name"])
    mat_key   = st.selectbox("Maturity (smile)", list(MATURITIES.keys()), index=2)
    T         = MATURITIES[mat_key]
    sp        = SABR_PRESETS[commodity]
    st.markdown("---")
    st.markdown("<div style='color:#2a4a6a;font-size:9px;letter-spacing:1px;margin-bottom:6px'>SABR PARAMETERS</div>", unsafe_allow_html=True)
    alpha = st.slider("α (vol level)",    0.01, 1.5,  float(sp["alpha"]), 0.01)
    beta  = st.slider("β (CEV)",          0.0,  1.0,  float(sp["beta"]),  0.01)
    rho   = st.slider("ρ (skew corr)",   -0.99, 0.99, float(sp["rho"]),  0.01)
    nu    = st.slider("ν (vol of vol)",   0.01, 2.0,  float(sp["nu"]),   0.01)
    st.markdown("---")
    st.markdown("<div style='color:#2a4a6a;font-size:9px;letter-spacing:1px;margin-bottom:6px'>OPTION PRICER</div>", unsafe_allow_html=True)
    k_pct  = st.slider("Strike (% ATM)",  70, 130, 100)
    r_rate = st.slider("r (risk-free)",  0.0, 0.10, 0.05, 0.005)

@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats = load(commodity)
F     = stats["spot"]
K     = F * k_pct / 100
model = SABRModel(alpha=alpha, beta=beta, rho=rho, nu=nu)

st.markdown("## 📉 OPTIONS PRICER — SABR VOL SURFACE")

# ── Pricing metrics ────────────────────────────────────────────────────────────
sigma_k = model.implied_vol(F, K, T)
call_p  = model.price(F, K, r_rate, T, "call")
put_p   = model.price(F, K, r_rate, T, "put")
atm_v   = model.implied_vol(F, F, T)
g       = model.greeks(F, K, r_rate, T)

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Forward F",  f"{F:,.2f}")
c2.metric("Strike K",   f"{K:,.2f}", f"{k_pct}% ATM")
c3.metric("σ_ATM",      f"{atm_v*100:.2f}%")
c4.metric("σ(K)",       f"{sigma_k*100:.2f}%")
c5.metric("Call",       f"{call_p:.3f}")
c6.metric("Put",        f"{put_p:.3f}")

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["VOL SMILE", "3D SURFACE", "GREEKS", "CALIBRATION"])

# ── TAB 1: Smile ──────────────────────────────────────────────────────────────
with tab1:
    moneyness = np.linspace(0.70, 1.30, 31)
    smile_df  = pd.DataFrame({
        "m"  : moneyness,
        "K"  : F * moneyness,
        "iv" : [model.implied_vol(F, F*m, T)*100 for m in moneyness],
    })
    col_s, col_i = st.columns([3, 1])
    with col_s:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=smile_df["m"]*100, y=smile_df["iv"],
            name="SABR σ_impl",
            line=dict(color="#7ec8ff", width=2.5),
            fill="tozeroy", fillcolor="#7ec8ff10",
        ))
        fig.add_vline(x=100, line_dash="dot", line_color="#2a4a6a",
                      annotation_text="ATM")
        fig.add_vline(x=k_pct, line_dash="dash", line_color="#4aff99",
                      annotation_text=f"K={k_pct}%")
        fig.update_layout(**LAYOUT, height=320,
                          xaxis_title="Strike (% ATM)", yaxis_title="Impl. Vol (%)")
        st.plotly_chart(fig, use_container_width=True)
    with col_i:
        st.markdown("**SMILE METRICS**")
        skw = model.skew(F, T)*1e4
        fly = model.butterfly(F, T)*1e4
        for label, val, color in [
            ("ATM Vol",    f"{atm_v*100:.2f}%",    "#7ec8ff"),
            ("Skew (bp)",  f"{skw:+.1f}",          "#ff7eb3" if skw>0 else "#4aff99"),
            ("Butterfly",  f"{fly:.1f} bp",         "#f5d060"),
            ("ρ→skew",    f"{rho:.3f}",             "#ff7eb3"),
            ("ν→smile",   f"{nu:.3f}",              "#4aff99"),
        ]:
            st.markdown(f"""<div style='background:#070c07;border:1px solid #0a1a2a;padding:8px 12px;
              border-radius:4px;margin-bottom:6px'>
              <div style='color:#2a4a6a;font-size:8px'>{label}</div>
              <div style='color:{color};font-size:15px;font-weight:600'>{val}</div>
            </div>""", unsafe_allow_html=True)

# ── TAB 2: 3D Surface ─────────────────────────────────────────────────────────
with tab2:
    surf = model.vol_surface(F,
        maturities=[1/12,2/12,3/12,6/12,9/12,1.0,1.5,2.0],
        moneyness=np.linspace(0.70,1.30,21))
    T_labels = ["1M","2M","3M","6M","9M","1Y","18M","2Y"]
    K_labels = [f"{m*100:.0f}%" for m in surf["moneyness"]]
    fig3d = go.Figure(go.Surface(
        z=surf["vols_pct"],
        x=surf["moneyness"]*100,
        y=list(range(len(surf["maturities"]))),
        colorscale=[[0,"#0a1a2a"],[0.3,"#1a4a7a"],[0.6,"#4a9eff"],[0.8,"#7ec8ff"],[1,"#ffffff"]],
        opacity=0.92,
        contours=dict(z=dict(show=True, usecolormap=True, highlightcolor="#7ec8ff", project_z=True)),
        hovertemplate="Strike: %{x:.0f}%<br>Vol: %{z:.2f}%<extra></extra>",
    ))
    fig3d.update_layout(
        paper_bgcolor="#07090d", plot_bgcolor="#07090d",
        scene=dict(
            bgcolor="#07090d",
            xaxis=dict(title="Strike (% ATM)", gridcolor="#0a1a2a", color="#2a4a6a"),
            yaxis=dict(title="Maturity", tickvals=list(range(len(surf["maturities"]))),
                       ticktext=T_labels, gridcolor="#0a1a2a", color="#2a4a6a"),
            zaxis=dict(title="Impl. Vol (%)", gridcolor="#0a1a2a", color="#2a4a6a"),
            camera=dict(eye=dict(x=1.5, y=-1.8, z=0.8)),
        ),
        font=dict(family="IBM Plex Mono", color="#2a4a6a"),
        height=520, margin=dict(l=0,r=0,t=30,b=0),
    )
    st.plotly_chart(fig3d, use_container_width=True)

# ── TAB 3: Greeks ─────────────────────────────────────────────────────────────
with tab3:
    col_g, col_chart = st.columns([1, 2])
    with col_g:
        st.markdown("**GREEKS (CALL)**")
        greek_info = [
            ("Δ Delta",  g["delta"],   "∂V/∂F",   "#4aff99", "Exposición directional al forward"),
            ("Γ Gamma",  g["gamma"],   "∂²V/∂F²", "#f5d060", "Convexidad. Δ cambia por unidad de F"),
            ("ν Vega",   g["vega"],    "∂V/∂σ",   "#7ec8ff", "Sensibilidad a vol implícita"),
            ("Θ Theta",  g["theta"],   "∂V/∂t/yr",  "#ff7eb3", "Decaimiento temporal (diario)"),
            ("Vanna",    g["vanna"],   "∂²V/∂F∂σ","#c8c8ff", "Mixta F-vol. Clave en barrier pricing"),
            ("Volga",    g["volga"],   "∂²V/∂σ²", "#ffc8c8", "Convexidad de vol. Captura vol smile risk"),
        ]
        for name, val, formula, color, desc in greek_info:
            st.markdown(f"""<div style='background:#070c07;border:1px solid #0a1a2a;
              border-left:3px solid {color};padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px'>
              <div style='display:flex;justify-content:space-between;align-items:baseline'>
                <span style='color:{color};font-size:11px;font-weight:600'>{name}</span>
                <span style='color:{color};font-size:16px;font-weight:700'>{val:.5f}</span>
              </div>
              <div style='color:#2a4a6a;font-size:8px;margin-top:3px'>{formula} · {desc}</div>
            </div>""", unsafe_allow_html=True)

    with col_chart:
        st.markdown("**DELTA vs STRIKE PROFILE**")
        strikes_range = np.linspace(F*0.5, F*1.5, 80)
        deltas = [model.greeks(F, K_, r_rate, T)["delta"] for K_ in strikes_range]
        gammas = [model.greeks(F, K_, r_rate, T)["gamma"] * F * 0.01 for K_ in strikes_range]
        fig_g = go.Figure()
        fig_g.add_trace(go.Scatter(x=strikes_range/F*100, y=deltas,
            name="Delta", line=dict(color="#4aff99", width=2)))
        fig_g.add_trace(go.Scatter(x=strikes_range/F*100, y=gammas,
            name="Gamma (×F×1%)", line=dict(color="#f5d060", width=2, dash="dash"),
            yaxis="y2"))
        fig_g.add_vline(x=k_pct, line_dash="dash", line_color="#7ec8ff44")
        fig_g.add_hline(y=0.5, line_dash="dot", line_color="#1a3a1a")
        fig_g.update_layout(**LAYOUT, height=330,
            xaxis_title="Strike (% ATM)",
            yaxis=dict(title="Delta", gridcolor="#0a1a2a", range=[-0.1,1.1]),
            yaxis2=dict(title="Gamma", overlaying="y", side="right",
                        showgrid=False, color="#f5d060"),
            legend=dict(bgcolor="#070c07", bordercolor="#0a1a2a"))
        st.plotly_chart(fig_g, use_container_width=True)

# ── TAB 4: Calibration ────────────────────────────────────────────────────────
with tab4:
    st.markdown("**CALIBRACIÓN SABR A SMILE DE MERCADO**")
    st.markdown("""<div style='background:#0a1020;border:1px solid #0a1a2a;border-left:3px solid #7ec8ff;
      padding:10px 14px;border-radius:0 4px 4px 0;font-size:10px;color:#2a4a6a;margin-bottom:16px'>
      Introduce vols de mercado (en %) por strike. El modelo calibra (α, ρ, ν) vía WLS.
      β se fija externamente (β=0.5 estándar para commodities).
    </div>""", unsafe_allow_html=True)

    default_moneyness = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
    default_vols = [model.implied_vol(F, F*m, T)*100 + np.random.normal(0, 0.3)
                    for m in default_moneyness]
    calib_df = pd.DataFrame({
        "Strike (% ATM)": [f"{m*100:.0f}%" for m in default_moneyness],
        "Strike"        : [round(F*m, 2) for m in default_moneyness],
        "Mkt IV (%)"    : [round(v, 2) for v in default_vols],
    })
    edited = st.data_editor(calib_df[["Strike (% ATM)","Mkt IV (%)"]], use_container_width=True,
                             hide_index=True, num_rows="fixed")

    if st.button("▶ CALIBRAR"):
        strikes_cal = np.array([F * float(r.replace("%",""))/100
                                 for r in edited["Strike (% ATM)"]])
        vols_cal    = np.array(edited["Mkt IV (%)"].values, dtype=float) / 100
        with st.spinner("Calibrando..."):
            fitted = SABRModel.calibrate(strikes_cal, vols_cal, F=F, T=T, beta=beta)
        r = fitted._calib_result
        st.success(f"✓ Calibración completada — RMSE: {r['rmse_bp']:.1f} bp")
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("α calibrado", f"{fitted.alpha:.4f}", f"{fitted.alpha-alpha:+.4f} vs prior")
        col_r2.metric("ρ calibrado", f"{fitted.rho:.4f}",  f"{fitted.rho-rho:+.4f} vs prior")
        col_r3.metric("ν calibrado", f"{fitted.nu:.4f}",   f"{fitted.nu-nu:+.4f} vs prior")

        fig_cal = go.Figure()
        m_range = np.linspace(0.75, 1.25, 40)
        fig_cal.add_trace(go.Scatter(
            x=m_range*100,
            y=[fitted.implied_vol(F, F*m, T)*100 for m in m_range],
            name="Calibrado", line=dict(color="#7ec8ff", width=2)))
        fig_cal.add_trace(go.Scatter(
            x=m_range*100,
            y=[model.implied_vol(F, F*m, T)*100 for m in m_range],
            name="Prior", line=dict(color="#3a3a3a", width=1.5, dash="dot")))
        fig_cal.add_trace(go.Scatter(
            x=[float(r.replace("%","")) for r in edited["Strike (% ATM)"]],
            y=list(edited["Mkt IV (%)"]),
            name="Market", mode="markers",
            marker=dict(color="#4aff99", size=9, symbol="circle")))
        fig_cal.update_layout(**LAYOUT, height=300,
                              xaxis_title="Strike (% ATM)", yaxis_title="Impl. Vol (%)")
        st.plotly_chart(fig_cal, use_container_width=True)

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

