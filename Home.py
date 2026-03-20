"""
QCEX — Quantum Commodity Exchange
by QuantumPablo

Entry point for Streamlit Cloud deployment.
Run locally: streamlit run Home.py
"""

import streamlit as st

st.set_page_config(
    page_title="QCEX · QuantumPablo",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: #07090D;
    color: #B8CCB8;
  }
  .stApp { background-color: #07090D; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060A06 0%, #07090D 100%);
    border-right: 1px solid #0F1F0F;
  }
  section[data-testid="stSidebar"] * { font-family: 'IBM Plex Mono', monospace !important; }
  section[data-testid="stSidebar"] label { color: #2A5A2A !important; font-size: 10px !important; letter-spacing: 1px; }

  /* Metrics */
  [data-testid="metric-container"] {
    background: #070C07;
    border: 1px solid #0F1F0F;
    border-radius: 3px;
    padding: 10px 14px;
  }
  [data-testid="metric-container"] label { color: #1A3A1A !important; font-size: 9px !important; letter-spacing: 1.5px; text-transform: uppercase; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #4AFF99 !important; font-family: 'IBM Plex Mono', monospace !important; }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 10px !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: #060A06;
    border-bottom: 1px solid #0F1F0F;
    gap: 0;
  }
  .stTabs [data-baseweb="tab"] {
    color: #1A3A1A;
    font-size: 9px;
    letter-spacing: 2px;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
    font-family: 'IBM Plex Mono', monospace !important;
  }
  .stTabs [aria-selected="true"] {
    color: #4AFF99 !important;
    border-bottom: 2px solid #3A8A3A !important;
    background: transparent !important;
  }

  /* Buttons */
  .stButton button {
    background: transparent;
    border: 1px solid #2A5A2A;
    color: #4AFF99;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px;
    letter-spacing: 2px;
    padding: 7px 18px;
    border-radius: 2px;
    transition: all 0.15s;
    text-transform: uppercase;
  }
  .stButton button:hover { background: #0A1A0A; border-color: #4AFF99; }

  /* DataFrames */
  .stDataFrame { border: 1px solid #0F1F0F !important; }
  thead tr th { background: #060A06 !important; color: #1A3A1A !important; font-size: 9px !important; letter-spacing: 1px; }
  tbody tr td { color: #B8CCB8 !important; font-size: 10px !important; }
  tbody tr:hover td { background: #0A100A !important; }

  /* Slider */
  .stSlider [data-baseweb="slider"] { padding: 0 2px; }

  /* Select boxes */
  .stSelectbox [data-baseweb="select"] { background: #070C07; border-color: #0F1F0F; }

  /* Horizontal rule */
  hr { border-color: #0F1F0F; margin: 16px 0; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 3px; background: #07090D; }
  ::-webkit-scrollbar-thumb { background: #1A2A1A; border-radius: 2px; }

  /* Headers */
  h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; font-weight: 500 !important; letter-spacing: 1px; }

  /* Scanlines overlay */
  .stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.015) 2px,
      rgba(0,0,0,0.015) 4px
    );
  }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR BRAND ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 20px 4px 24px; border-bottom: 1px solid #0F1F0F; margin-bottom: 16px;">
      <div style="color: #4AFF99; font-size: 20px; font-weight: 700; letter-spacing: 3px; line-height: 1;">
        QCEX
      </div>
      <div style="color: #1A3A1A; font-size: 8px; letter-spacing: 2px; margin-top: 5px;">
        QUANTUM COMMODITY EXCHANGE
      </div>
      <div style="margin-top: 14px; padding: 8px 10px; background: #071407;
        border: 1px solid #1A3A1A; border-radius: 2px;">
        <div style="color: #0F2A0F; font-size: 7px; letter-spacing: 2px; margin-bottom: 3px;">BY</div>
        <div style="color: #4AFF99; font-size: 11px; font-weight: 600; letter-spacing: 1px;">
          QuantumPablo
        </div>
        <div style="color: #0F2A0F; font-size: 7px; margin-top: 3px; letter-spacing: 1px;">
          COMMODITY DERIVATIVES · QUANT FINANCE
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="color: #0F2A0F; font-size: 8px; letter-spacing: 2px; margin-bottom: 10px;">
      NAVIGATION
    </div>
    """, unsafe_allow_html=True)

    st.page_link("Home.py",                      label="◈  Home",            icon=None)
    st.page_link("pages/1_Market_Overview.py",   label="01  Market Overview", icon=None)
    st.page_link("pages/2_Futures_Pricer.py",    label="02  Futures Pricer",  icon=None)
    st.page_link("pages/3_Options_SABR.py",      label="03  Options · SABR",  icon=None)
    st.page_link("pages/4_Risk_Dashboard.py",    label="04  Risk Dashboard",  icon=None)

    st.markdown("""
    <div style="position: absolute; bottom: 24px; left: 16px; right: 16px;">
      <div style="border-top: 1px solid #0F1F0F; padding-top: 12px;">
        <div style="color: #071407; font-size: 7px; letter-spacing: 1px; line-height: 1.8;">
          MODELS<br>
          <span style="color: #0F2A0F;">Schwartz-Smith 2F · SABR<br>Black-76 · Kalman Filter</span>
        </div>
        <div style="color: #071407; font-size: 7px; letter-spacing: 1px; margin-top: 8px; line-height: 1.8;">
          RISK<br>
          <span style="color: #0F2A0F;">Hist. VaR · CVaR · Stress</span>
        </div>
        <div style="color: #071407; font-size: 7px; letter-spacing: 1px; margin-top: 8px; line-height: 1.8;">
          DATA<br>
          <span style="color: #0F2A0F;">yfinance · Synthetic fallback</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 8px 0 0;">
  <div style="display: flex; align-items: baseline; gap: 16px; margin-bottom: 6px;">
    <span style="color: #4AFF99; font-size: 32px; font-weight: 700; letter-spacing: 4px; line-height: 1;">
      QCEX
    </span>
    <span style="color: #1A3A1A; font-size: 10px; letter-spacing: 3px;">
      QUANTUM COMMODITY EXCHANGE
    </span>
  </div>
  <div style="color: #0F2A0F; font-size: 9px; letter-spacing: 1px; margin-bottom: 20px;">
    Schwartz-Smith 2F · Kalman Filter · SABR Vol Surface · Black-76 · Historical VaR/CVaR · Stress Testing
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="border-top: 1px solid #4AFF9944; margin-bottom: 24px;"></div>', unsafe_allow_html=True)

# ── MODULE CARDS ──────────────────────────────────────────────────────────────
cols = st.columns(4)
modules = [
    ("01", "MARKET OVERVIEW",
     "Spot prices via yfinance, historical vol, return distribution, correlation matrix, vol cone, drawdown analysis.",
     "#4AFF99", "cocoa · gas · uranium"),
    ("02", "FUTURES PRICER",
     "Schwartz-Smith 2-factor model with Kalman Filter. Interactive term structure, convenience yield, Monte Carlo fan chart.",
     "#F5D060", "SS-2F · Kalman · MC"),
    ("03", "OPTIONS · SABR",
     "SABR stochastic vol with Hagan approximation. Black-76 pricing. Full Greeks: Δ Γ ν Θ Vanna Volga. 3D surface.",
     "#7EC8FF", "SABR · Black-76 · Greeks"),
    ("04", "RISK DASHBOARD",
     "Historical & parametric VaR/CVaR, vol cone, commodity-specific stress scenarios, rolling risk, drawdown.",
     "#FF7EB3", "VaR · CVaR · Stress"),
]

for col, (num, title, desc, color, tags) in zip(cols, modules):
    with col:
        st.markdown(f"""
        <div style="background: #070C07; border: 1px solid #0F1F0F;
          border-top: 2px solid {color}; padding: 18px 16px; border-radius: 3px;
          height: 200px; position: relative; transition: all 0.2s;">
          <div style="color: {color}; font-size: 8px; letter-spacing: 3px; opacity: 0.5;">
            {num}
          </div>
          <div style="color: {color}; font-size: 12px; font-weight: 600;
            letter-spacing: 1.5px; margin: 6px 0 10px;">
            {title}
          </div>
          <div style="color: #1A3A1A; font-size: 9px; line-height: 1.6; margin-bottom: 12px;">
            {desc}
          </div>
          <div style="position: absolute; bottom: 14px; left: 16px; right: 16px;
            color: {color}; font-size: 7px; letter-spacing: 1px; opacity: 0.4;
            border-top: 1px solid #0F1F0F; padding-top: 8px;">
            {tags}
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── MODEL ARCHITECTURE SECTION ────────────────────────────────────────────────
st.markdown("""
<div style="color: #1A3A1A; font-size: 8px; letter-spacing: 3px; margin-bottom: 16px;">
  MODEL ARCHITECTURE
</div>
""", unsafe_allow_html=True)

col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown("""
    <div style="background: #070C07; border: 1px solid #0F1F0F; border-radius: 3px; padding: 20px 24px;">
      <div style="color: #4AFF99; font-size: 10px; font-weight: 600; letter-spacing: 2px; margin-bottom: 16px;">
        SCHWARTZ-SMITH TWO-FACTOR MODEL
      </div>
      <div style="color: #4AFF99; font-size: 13px; font-family: 'IBM Plex Mono', monospace;
        background: #071407; border-left: 2px solid #4AFF99; padding: 8px 14px;
        border-radius: 0 3px 3px 0; margin-bottom: 12px; letter-spacing: 1px;">
        ln S<sub>t</sub> = χ<sub>t</sub> + ξ<sub>t</sub>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
        <div style="background: #071407; border: 1px solid #0F1F0F; padding: 10px 12px; border-radius: 2px;">
          <div style="color: #4AFF99; font-size: 9px; font-weight: 600; margin-bottom: 4px;">χ<sub>t</sub> SHORT-TERM</div>
          <div style="color: #0F2A0F; font-size: 8px; line-height: 1.6;">Ornstein-Uhlenbeck<br>Mean-reverting<br>Supply/demand shocks<br>Half-life = ln2/κ</div>
        </div>
        <div style="background: #071407; border: 1px solid #0F1F0F; padding: 10px 12px; border-radius: 2px;">
          <div style="color: #4AFF99; font-size: 9px; font-weight: 600; margin-bottom: 4px;">ξ<sub>t</sub> LONG-TERM</div>
          <div style="color: #0F2A0F; font-size: 8px; line-height: 1.6;">GBM with drift<br>Permanent component<br>Production costs<br>Energy transition</div>
        </div>
      </div>
      <div style="color: #4AFF99; font-size: 11px; font-family: 'IBM Plex Mono', monospace;
        background: #071407; border-left: 2px solid #3A7A3A; padding: 8px 14px;
        border-radius: 0 3px 3px 0; letter-spacing: 0.5px;">
        ln F(t,T) = e<sup>−κτ</sup>·χ<sub>t</sub> + ξ<sub>t</sub> + A(τ)
      </div>
      <div style="color: #0F2A0F; font-size: 8px; margin-top: 8px; line-height: 1.6;">
        A(τ) encodes risk-adjusted drift, risk premia λ<sub>χ</sub> λ<sub>ξ</sub>, and Jensen corrections.<br>
        Latent states extracted via <strong style="color: #1A3A1A;">Kalman Filter MLE</strong> on observed futures term structure.
      </div>
    </div>

    <div style="background: #070C07; border: 1px solid #0F1F0F; border-radius: 3px;
      padding: 20px 24px; margin-top: 12px;">
      <div style="color: #7EC8FF; font-size: 10px; font-weight: 600; letter-spacing: 2px; margin-bottom: 16px;">
        SABR STOCHASTIC VOLATILITY
      </div>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
        <div style="text-align: center; padding: 10px 6px; background: #071020;
          border: 1px solid #0A1A2A; border-radius: 2px;">
          <div style="color: #F5D060; font-size: 16px; font-weight: 700; margin-bottom: 4px;">α</div>
          <div style="color: #1A2A3A; font-size: 7px; letter-spacing: 1px;">VOL LEVEL</div>
        </div>
        <div style="text-align: center; padding: 10px 6px; background: #071020;
          border: 1px solid #0A1A2A; border-radius: 2px;">
          <div style="color: #7EC8FF; font-size: 16px; font-weight: 700; margin-bottom: 4px;">β</div>
          <div style="color: #1A2A3A; font-size: 7px; letter-spacing: 1px;">CEV (=0.5)</div>
        </div>
        <div style="text-align: center; padding: 10px 6px; background: #071020;
          border: 1px solid #0A1A2A; border-radius: 2px;">
          <div style="color: #FF7EB3; font-size: 16px; font-weight: 700; margin-bottom: 4px;">ρ</div>
          <div style="color: #1A2A3A; font-size: 7px; letter-spacing: 1px;">SKEW</div>
        </div>
        <div style="text-align: center; padding: 10px 6px; background: #071020;
          border: 1px solid #0A1A2A; border-radius: 2px;">
          <div style="color: #4AFF99; font-size: 16px; font-weight: 700; margin-bottom: 4px;">ν</div>
          <div style="color: #1A2A3A; font-size: 7px; letter-spacing: 1px;">VOL OF VOL</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_r:
    # Commodity parameters table
    st.markdown("""
    <div style="background: #070C07; border: 1px solid #0F1F0F; border-radius: 3px; padding: 20px 24px;">
      <div style="color: #4AFF99; font-size: 10px; font-weight: 600; letter-spacing: 2px; margin-bottom: 16px;">
        CALIBRATED PARAMETERS
      </div>
    """, unsafe_allow_html=True)

    params_data = {
        "CACAO": {
            "color": "#D4A85A", "accent": "#F5D060",
            "spot": "9,240", "unit": "USD/MT",
            "kappa": "0.80", "hl": "10.4M",
            "sigma_chi": "38%", "sabr_rho": "−0.45", "sabr_nu": "0.68",
            "note": "El Niño · ICCO · supply crisis 2023-24"
        },
        "GAS TTF": {
            "color": "#3A8FFF", "accent": "#7EC8FF",
            "spot": "41.2", "unit": "EUR/MWh",
            "kappa": "2.10", "hl": "4.0M",
            "sigma_chi": "55%", "sabr_rho": "−0.25", "sabr_nu": "0.85",
            "note": "HDD seasonal · LNG flows · post-2022"
        },
        "URANIUM": {
            "color": "#3FFF88", "accent": "#7FFFC0",
            "spot": "78.5", "unit": "USD/lb",
            "kappa": "0.30", "hl": "27.6M",
            "sigma_chi": "28%", "sabr_rho": "−0.15", "sabr_nu": "0.42",
            "note": "OTC market · Kazatomprom · nuclear policy"
        },
    }

    for comm, p in params_data.items():
        st.markdown(f"""
        <div style="border: 1px solid #0F1F0F; border-left: 2px solid {p['color']};
          border-radius: 0 3px 3px 0; padding: 12px 14px; margin-bottom: 10px; background: #060A06;">
          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
            <span style="color: {p['accent']}; font-size: 10px; font-weight: 600; letter-spacing: 1px;">
              {comm}
            </span>
            <span style="color: {p['color']}; font-size: 13px; font-weight: 700;">
              {p['spot']} <span style="font-size: 8px; opacity: 0.6;">{p['unit']}</span>
            </span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 8px;">
            <div style="background: #071407; padding: 5px 8px; border-radius: 2px;">
              <div style="color: #0F2A0F; font-size: 7px; letter-spacing: 1px;">κ / HL</div>
              <div style="color: {p['color']}; font-size: 10px; font-weight: 600;">{p['kappa']} / {p['hl']}</div>
            </div>
            <div style="background: #071407; padding: 5px 8px; border-radius: 2px;">
              <div style="color: #0F2A0F; font-size: 7px; letter-spacing: 1px;">σ<sub>χ</sub></div>
              <div style="color: {p['color']}; font-size: 10px; font-weight: 600;">{p['sigma_chi']}</div>
            </div>
            <div style="background: #071407; padding: 5px 8px; border-radius: 2px;">
              <div style="color: #0F2A0F; font-size: 7px; letter-spacing: 1px;">SABR ρ / ν</div>
              <div style="color: {p['color']}; font-size: 10px; font-weight: 600;">{p['sabr_rho']} / {p['sabr_nu']}</div>
            </div>
          </div>
          <div style="color: #0F2A0F; font-size: 8px; font-style: italic;">{p['note']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # References
    st.markdown("""
    <div style="background: #070C07; border: 1px solid #0F1F0F; border-radius: 3px;
      padding: 16px 20px; margin-top: 12px;">
      <div style="color: #4AFF99; font-size: 9px; letter-spacing: 2px; margin-bottom: 10px;">REFERENCES</div>
      <div style="color: #0F2A0F; font-size: 8px; line-height: 2.0;">
        Black (1976) · Pricing of Commodity Contracts<br>
        Schwartz (1997) · Stochastic Behavior of Commodities<br>
        Schwartz &amp; Smith (2000) · Two-Factor Model<br>
        Hagan et al. (2002) · Managing Smile Risk (SABR)<br>
        Working (1949) · Theory of Price of Storage
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── FOOTER / SIGNATURE ────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top: 1px solid #0F1F0F; padding-top: 20px; margin-top: 8px;
  display: flex; justify-content: space-between; align-items: center;">
  <div>
    <span style="color: #4AFF99; font-size: 12px; font-weight: 700; letter-spacing: 2px;">QCEX</span>
    <span style="color: #0F2A0F; font-size: 9px; margin-left: 10px; letter-spacing: 1px;">
      Quantitative Risk &amp; Commodity Lab Engine
    </span>
  </div>
  <div style="text-align: right;">
    <div style="color: #1A3A1A; font-size: 9px; letter-spacing: 1px;">
      by <strong style="color: #4AFF99;">QuantumPablo</strong>
    </div>
    <div style="color: #0F2A0F; font-size: 8px; margin-top: 2px;">
      Commodity Derivatives · Quantitative Finance
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
