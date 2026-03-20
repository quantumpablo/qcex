"""Home.py — QCEX v4 · Clean, elegant, functional"""
from __future__ import annotations
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import CSS, BG, BG2, BG3, ACC, GOLD, BLUE, PINK, TEXT, TEXT2, BORD, footer

st.set_page_config(page_title="QCEX · QuantumPablo", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 20px;">
      <div style="color:{ACC};font-size:24px;font-weight:700;letter-spacing:3px;">QCEX</div>
      <div style="color:{TEXT2};font-size:8px;letter-spacing:2px;margin-top:4px;">QUANTUM COMMODITY EXCHANGE</div>
      <div style="background:{BG3};border:1px solid {BORD};border-radius:3px;
        padding:10px 12px;margin-top:14px;">
        <div style="color:{TEXT2};font-size:7px;letter-spacing:2px;margin-bottom:3px;">BY</div>
        <div style="color:{ACC};font-size:12px;font-weight:600;">QuantumPablo</div>
        <div style="color:{TEXT2};font-size:8px;margin-top:1px;">Pablo M. Paniagua</div>
      </div>
    </div>
    <hr style="border-color:{BORD};margin:8px 0 14px;">
    <div style="color:{TEXT2};font-size:8px;line-height:2.2;">
      <div style="color:{ACC};font-size:7px;letter-spacing:2px;margin-bottom:3px;">MODELS</div>
      Schwartz-Smith 2F · SABR<br>Black-76 · Kalman Filter
      <div style="color:{ACC};font-size:7px;letter-spacing:2px;margin:10px 0 3px;">RISK</div>
      VaR · CVaR · Stress Testing
      <div style="color:{ACC};font-size:7px;letter-spacing:2px;margin:10px 0 3px;">WEATHER</div>
      HDD · ENSO · Precipitación
      <div style="color:{ACC};font-size:7px;letter-spacing:2px;margin:10px 0 3px;">DATA</div>
      yfinance · Open-Meteo
    </div>
    """, unsafe_allow_html=True)

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:12px 0 8px;border-bottom:1px solid {BORD};margin-bottom:28px;">
  <div style="display:flex;align-items:baseline;gap:16px;">
    <span style="color:{ACC};font-size:36px;font-weight:700;letter-spacing:4px;line-height:1;">QCEX</span>
    <span style="color:{TEXT2};font-size:10px;letter-spacing:3px;">QUANTUM COMMODITY EXCHANGE</span>
  </div>
  <div style="color:{TEXT2};font-size:9px;margin-top:10px;line-height:1.9;">
    Commodity derivatives pricing engine &nbsp;·&nbsp;
    Schwartz-Smith 2F &nbsp;·&nbsp; SABR Vol Surface &nbsp;·&nbsp;
    Black-76 &nbsp;·&nbsp; Kalman Filter &nbsp;·&nbsp; VaR/CVaR
  </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation cards ──────────────────────────────────────────────────────────
cols = st.columns(4)
pages = [
    ("01", "Market Overview",   "Precios spot, vol histórica, correlaciones, drawdown, vol cone.",         ACC,  "◈"),
    ("02", "Futures Pricer",    "Schwartz-Smith 2F + Kalman. Curva de futuros, CY, Monte Carlo.",          GOLD, "📈"),
    ("03", "Options · SABR",    "Superficie SABR, Black-76, Greeks completos (Δ Γ ν Θ Vanna Volga).",     BLUE, "📉"),
    ("04", "Risk Dashboard",    "VaR/CVaR histórico, stress testing, vol cone, rolling risk.",             PINK, "⚠"),
]
for col, (num, title, desc, color, icon) in zip(cols, pages):
    with col:
        st.markdown(f"""
        <div style="background:{BG2};border:1px solid {BORD};border-left:3px solid {color};
          padding:16px;border-radius:4px;height:150px;position:relative;cursor:pointer;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="color:{TEXT2};font-size:8px;letter-spacing:2px;">{num}</span>
            <span style="color:{color};font-size:11px;font-weight:600;">{title}</span>
          </div>
          <div style="color:{TEXT2};font-size:9px;line-height:1.6;">{desc}</div>
          <div style="position:absolute;bottom:12px;right:14px;
            color:{color};font-size:18px;opacity:0.3;">{icon}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Two column layout: models + commodities ───────────────────────────────────
col_l, col_r = st.columns([1, 1])

with col_l:
    st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:2px;margin-bottom:12px;'>MODEL ARCHITECTURE</div>", unsafe_allow_html=True)

    # SS Model
    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {BORD};border-radius:4px;padding:16px;margin-bottom:12px;">
      <div style="color:{ACC};font-size:9px;font-weight:600;letter-spacing:1.5px;margin-bottom:12px;">
        SCHWARTZ-SMITH TWO-FACTOR
      </div>
      <div style="font-family:monospace;color:{ACC};font-size:12px;background:{BG3};
        border-left:2px solid {ACC};padding:7px 12px;border-radius:0 3px 3px 0;margin-bottom:10px;">
        ln S<sub>t</sub> = &chi;<sub>t</sub> + &xi;<sub>t</sub>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
        <div style="background:{BG3};border:1px solid {BORD};padding:9px;border-radius:3px;">
          <div style="color:{ACC};font-size:8px;font-weight:600;margin-bottom:4px;">&chi;<sub>t</sub> Short-term</div>
          <div style="color:{TEXT2};font-size:8px;line-height:1.7;">Ornstein-Uhlenbeck<br>Transient shocks<br>Semivida = ln2/&kappa;</div>
        </div>
        <div style="background:{BG3};border:1px solid {BORD};padding:9px;border-radius:3px;">
          <div style="color:{ACC};font-size:8px;font-weight:600;margin-bottom:4px;">&xi;<sub>t</sub> Long-term</div>
          <div style="color:{TEXT2};font-size:8px;line-height:1.7;">GBM with drift<br>Equilibrium level<br>Production costs</div>
        </div>
      </div>
      <div style="font-family:monospace;color:{TEXT2};font-size:10px;background:{BG3};
        border-left:2px solid {BORD};padding:7px 12px;border-radius:0 3px 3px 0;">
        ln F(t,T) = e<sup>-&kappa;&tau;</sup>&chi; + &xi; + A(&tau;)
        &nbsp;&nbsp;<span style="color:{TEXT2};font-size:8px;">Kalman Filter MLE</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # SABR
    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {BORD};border-radius:4px;padding:16px;">
      <div style="color:{BLUE};font-size:9px;font-weight:600;letter-spacing:1.5px;margin-bottom:12px;">
        SABR STOCHASTIC VOLATILITY
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
        <div style="text-align:center;padding:10px 4px;background:{BG3};border:1px solid {BORD};border-radius:3px;">
          <div style="color:{GOLD};font-size:18px;font-weight:700;">&alpha;</div>
          <div style="color:{TEXT2};font-size:7px;margin-top:3px;">Vol level</div>
        </div>
        <div style="text-align:center;padding:10px 4px;background:{BG3};border:1px solid {BORD};border-radius:3px;">
          <div style="color:{BLUE};font-size:18px;font-weight:700;">&beta;</div>
          <div style="color:{TEXT2};font-size:7px;margin-top:3px;">CEV = 0.5</div>
        </div>
        <div style="text-align:center;padding:10px 4px;background:{BG3};border:1px solid {BORD};border-radius:3px;">
          <div style="color:{PINK};font-size:18px;font-weight:700;">&rho;</div>
          <div style="color:{TEXT2};font-size:7px;margin-top:3px;">Skew</div>
        </div>
        <div style="text-align:center;padding:10px 4px;background:{BG3};border:1px solid {BORD};border-radius:3px;">
          <div style="color:{ACC};font-size:18px;font-weight:700;">&nu;</div>
          <div style="color:{TEXT2};font-size:7px;margin-top:3px;">Vol of vol</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_r:
    st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:2px;margin-bottom:12px;'>CALIBRATED PARAMETERS</div>", unsafe_allow_html=True)

    commodities_info = [
        ("CACAO",   "#D4A85A", "ICE CC1",  "9,240","USD/MT", "0.80","10.4M","38%","-0.45","0.68",
         "El Niño · ICCO · supply crisis 2023-24"),
        ("GAS TTF", BLUE,      "ICE TTF",  "41.2", "EUR/MWh","2.10","4.0M", "55%","-0.25","0.85",
         "HDD seasonal · LNG flows · post-2022"),
        ("URANIO",  ACC,       "OTC/URA",  "78.5", "USD/lb", "0.30","27.6M","28%","-0.15","0.42",
         "OTC market · Kazatomprom · nuclear policy"),
    ]

    for name, color, exch, spot, unit, kappa, hl, schi, srho, snu, note in commodities_info:
        st.markdown(f"""
        <div style="border:1px solid {BORD};border-left:3px solid {color};border-radius:0 4px 4px 0;
          padding:12px 14px;margin-bottom:10px;background:{BG2};">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div>
              <span style="color:{color};font-size:11px;font-weight:600;">{name}</span>
              <span style="color:{TEXT2};font-size:8px;margin-left:8px;">{exch}</span>
            </div>
            <span style="color:{color};font-size:14px;font-weight:700;">{spot}
              <span style="font-size:8px;opacity:0.6;">{unit}</span></span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-bottom:8px;">
            <div style="background:{BG3};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT2};font-size:7px;">&kappa; / HL</div>
              <div style="color:{color};font-size:10px;font-weight:600;">{kappa} / {hl}</div>
            </div>
            <div style="background:{BG3};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT2};font-size:7px;">&sigma;&chi;</div>
              <div style="color:{color};font-size:10px;font-weight:600;">{schi}</div>
            </div>
            <div style="background:{BG3};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT2};font-size:7px;">SABR &rho;/&nu;</div>
              <div style="color:{color};font-size:10px;font-weight:600;">{srho}/{snu}</div>
            </div>
          </div>
          <div style="color:{TEXT2};font-size:8px;font-style:italic;">{note}</div>
        </div>
        """, unsafe_allow_html=True)

    # References
    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {BORD};border-radius:4px;padding:14px 16px;">
      <div style="color:{ACC};font-size:7px;letter-spacing:2px;margin-bottom:8px;">REFERENCES</div>
      <div style="color:{TEXT2};font-size:8px;line-height:2.0;">
        Black (1976) · Pricing of Commodity Contracts<br>
        Schwartz (1997) · Stochastic Behavior of Commodities<br>
        Schwartz &amp; Smith (2000) · Two-Factor Model<br>
        Hagan et al. (2002) · Managing Smile Risk (SABR)<br>
        Working (1949) · Theory of Price of Storage
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(footer(), unsafe_allow_html=True)
