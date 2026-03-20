from __future__ import annotations
"""pages/3_Options_SABR.py — QCEX v4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from theme import LEGEND, CSS, BG, BG2, BG3, ACC, BLUE, GOLD, PINK, TEXT, TEXT2, BORD, GRID, PLOTLY, ax, footer
from data.fetcher import compute_stats, TICKERS
from models.sabr import SABRModel

st.set_page_config(page_title="QCEX · Options · SABR", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

PRESETS = {
    "cocoa":   dict(alpha=0.52,beta=0.5,rho=-0.45,nu=0.68),
    "gas":     dict(alpha=0.65,beta=0.5,rho=-0.25,nu=0.85),
    "uranium": dict(alpha=0.35,beta=0.5,rho=-0.15,nu=0.42),
}
MATURITIES = {"1M":1/12,"3M":3/12,"6M":0.5,"1Y":1.0,"18M":1.5,"2Y":2.0}

with st.sidebar:
    st.markdown(f"<div style='color:{BLUE};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>OPTIONS · SABR</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", list(PRESETS.keys()), format_func=lambda x: TICKERS[x]["name"])
    mat_key   = st.selectbox("Maturity", list(MATURITIES.keys()), index=2)
    T         = MATURITIES[mat_key]
    sp        = PRESETS[commodity]
    st.markdown("---")
    alpha = st.slider("α  vol level",  0.01, 1.5,  float(sp["alpha"]), 0.01)
    beta  = st.slider("β  CEV",        0.0,  1.0,  float(sp["beta"]),  0.01)
    rho   = st.slider("ρ  skew corr", -0.99, 0.99, float(sp["rho"]),   0.01)
    nu    = st.slider("ν  vol of vol", 0.01, 2.0,  float(sp["nu"]),    0.01)
    st.markdown("---")
    k_pct  = st.slider("Strike (% ATM)", 70, 130, 100)
    r_rate = st.slider("r risk-free",    0.0, 0.10, 0.05, 0.005)

@st.cache_data(ttl=3600)
def load(c): return compute_stats(c)

stats = load(commodity)
F = stats["spot"]
K = F * k_pct / 100

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
    st.error(f"Error SABR: {e}")
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

tab1, tab2, tab3, tab4 = st.tabs(["VOL SMILE","3D SURFACE","GREEKS","CALIBRATION"])

# ── SMILE ─────────────────────────────────────────────────────────────────────
with tab1:
    try:
        mon = np.linspace(0.70, 1.30, 31)
        ivs = np.array([model.implied_vol(F, F*m, T)*100 for m in mon])

        col_s, col_i = st.columns([3, 1])
        with col_s:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mon*100, y=ivs, name="SABR σ_impl",
                line=dict(color=BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(91,174,255,0.07)"))
            fig.add_vline(x=100, line_dash="dot", line_color=BORD,
                annotation_text="ATM", annotation_font_color=TEXT2)
            fig.add_vline(x=k_pct, line_dash="dash", line_color=ACC,
                annotation_text=f"K={k_pct}%", annotation_font_color=ACC)
            fig.update_layout(**PLOTLY, height=300,
                xaxis=ax("Strike (% ATM)"), yaxis=ax("Impl. Vol (%)"))
            st.plotly_chart(fig, use_container_width=True)

        with col_i:
            st.markdown(f"<div style='color:{BLUE};font-size:9px;font-weight:600;margin-bottom:12px;'>SMILE METRICS</div>", unsafe_allow_html=True)
            for label, val, color in [
                ("ATM Vol",   f"{atm_v*100:.2f}%",  BLUE),
                ("Skew (bp)", f"{skw:+.1f}",         PINK if skw > 0 else ACC),
                ("Butterfly", f"{fly:.1f} bp",        GOLD),
                ("ρ",         f"{rho:.3f}",           PINK),
                ("ν",         f"{nu:.3f}",            ACC),
            ]:
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORD};padding:8px 12px;'
                    f'border-radius:4px;margin-bottom:6px;">'
                    f'<div style="color:{TEXT2};font-size:8px;letter-spacing:1px;">{label}</div>'
                    f'<div style="color:{color};font-size:16px;font-weight:600;margin-top:2px;">{val}</div>'
                    f'</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Smile: {e}")

# ── 3D SURFACE ────────────────────────────────────────────────────────────────
with tab2:
    try:
        surf = model.vol_surface(F,
            maturities=[1/12,2/12,3/12,6/12,9/12,1.0,1.5,2.0],
            moneyness=np.linspace(0.70,1.30,21))
        fig3d = go.Figure(go.Surface(
            z=surf["vols_pct"], x=surf["moneyness"]*100,
            y=list(range(len(surf["maturities"]))),
            colorscale=[[0,"#0a1a2a"],[0.4,"#1a5a9a"],[0.7,"#4a9eff"],[1,"#c8f0ff"]],
            opacity=0.92,
            hovertemplate="Strike: %{x:.0f}%<br>Vol: %{z:.2f}%<extra></extra>"))
        fig3d.update_layout(
            paper_bgcolor=BG, height=480,
            scene=dict(bgcolor=BG3,
                xaxis=dict(title="Strike (% ATM)", gridcolor=GRID, color=TEXT2),
                yaxis=dict(title="Maturity",
                    tickvals=list(range(8)),
                    ticktext=["1M","2M","3M","6M","9M","1Y","18M","2Y"],
                    gridcolor=GRID, color=TEXT2),
                zaxis=dict(title="Impl. Vol (%)", gridcolor=GRID, color=TEXT2),
                camera=dict(eye=dict(x=1.5,y=-1.8,z=0.8))),
            font=dict(family="IBM Plex Mono", color=TEXT2),
            margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig3d, use_container_width=True)
    except Exception as e:
        st.error(f"3D Surface: {e}")

# ── GREEKS ────────────────────────────────────────────────────────────────────
with tab3:
    col_g, col_chart = st.columns([1, 2])

    with col_g:
        st.markdown(f"<div style='color:{BLUE};font-size:9px;font-weight:600;letter-spacing:2px;margin-bottom:14px;'>GREEKS (CALL)</div>", unsafe_allow_html=True)
        greek_rows = [
            ("Δ Delta",  "delta",  "∂V/∂F",    ACC),
            ("Γ Gamma",  "gamma",  "∂²V/∂F²",  GOLD),
            ("ν Vega",   "vega",   "∂V/∂σ",    BLUE),
            ("Θ Theta",  "theta",  "∂V/∂t",    PINK),
            ("Vanna",    "vanna",  "∂²V/∂F∂σ", "#AAAAFF"),
            ("Volga",    "volga",  "∂²V/∂σ²",  "#FFAAAA"),
        ]
        for name, key, formula, color in greek_rows:
            raw = g.get(key, None)
            if raw is None:
                val_str = "—"
            elif abs(raw) > 9999:
                val_str = f"{raw:,.0f}"
            elif abs(raw) > 0.001:
                val_str = f"{raw:.4f}"
            else:
                val_str = f"{raw:.2e}"

            st.markdown(
                f'<div style="background:{BG2};border:1px solid {BORD};border-left:3px solid {color};'
                f'padding:10px 12px;border-radius:0 4px 4px 0;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="color:{color};font-size:11px;font-weight:600;">{name}</span>'
                f'<span style="color:{color};font-size:15px;font-weight:700;font-family:monospace;">{val_str}</span>'
                f'</div>'
                f'<div style="color:{TEXT2};font-size:8px;margin-top:3px;">{formula}</div>'
                f'</div>', unsafe_allow_html=True)

    with col_chart:
        st.markdown(f"<div style='color:{BLUE};font-size:9px;font-weight:600;letter-spacing:2px;margin-bottom:14px;'>DELTA & GAMMA vs STRIKE</div>", unsafe_allow_html=True)
        try:
            strikes_r = np.linspace(F*0.6, F*1.4, 50)
            deltas, gammas = [], []
            for K_ in strikes_r:
                try:
                    gk = model.greeks(F, K_, r_rate, T)
                    deltas.append(gk["delta"])
                    gammas.append(gk["gamma"] * F * 0.01)
                except:
                    deltas.append(np.nan); gammas.append(np.nan)

            fig_g = go.Figure()
            fig_g.add_trace(go.Scatter(x=strikes_r/F*100, y=deltas,
                name="Delta", line=dict(color=ACC, width=2.5)))
            fig_g.add_trace(go.Scatter(x=strikes_r/F*100, y=gammas,
                name="Gamma ×F×1%",
                line=dict(color=GOLD, width=2, dash="dash"),
                yaxis="y2"))
            fig_g.add_vline(x=k_pct, line_dash="dash", line_color=BORD)
            fig_g.add_hline(y=0.5, line_dash="dot", line_color=GRID)
            fig_g.update_layout(**PLOTLY, height=340,
                xaxis=ax("Strike (% ATM)"),
                yaxis=dict(**ax("Delta"), range=[-0.05, 1.05]),
                yaxis2=dict(title=dict(text="Gamma ×F×1%",
                    font=dict(color=GOLD, size=10)),
                    overlaying="y", side="right", showgrid=False,
                    zeroline=False, color=GOLD,
                    tickfont=dict(color=GOLD, size=9)))
            st.plotly_chart(fig_g, use_container_width=True)
        except Exception as e:
            st.error(f"Greeks chart: {e}")

# ── CALIBRATION ───────────────────────────────────────────────────────────────
with tab4:
    st.markdown(
        f'<div style="background:{BG3};border:1px solid {BORD};border-left:3px solid {BLUE};'
        f'padding:10px 14px;border-radius:0 4px 4px 0;font-size:9px;color:{TEXT2};margin-bottom:16px;">'
        f'Calibrate (&alpha;, &rho;, &nu;) to market vols with &beta; = {beta:.2f} fixed.'
        f'</div>', unsafe_allow_html=True)

    rng = np.random.default_rng(42)
    default_moneyness = [0.80,0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20]
    default_vols = [round(max(0.5, model.implied_vol(F,F*m,T)*100 + rng.normal(0,0.3)),2)
                    for m in default_moneyness]
    edited = st.data_editor(pd.DataFrame({
        "Strike (% ATM)": [f"{int(m*100)}%" for m in default_moneyness],
        "Mkt IV (%)":     default_vols,
    }), use_container_width=True, hide_index=True, num_rows="fixed")

    if st.button("▶ CALIBRATE"):
        try:
            strikes_cal = np.array([F*float(r.replace("%",""))/100 for r in edited["Strike (% ATM)"]])
            vols_cal    = np.array(edited["Mkt IV (%)"].values, dtype=float)/100
            with st.spinner("Calibratendo..."):
                fitted = SABRModel.calibrate(strikes_cal, vols_cal, F=F, T=T, beta=beta)
            r_ = fitted._calib_result
            st.success(f"✓ Calibrateción — RMSE: {r_['rmse_bp']:.1f} bp")
            cr1,cr2,cr3 = st.columns(3)
            cr1.metric("α", f"{fitted.alpha:.4f}", f"{fitted.alpha-alpha:+.4f}")
            cr2.metric("ρ", f"{fitted.rho:.4f}",   f"{fitted.rho-rho:+.4f}")
            cr3.metric("ν", f"{fitted.nu:.4f}",    f"{fitted.nu-nu:+.4f}")

            m_r = np.linspace(0.75, 1.25, 40)
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Scatter(x=m_r*100,
                y=[fitted.implied_vol(F,F*m,T)*100 for m in m_r],
                name="Calibratedo", line=dict(color=BLUE, width=2)))
            fig_cal.add_trace(go.Scatter(x=m_r*100,
                y=[model.implied_vol(F,F*m,T)*100 for m in m_r],
                name="Prior", line=dict(color=TEXT2, width=1.5, dash="dot")))
            fig_cal.add_trace(go.Scatter(
                x=[float(r.replace("%","")) for r in edited["Strike (% ATM)"]],
                y=list(edited["Mkt IV (%)"]),
                name="Market", mode="markers",
                marker=dict(color=ACC, size=9)))
            fig_cal.update_layout(**PLOTLY, height=280,
                xaxis=ax("Strike (% ATM)"), yaxis=ax("Impl. Vol (%)"))
            st.plotly_chart(fig_cal, use_container_width=True)
        except Exception as e:
            st.error(f"Calibrateción: {e}")

st.markdown(footer("Options · SABR"), unsafe_allow_html=True)
