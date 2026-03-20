"""pages/3_Options_SABR.py — QCEX · Fixed + light/dark mode"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from data.fetcher import compute_stats, TICKERS
from models.sabr import SABRModel, black76

st.set_page_config(page_title="QCEX · Options · SABR", page_icon="◈", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

SABR_PRESETS = {
    "cocoa":   dict(alpha=0.52,beta=0.5,rho=-0.45,nu=0.68),
    "gas":     dict(alpha=0.65,beta=0.5,rho=-0.25,nu=0.85),
    "uranium": dict(alpha=0.35,beta=0.5,rho=-0.15,nu=0.42),
}
MATURITIES = {"1M":1/12,"3M":3/12,"6M":0.5,"1Y":1.0,"18M":1.5,"2Y":2.0}

with st.sidebar:
    st.markdown("<div style='font-size:9px;letter-spacing:2px;margin-bottom:8px'>QCEX · OPTIONS · SABR</div>",unsafe_allow_html=True)
    dark = st.toggle("Modo oscuro", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark
    st.markdown("---")
    commodity = st.selectbox("Commodity", list(SABR_PRESETS.keys()), format_func=lambda x: TICKERS[x]["name"])
    mat_key   = st.selectbox("Maturity", list(MATURITIES.keys()), index=2)
    T         = MATURITIES[mat_key]
    sp        = SABR_PRESETS[commodity]
    st.markdown("<div style='font-size:9px;letter-spacing:1px;margin:8px 0 4px'>SABR PARAMS</div>",unsafe_allow_html=True)
    alpha  = st.slider("α  vol level",   0.01, 1.5,  float(sp["alpha"]), 0.01)
    beta   = st.slider("β  CEV",         0.0,  1.0,  float(sp["beta"]),  0.01)
    rho    = st.slider("ρ  skew corr",  -0.99, 0.99, float(sp["rho"]),   0.01)
    nu     = st.slider("ν  vol of vol",  0.01, 2.0,  float(sp["nu"]),    0.01)
    st.markdown("---")
    k_pct  = st.slider("Strike (% ATM)", 70, 130, 100)
    r_rate = st.slider("r risk-free",    0.0, 0.10, 0.05, 0.005)

BG,BG2,GRID,TEXT,TEXT2,BORDER,ACC = (
    ("#07090D","#070C07","#0A1A2A","#C8D6E8","#2A3A4A","#0A1A2A","#7EC8FF") if dark else
    ("#F4F8FC","#FFFFFF","#D0E4F4","#1A2A3A","#3A4A5A","#AACCEE","#1A6A9A")
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
def load(c): return compute_stats(c)

stats = load(commodity)
F     = stats["spot"]
K     = F * k_pct / 100

try:
    model    = SABRModel(alpha=alpha, beta=beta, rho=rho, nu=nu)
    sigma_k  = model.implied_vol(F, K, T)
    atm_v    = model.implied_vol(F, F, T)
    call_p   = model.price(F, K, r_rate, T, "call")
    put_p    = model.price(F, K, r_rate, T, "put")
    g        = model.greeks(F, K, r_rate, T)
    skw      = model.skew(F, T) * 1e4
    fly      = model.butterfly(F, T) * 1e4
except Exception as e:
    st.error(f"Error inicializando modelo SABR: {e}")
    st.stop()

st.markdown("## OPTIONS · SABR VOL SURFACE")

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Forward F",  f"{F:,.2f}")
c2.metric("Strike K",   f"{K:,.2f}", f"{k_pct}% ATM")
c3.metric("σ_ATM",      f"{atm_v*100:.2f}%")
c4.metric("σ(K)",       f"{sigma_k*100:.2f}%")
c5.metric("Call",       f"{call_p:.3f}")
c6.metric("Put",        f"{put_p:.3f}")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["VOL SMILE","3D SURFACE","GREEKS","CALIBRACIÓN"])

# ── TAB 1: Smile ──────────────────────────────────────────────────────────────
with tab1:
    try:
        moneyness = np.linspace(0.70, 1.30, 31)
        smile_iv  = [model.implied_vol(F, F*m, T)*100 for m in moneyness]

        col_s, col_i = st.columns([3,1])
        with col_s:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=moneyness*100, y=smile_iv, name="SABR σ_impl",
                line=dict(color=ACC,width=2.5), fill="tozeroy", fillcolor="rgba(126,200,255,0.08)"))
            fig.add_vline(x=100, line_dash="dot", line_color=BORDER, annotation_text="ATM")
            fig.add_vline(x=k_pct, line_dash="dash", line_color="#4AFF99",
                annotation_text=f"K={k_pct}%")
            fig.update_layout(**PL, height=320,
                xaxis=dict(**AX,title="Strike (% ATM)"),
                yaxis=dict(**AX,title="Impl. Vol (%)"))
            st.plotly_chart(fig, use_container_width=True)

        with col_i:
            st.markdown("**SMILE METRICS**")
            for label, val, color in [
                ("ATM Vol",   f"{atm_v*100:.2f}%",  ACC),
                ("Skew (bp)", f"{skw:+.1f}",         "#FF7EB3" if skw>0 else "#4AFF99"),
                ("Butterfly", f"{fly:.1f} bp",        "#F5D060"),
                ("ρ → skew",  f"{rho:.3f}",           "#FF7EB3"),
                ("ν → smile", f"{nu:.3f}",            "#4AFF99"),
            ]:
                st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};padding:8px 12px;
                  border-radius:4px;margin-bottom:6px'>
                  <div style='color:{TEXT2};font-size:8px'>{label}</div>
                  <div style='color:{color};font-size:15px;font-weight:600'>{val}</div>
                </div>""",unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en smile: {e}")

# ── TAB 2: 3D Surface ─────────────────────────────────────────────────────────
with tab2:
    try:
        surf = model.vol_surface(F,
            maturities=[1/12,2/12,3/12,6/12,9/12,1.0,1.5,2.0],
            moneyness=np.linspace(0.70,1.30,21))
        T_labels = ["1M","2M","3M","6M","9M","1Y","18M","2Y"]

        cs_dark  = [[0,"#0a1a2a"],[0.3,"#1a4a7a"],[0.6,"#4a9eff"],[0.8,"#7ec8ff"],[1,"#ffffff"]]
        cs_light = [[0,"#e0f0ff"],[0.3,"#90c8f0"],[0.6,"#4090d0"],[0.8,"#1060a0"],[1,"#002060"]]

        fig3d = go.Figure(go.Surface(
            z=surf["vols_pct"], x=surf["moneyness"]*100,
            y=list(range(len(surf["maturities"]))),
            colorscale=cs_dark if dark else cs_light, opacity=0.92,
            hovertemplate="Strike: %{x:.0f}%<br>Vol: %{z:.2f}%<extra></extra>",
        ))
        fig3d.update_layout(
            paper_bgcolor=BG, height=500,
            scene=dict(
                bgcolor=BG,
                xaxis=dict(title="Strike (% ATM)",gridcolor=GRID,color=TEXT2),
                yaxis=dict(title="Maturity",tickvals=list(range(len(surf["maturities"]))),
                    ticktext=T_labels,gridcolor=GRID,color=TEXT2),
                zaxis=dict(title="Impl. Vol (%)",gridcolor=GRID,color=TEXT2),
                camera=dict(eye=dict(x=1.5,y=-1.8,z=0.8)),
            ),
            font=dict(family="IBM Plex Mono",color=TEXT2),
            margin=dict(l=0,r=0,t=30,b=0),
        )
        st.plotly_chart(fig3d, use_container_width=True)
    except Exception as e:
        st.error(f"Error en superficie 3D: {e}")

# ── TAB 3: Greeks ─────────────────────────────────────────────────────────────
with tab3:
    try:
        col_g, col_chart = st.columns([1,2])
        with col_g:
            st.markdown("**GREEKS (CALL)**")
            greek_info = [
                ("Δ Delta",  g["delta"],   "∂V/∂F",    "#4AFF99"),
                ("Γ Gamma",  g["gamma"],   "∂²V/∂F²",  "#F5D060"),
                ("ν Vega",   g["vega"],    "∂V/∂σ",    ACC),
                ("Θ Theta",  g["theta"],   "∂V/∂t/yr", "#FF7EB3"),
                ("Vanna",    g["vanna"],   "∂²V/∂F∂σ", "#C8C8FF"),
                ("Volga",    g["volga"],   "∂²V/∂σ²",  "#FFC8C8"),
            ]
            for name, val, formula, color in greek_info:
                st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};
                  border-left:3px solid {color};padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px'>
                  <div style='display:flex;justify-content:space-between;align-items:baseline'>
                    <span style='color:{color};font-size:11px;font-weight:600'>{name}</span>
                    <span style='color:{color};font-size:16px;font-weight:700'>{val:.5f}</span>
                  </div>
                  <div style='color:{TEXT2};font-size:8px;margin-top:3px'>{formula}</div>
                </div>""",unsafe_allow_html=True)

        with col_chart:
            st.markdown("**DELTA vs STRIKE**")
            strikes_r = np.linspace(F*0.6, F*1.4, 60)
            deltas = []
            gammas = []
            for K_ in strikes_r:
                try:
                    gk = model.greeks(F, K_, r_rate, T)
                    deltas.append(gk["delta"])
                    gammas.append(gk["gamma"] * F * 0.01)
                except:
                    deltas.append(np.nan)
                    gammas.append(np.nan)

            fig_g = go.Figure()
            fig_g.add_trace(go.Scatter(x=strikes_r/F*100, y=deltas,
                name="Delta", line=dict(color="#4AFF99",width=2)))
            fig_g.add_trace(go.Scatter(x=strikes_r/F*100, y=gammas,
                name="Gamma (×F×1%)", line=dict(color="#F5D060",width=2,dash="dash"),
                yaxis="y2"))
            fig_g.add_vline(x=k_pct, line_dash="dash", line_color=BORDER+"88")
            fig_g.add_hline(y=0.5, line_dash="dot", line_color=GRID)
            fig_g.update_layout(**PL, height=330,
                xaxis=dict(**AX,title="Strike (% ATM)"),
                yaxis=dict(**AX,title="Delta",range=[-0.1,1.1]),
                yaxis2=dict(title="Gamma",overlaying="y",side="right",
                    showgrid=False,color="#F5D060"),
                legend=dict(bgcolor=BG2,bordercolor=BORDER))
            st.plotly_chart(fig_g, use_container_width=True)
    except Exception as e:
        st.error(f"Error en Greeks: {e}")

# ── TAB 4: Calibración ────────────────────────────────────────────────────────
with tab4:
    st.markdown("**CALIBRACIÓN SABR A SMILE DE MERCADO**")
    st.markdown(f"""<div style='background:{BG2};border:1px solid {BORDER};border-left:3px solid {ACC};
      padding:10px 14px;border-radius:0 4px 4px 0;font-size:10px;color:{TEXT2};margin-bottom:16px'>
      Introduce vols de mercado (%). El modelo calibra α, ρ, ν con β={beta:.2f} fijo.
    </div>""",unsafe_allow_html=True)

    default_moneyness = [0.80,0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20]
    rng = np.random.default_rng(42)
    default_vols = [max(0.5, model.implied_vol(F,F*m,T)*100 + rng.normal(0,0.3))
                    for m in default_moneyness]
    calib_df = pd.DataFrame({
        "Strike (% ATM)": [f"{m*100:.0f}%" for m in default_moneyness],
        "Mkt IV (%)":     [round(v,2) for v in default_vols],
    })
    edited = st.data_editor(calib_df, use_container_width=True, hide_index=True, num_rows="fixed")

    if st.button("▶ CALIBRAR"):
        try:
            strikes_cal = np.array([F*float(r.replace("%",""))/100 for r in edited["Strike (% ATM)"]])
            vols_cal    = np.array(edited["Mkt IV (%)"].values, dtype=float) / 100
            with st.spinner("Calibrando..."):
                fitted = SABRModel.calibrate(strikes_cal, vols_cal, F=F, T=T, beta=beta)
            r_ = fitted._calib_result
            st.success(f"✓ Calibración completada — RMSE: {r_['rmse_bp']:.1f} bp")
            cr1,cr2,cr3 = st.columns(3)
            cr1.metric("α calibrado", f"{fitted.alpha:.4f}", f"{fitted.alpha-alpha:+.4f}")
            cr2.metric("ρ calibrado", f"{fitted.rho:.4f}",   f"{fitted.rho-rho:+.4f}")
            cr3.metric("ν calibrado", f"{fitted.nu:.4f}",    f"{fitted.nu-nu:+.4f}")

            m_range = np.linspace(0.75,1.25,40)
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Scatter(x=m_range*100,
                y=[fitted.implied_vol(F,F*m,T)*100 for m in m_range],
                name="Calibrado",line=dict(color=ACC,width=2)))
            fig_cal.add_trace(go.Scatter(x=m_range*100,
                y=[model.implied_vol(F,F*m,T)*100 for m in m_range],
                name="Prior",line=dict(color=TEXT2,width=1.5,dash="dot")))
            fig_cal.add_trace(go.Scatter(
                x=[float(r.replace("%","")) for r in edited["Strike (% ATM)"]],
                y=list(edited["Mkt IV (%)"]),
                name="Market",mode="markers",marker=dict(color="#4AFF99",size=9)))
            fig_cal.update_layout(**PL, height=300,
                xaxis=dict(**AX,title="Strike (% ATM)"),
                yaxis=dict(**AX,title="Impl. Vol (%)"),
                legend=dict(bgcolor=BG2,bordercolor=BORDER))
            st.plotly_chart(fig_cal, use_container_width=True)
        except Exception as e:
            st.error(f"Error en calibración: {e}")

st.markdown(f"""<div style="border-top:1px solid {BORDER};padding-top:14px;margin-top:32px;
  display:flex;justify-content:space-between;align-items:center;">
  <div style="color:{ACC};font-size:11px;font-weight:600;letter-spacing:2px;">QCEX</div>
  <div style="color:{TEXT2};font-size:8px;">by <strong>QuantumPablo</strong> · Pablo M. Paniagua</div>
</div>""",unsafe_allow_html=True)
