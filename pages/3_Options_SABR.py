"""pages/3_Options_SABR.py — QCEX v3 · Fixed Greeks, theme, no f-string nesting"""
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
    "cocoa":   dict(alpha=0.52, beta=0.5, rho=-0.45, nu=0.68),
    "gas":     dict(alpha=0.65, beta=0.5, rho=-0.25, nu=0.85),
    "uranium": dict(alpha=0.35, beta=0.5, rho=-0.15, nu=0.42),
}
MATURITIES = {"1M":1/12,"3M":3/12,"6M":0.5,"1Y":1.0,"18M":1.5,"2Y":2.0}

with st.sidebar:
    st.markdown("<div style='font-size:9px;letter-spacing:2px;margin-bottom:8px'>QCEX · OPTIONS · SABR</div>", unsafe_allow_html=True)
    dark   = st.toggle("Modo oscuro", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark
    st.markdown("---")
    commodity = st.selectbox("Commodity", list(SABR_PRESETS.keys()), format_func=lambda x: TICKERS[x]["name"])
    mat_key   = st.selectbox("Maturity", list(MATURITIES.keys()), index=2)
    T         = MATURITIES[mat_key]
    sp        = SABR_PRESETS[commodity]
    st.markdown("<div style='font-size:9px;letter-spacing:1px;margin:8px 0 4px'>SABR PARAMS</div>", unsafe_allow_html=True)
    alpha = st.slider("α  vol level",  0.01, 1.5,  float(sp["alpha"]), 0.01)
    beta  = st.slider("β  CEV",        0.0,  1.0,  float(sp["beta"]),  0.01)
    rho   = st.slider("ρ  skew corr", -0.99, 0.99, float(sp["rho"]),   0.01)
    nu    = st.slider("ν  vol of vol", 0.01, 2.0,  float(sp["nu"]),    0.01)
    st.markdown("---")
    k_pct  = st.slider("Strike (% ATM)", 70, 130, 100)
    r_rate = st.slider("r risk-free",    0.0, 0.10, 0.05, 0.005)

# ── Theme ─────────────────────────────────────────────────────────────────────
if dark:
    BG,BG2,GRID,TEXT,TEXT2,TEXT3,BORD,ACC = "#07090D","#070C07","#0A1A2A","#C8D6E8","#2A3A4A","#1A2A3A","#0A1A2A","#7EC8FF"
else:
    BG,BG2,GRID,TEXT,TEXT2,TEXT3,BORD,ACC = "#F4F8FC","#FFFFFF","#D0E4F4","#1A2A3A","#2A4A6A","#5A7A9A","#AACCEE","#1A6A9A"

st.markdown(f"""<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  html,body,[class*="css"]{{font-family:'IBM Plex Mono',monospace!important;background:{BG}!important;color:{TEXT}!important}}
  .stApp{{background:{BG}!important}}
  section[data-testid="stSidebar"]{{background:{BG2}!important;border-right:1px solid {BORD}}}
  section[data-testid="stSidebar"] *{{color:{TEXT2}!important}}
  h1,h2,h3{{color:{ACC}!important;font-family:'IBM Plex Mono',monospace!important}}
  [data-testid="metric-container"]{{background:{BG2}!important;border:1px solid {BORD};border-radius:4px;padding:8px 12px}}
  [data-testid="metric-container"] label{{color:{TEXT2}!important;font-size:10px}}
  [data-testid="metric-container"] [data-testid="stMetricValue"]{{color:{ACC}!important}}
  [data-testid="stDataFrame"]{{background:{BG2}!important}}
  .stTabs [data-baseweb="tab"]{{color:{TEXT2}!important}}
  .stTabs [aria-selected="true"]{{color:{ACC}!important;border-bottom-color:{ACC}!important}}
  hr{{border-color:{BORD}}}
</style>""", unsafe_allow_html=True)

PL = dict(paper_bgcolor=BG, plot_bgcolor=BG,
    font=dict(family="IBM Plex Mono", color=TEXT2, size=10),
    margin=dict(l=50, r=20, t=35, b=40))
AX = dict(gridcolor=GRID, showgrid=True, zeroline=False)

@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats = load(commodity)
F = stats["spot"]
K = F * k_pct / 100

# ── Init model ────────────────────────────────────────────────────────────────
try:
    model   = SABRModel(alpha=alpha, beta=beta, rho=rho, nu=nu)
    sigma_k = model.implied_vol(F, K, T)
    atm_v   = model.implied_vol(F, F, T)
    call_p  = model.price(F, K, r_rate, T, "call")
    put_p   = model.price(F, K, r_rate, T, "put")
    g       = model.greeks(F, K, r_rate, T)
    skw     = model.skew(F, T) * 1e4
    fly     = model.butterfly(F, T) * 1e4
except Exception as e:
    st.error(f"Error inicializando SABR: {e}")
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

# ── SMILE ─────────────────────────────────────────────────────────────────────
with tab1:
    try:
        moneyness = np.linspace(0.70, 1.30, 31)
        smile_iv  = np.array([model.implied_vol(F, F*m, T)*100 for m in moneyness])

        col_s, col_i = st.columns([3, 1])
        with col_s:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=moneyness*100, y=smile_iv, name="SABR σ_impl",
                line=dict(color=ACC, width=2.5),
                fill="tozeroy",
                fillcolor=f"rgba(126,200,255,0.08)" if dark else f"rgba(26,106,154,0.08)"))
            fig.add_vline(x=100, line_dash="dot", line_color=BORD, annotation_text="ATM",
                annotation_font_color=TEXT2)
            fig.add_vline(x=k_pct, line_dash="dash", line_color="#4AFF99",
                annotation_text=f"K={k_pct}%", annotation_font_color="#4AFF99")
            fig.update_layout(**PL, height=320,
                xaxis=dict(**AX, title="Strike (% ATM)"),
                yaxis=dict(**AX, title="Impl. Vol (%)"),
                legend=dict(bgcolor=BG2, bordercolor=BORD))
            st.plotly_chart(fig, use_container_width=True)

        with col_i:
            st.markdown(f"<div style='color:{ACC};font-size:10px;font-weight:600;margin-bottom:12px;'>SMILE METRICS</div>", unsafe_allow_html=True)
            metrics = [
                ("ATM Vol",   f"{atm_v*100:.2f}%",  ACC),
                ("Skew (bp)", f"{skw:+.1f}",         "#FF7EB3" if skw>0 else "#4AFF99"),
                ("Butterfly", f"{fly:.1f} bp",        "#F5D060"),
                ("ρ",         f"{rho:.3f}",           "#FF7EB3"),
                ("ν",         f"{nu:.3f}",            "#4AFF99"),
            ]
            for label, val, color in metrics:
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORD};padding:8px 12px;'
                    f'border-radius:4px;margin-bottom:6px;">'
                    f'<div style="color:{TEXT2};font-size:8px;">{label}</div>'
                    f'<div style="color:{color};font-size:16px;font-weight:600;">{val}</div>'
                    f'</div>',
                    unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error en smile: {e}")

# ── 3D SURFACE ────────────────────────────────────────────────────────────────
with tab2:
    try:
        surf = model.vol_surface(F,
            maturities=[1/12,2/12,3/12,6/12,9/12,1.0,1.5,2.0],
            moneyness=np.linspace(0.70,1.30,21))
        T_labels = ["1M","2M","3M","6M","9M","1Y","18M","2Y"]
        cs = [[0,"#0a1a2a"],[0.3,"#1a4a7a"],[0.6,"#4a9eff"],[0.8,"#7ec8ff"],[1,"#ffffff"]] if dark else \
             [[0,"#e0f0ff"],[0.3,"#90c8f0"],[0.6,"#4090d0"],[0.8,"#1060a0"],[1,"#002060"]]

        fig3d = go.Figure(go.Surface(
            z=surf["vols_pct"], x=surf["moneyness"]*100,
            y=list(range(len(surf["maturities"]))),
            colorscale=cs, opacity=0.92,
            hovertemplate="Strike: %{x:.0f}%<br>Vol: %{z:.2f}%<extra></extra>"))
        fig3d.update_layout(
            paper_bgcolor=BG, height=500,
            scene=dict(bgcolor=BG,
                xaxis=dict(title="Strike (% ATM)", gridcolor=GRID, color=TEXT2),
                yaxis=dict(title="Maturity", tickvals=list(range(len(surf["maturities"]))),
                    ticktext=T_labels, gridcolor=GRID, color=TEXT2),
                zaxis=dict(title="Impl. Vol (%)", gridcolor=GRID, color=TEXT2),
                camera=dict(eye=dict(x=1.5,y=-1.8,z=0.8))),
            font=dict(family="IBM Plex Mono", color=TEXT2),
            margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig3d, use_container_width=True)
    except Exception as e:
        st.error(f"Error en superficie 3D: {e}")

# ── GREEKS ────────────────────────────────────────────────────────────────────
with tab3:
    col_g, col_chart = st.columns([1, 2])

    with col_g:
        st.markdown(f"<div style='color:{ACC};font-size:10px;font-weight:600;margin-bottom:14px;'>GREEKS (CALL)</div>", unsafe_allow_html=True)

        greek_rows = [
            ("Δ Delta",  "delta",  "∂V/∂F",    "#4AFF99", "Exposición al forward"),
            ("Γ Gamma",  "gamma",  "∂²V/∂F²",  "#F5D060", "Convexidad respecto a F"),
            ("ν Vega",   "vega",   "∂V/∂σ",    ACC,       "Sensibilidad a la vol"),
            ("Θ Theta",  "theta",  "∂V/∂t",    "#FF7EB3", "Decaimiento temporal"),
            ("Vanna",    "vanna",  "∂²V/∂F∂σ", "#AAAAFF", "Mixta F-vol"),
            ("Volga",    "volga",  "∂²V/∂σ²",  "#FFAAAA", "Convexidad de vol"),
        ]
        for name, key, formula, color, desc in greek_rows:
            val = g.get(key, None)
            if val is None:
                val_str = "—"
            elif abs(val) > 1000:
                val_str = f"{val:,.1f}"
            elif abs(val) < 0.0001:
                val_str = f"{val:.2e}"
            else:
                val_str = f"{val:.5f}"

            st.markdown(
                f'<div style="background:{BG2};border:1px solid {BORD};border-left:3px solid {color};'
                f'padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="color:{color};font-size:11px;font-weight:600;">{name}</span>'
                f'<span style="color:{color};font-size:15px;font-weight:700;">{val_str}</span>'
                f'</div>'
                f'<div style="color:{TEXT3};font-size:8px;margin-top:4px;">{formula} · {desc}</div>'
                f'</div>',
                unsafe_allow_html=True)

    with col_chart:
        st.markdown(f"<div style='color:{ACC};font-size:10px;font-weight:600;margin-bottom:14px;'>DELTA & GAMMA vs STRIKE</div>", unsafe_allow_html=True)
        try:
            strikes_r = np.linspace(F*0.6, F*1.4, 50)
            deltas, gammas = [], []
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
                name="Delta", line=dict(color="#4AFF99", width=2.5)))
            fig_g.add_trace(go.Scatter(x=strikes_r/F*100, y=gammas,
                name="Gamma ×F×1%", line=dict(color="#F5D060", width=2, dash="dash"),
                yaxis="y2"))
            fig_g.add_vline(x=k_pct, line_dash="dash", line_color=BORD,
                annotation_text=f"K={k_pct}%", annotation_font_color=TEXT2)
            fig_g.add_hline(y=0.5, line_dash="dot", line_color=GRID)
            fig_g.update_layout(**PL, height=340,
                xaxis=dict(**AX, title="Strike (% ATM)"),
                yaxis=dict(**AX, title="Delta", range=[-0.05, 1.05]),
                yaxis2=dict(title="Gamma ×F×1%", overlaying="y", side="right",
                    showgrid=False, color="#F5D060", zeroline=False),
                legend=dict(bgcolor=BG2, bordercolor=BORD, font=dict(size=9)))
            st.plotly_chart(fig_g, use_container_width=True)
        except Exception as e:
            st.error(f"Error en gráfico Greeks: {e}")

# ── CALIBRACIÓN ───────────────────────────────────────────────────────────────
with tab4:
    st.markdown(f"**CALIBRACIÓN SABR A SMILE DE MERCADO**")
    st.markdown(
        f'<div style="background:{BG2};border:1px solid {BORD};border-left:3px solid {ACC};'
        f'padding:10px 14px;border-radius:0 4px 4px 0;font-size:10px;color:{TEXT2};margin-bottom:16px;">'
        f'Introduce vols de mercado (%). El modelo calibra &alpha;, &rho;, &nu; con &beta;={beta:.2f} fijo.'
        f'</div>',
        unsafe_allow_html=True)

    rng = np.random.default_rng(42)
    default_moneyness = [0.80,0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20]
    default_vols = [round(max(0.5, model.implied_vol(F,F*m,T)*100 + rng.normal(0,0.3)), 2)
                    for m in default_moneyness]
    calib_df = pd.DataFrame({
        "Strike (% ATM)": [f"{int(m*100)}%" for m in default_moneyness],
        "Mkt IV (%)": default_vols,
    })
    edited = st.data_editor(calib_df, use_container_width=True, hide_index=True, num_rows="fixed")

    if st.button("▶ CALIBRAR"):
        try:
            strikes_cal = np.array([F * float(r.replace("%",""))/100 for r in edited["Strike (% ATM)"]])
            vols_cal    = np.array(edited["Mkt IV (%)"].values, dtype=float) / 100
            with st.spinner("Calibrando..."):
                fitted = SABRModel.calibrate(strikes_cal, vols_cal, F=F, T=T, beta=beta)
            r_ = fitted._calib_result
            st.success(f"✓ Calibración completada — RMSE: {r_['rmse_bp']:.1f} bp")
            cr1, cr2, cr3 = st.columns(3)
            cr1.metric("α calibrado", f"{fitted.alpha:.4f}", f"{fitted.alpha-alpha:+.4f}")
            cr2.metric("ρ calibrado", f"{fitted.rho:.4f}",   f"{fitted.rho-rho:+.4f}")
            cr3.metric("ν calibrado", f"{fitted.nu:.4f}",    f"{fitted.nu-nu:+.4f}")

            m_range = np.linspace(0.75, 1.25, 40)
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Scatter(x=m_range*100,
                y=[fitted.implied_vol(F,F*m,T)*100 for m in m_range],
                name="Calibrado", line=dict(color=ACC, width=2)))
            fig_cal.add_trace(go.Scatter(x=m_range*100,
                y=[model.implied_vol(F,F*m,T)*100 for m in m_range],
                name="Prior", line=dict(color=TEXT2, width=1.5, dash="dot")))
            fig_cal.add_trace(go.Scatter(
                x=[float(r.replace("%","")) for r in edited["Strike (% ATM)"]],
                y=list(edited["Mkt IV (%)"]),
                name="Market", mode="markers",
                marker=dict(color="#4AFF99", size=9, symbol="circle")))
            fig_cal.update_layout(**PL, height=300,
                xaxis=dict(**AX, title="Strike (% ATM)"),
                yaxis=dict(**AX, title="Impl. Vol (%)"),
                legend=dict(bgcolor=BG2, bordercolor=BORD))
            st.plotly_chart(fig_cal, use_container_width=True)
        except Exception as e:
            st.error(f"Error en calibración: {e}")

st.markdown(
    f'<div style="border-top:1px solid {BORD};padding-top:14px;margin-top:32px;'
    f'display:flex;justify-content:space-between;align-items:center;">'
    f'<div style="color:{ACC};font-size:11px;font-weight:600;letter-spacing:2px;">QCEX</div>'
    f'<div style="color:{TEXT2};font-size:8px;">by <strong>QuantumPablo</strong> · Pablo M. Paniagua</div>'
    f'</div>',
    unsafe_allow_html=True)
