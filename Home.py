"""
Home.py — QCEX · Quantum Commodity Exchange
Entry point with light/dark mode support
"""
import streamlit as st

st.set_page_config(
    page_title="QCEX · QuantumPablo",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

with st.sidebar:
    dark = st.toggle("Modo oscuro", value=st.session_state.dark_mode, key="home_dark")
    st.session_state.dark_mode = dark

# ── Theme ─────────────────────────────────────────────────────────────────────
if dark:
    BG    = "#07090D"
    BG2   = "#070C07"
    TEXT  = "#B8CCB8"
    TEXT2 = "#3A5A3A"
    TEXT3 = "#1A3A1A"
    BORD  = "#0F1F0F"
    ACC   = "#4AFF99"
    HEAD  = "rgba(255,255,255,0.03)"
else:
    BG    = "#F4FAF4"
    BG2   = "#FFFFFF"
    TEXT  = "#1A2A1A"
    TEXT2 = "#3A5A3A"
    TEXT3 = "#5A8A5A"
    BORD  = "#CCDDCC"
    ACC   = "#1A6A2A"
    HEAD  = "rgba(0,0,0,0.03)"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] {{
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: {BG} !important;
    color: {TEXT} !important;
  }}
  .stApp {{ background-color: {BG} !important; }}
  section[data-testid="stSidebar"] {{
    background: {BG2} !important;
    border-right: 1px solid {BORD};
  }}
  section[data-testid="stSidebar"] * {{ color: {TEXT2} !important; }}
  h1, h2, h3 {{ color: {ACC} !important; font-family: 'IBM Plex Mono', monospace !important; }}
  hr {{ border-color: {BORD}; }}
  ::-webkit-scrollbar {{ width: 3px; background: {BG}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORD}; border-radius: 2px; }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar brand ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 4px 20px;border-bottom:1px solid {BORD};margin-bottom:14px;">
      <div style="color:{ACC};font-size:22px;font-weight:700;letter-spacing:3px;">QCEX</div>
      <div style="color:{TEXT3};font-size:8px;letter-spacing:2px;margin-top:4px;">QUANTUM COMMODITY EXCHANGE</div>
      <div style="margin-top:12px;padding:8px 10px;background:{BG};border:1px solid {BORD};border-radius:2px;">
        <div style="color:{TEXT3};font-size:7px;letter-spacing:2px;margin-bottom:2px;">BY</div>
        <div style="color:{ACC};font-size:11px;font-weight:600;">QuantumPablo</div>
        <div style="color:{TEXT3};font-size:7px;margin-top:2px;">Pablo M. Paniagua</div>
      </div>
    </div>
    <div style="color:{TEXT3};font-size:8px;letter-spacing:2px;margin-bottom:10px;">MODELS</div>
    <div style="color:{TEXT2};font-size:9px;line-height:2.0;">
      Schwartz-Smith 2F · SABR<br>Black-76 · Kalman Filter
    </div>
    <div style="color:{TEXT3};font-size:8px;letter-spacing:2px;margin:12px 0 6px;">RISK</div>
    <div style="color:{TEXT2};font-size:9px;">Hist. VaR · CVaR · Stress</div>
    <div style="color:{TEXT3};font-size:8px;letter-spacing:2px;margin:12px 0 6px;">DATA</div>
    <div style="color:{TEXT2};font-size:9px;">yfinance · Synthetic fallback</div>
    """, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:8px 0 20px;">
  <div style="color:{ACC};font-size:30px;font-weight:700;letter-spacing:4px;line-height:1;">QCEX</div>
  <div style="color:{TEXT2};font-size:11px;letter-spacing:2px;margin-top:6px;">QUANTUM COMMODITY EXCHANGE</div>
  <div style="color:{TEXT3};font-size:9px;margin-top:4px;">
    Schwartz-Smith 2F · Kalman Filter · SABR Vol Surface · Black-76 · Historical VaR/CVaR · Stress Testing
  </div>
</div>
<div style="border-top:1px solid {ACC};opacity:0.3;margin-bottom:24px;"></div>
""", unsafe_allow_html=True)

# ── Module cards ──────────────────────────────────────────────────────────────
modules = [
    ("01", "MARKET OVERVIEW",
     "Spot prices via yfinance, historical vol, return distribution, correlation matrix, vol cone, drawdown.",
     ACC, "cocoa · gas · uranium"),
    ("02", "FUTURES PRICER",
     "Schwartz-Smith 2-factor + Kalman Filter. Term structure, convenience yield, Monte Carlo fan chart.",
     "#F5D060", "SS-2F · Kalman · MC"),
    ("03", "OPTIONS · SABR",
     "SABR vol surface + Hagan approx. Black-76 pricing. Full Greeks: Δ Γ ν Θ Vanna Volga. 3D surface.",
     "#7EC8FF", "SABR · Black-76 · Greeks"),
    ("04", "RISK DASHBOARD",
     "Historical & parametric VaR/CVaR, vol cone, stress scenarios, rolling risk, drawdown analysis.",
     "#FF7EB3", "VaR · CVaR · Stress"),
]

cols = st.columns(4)
for col, (num, title, desc, color, tags) in zip(cols, modules):
    with col:
        st.markdown(f"""
        <div style="background:{BG2};border:1px solid {BORD};border-top:2px solid {color};
          padding:18px 16px;border-radius:3px;height:190px;position:relative;">
          <div style="color:{color};font-size:8px;letter-spacing:3px;opacity:0.5;">{num}</div>
          <div style="color:{color};font-size:12px;font-weight:600;letter-spacing:1px;margin:6px 0 10px;">{title}</div>
          <div style="color:{TEXT2};font-size:9px;line-height:1.6;">{desc}</div>
          <div style="position:absolute;bottom:14px;left:16px;right:16px;color:{color};
            font-size:7px;letter-spacing:1px;opacity:0.4;border-top:1px solid {BORD};padding-top:8px;">{tags}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("## MODEL ARCHITECTURE")

col_l, col_r = st.columns([3, 2])

with col_l:
    # SS model box
    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {BORD};border-radius:3px;padding:20px 24px;margin-bottom:12px;">
      <div style="color:{ACC};font-size:10px;font-weight:600;letter-spacing:2px;margin-bottom:14px;">SCHWARTZ-SMITH TWO-FACTOR MODEL</div>
      <div style="color:{ACC};font-size:13px;font-family:monospace;background:{BG};border-left:2px solid {ACC};
        padding:8px 14px;border-radius:0 3px 3px 0;margin-bottom:12px;">
        ln S<sub>t</sub> = &chi;<sub>t</sub> + &xi;<sub>t</sub>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
        <div style="background:{BG};border:1px solid {BORD};padding:10px 12px;border-radius:2px;">
          <div style="color:{ACC};font-size:9px;font-weight:600;margin-bottom:4px;">&chi;<sub>t</sub> CORTO PLAZO</div>
          <div style="color:{TEXT2};font-size:8px;line-height:1.7;">Ornstein-Uhlenbeck<br>Reversión a la media<br>Shocks oferta/demanda<br>Semivida = ln2/&kappa;</div>
        </div>
        <div style="background:{BG};border:1px solid {BORD};padding:10px 12px;border-radius:2px;">
          <div style="color:{ACC};font-size:9px;font-weight:600;margin-bottom:4px;">&xi;<sub>t</sub> LARGO PLAZO</div>
          <div style="color:{TEXT2};font-size:8px;line-height:1.7;">GBM con drift<br>Componente permanente<br>Costes de producción<br>Transición energética</div>
        </div>
      </div>
      <div style="color:{ACC};font-size:11px;font-family:monospace;background:{BG};border-left:2px solid {BORD};
        padding:8px 14px;border-radius:0 3px 3px 0;">
        ln F(t,T) = e<sup>-&kappa;&tau;</sup>&middot;&chi;<sub>t</sub> + &xi;<sub>t</sub> + A(&tau;)
      </div>
    </div>
    <div style="background:{BG2};border:1px solid {BORD};border-radius:3px;padding:18px 24px;">
      <div style="color:#7EC8FF;font-size:10px;font-weight:600;letter-spacing:2px;margin-bottom:14px;">SABR STOCHASTIC VOLATILITY</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
        {"".join([f'<div style="text-align:center;padding:10px 6px;background:{BG};border:1px solid {BORD};border-radius:2px;"><div style="color:{c};font-size:18px;font-weight:700;margin-bottom:4px;">{p}</div><div style="color:{TEXT3};font-size:7px;letter-spacing:1px;">{l}</div></div>' for p,c,l in [("α","#F5D060","VOL LEVEL"),("β","#7EC8FF","CEV (=0.5)"),("ρ","#FF7EB3","SKEW"),("ν","#4AFF99","VOL OF VOL")]])}
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_r:
    params_data = [
        ("CACAO",   "#D4A85A","#F5D060","9,240","USD/MT","0.80","10.4M","38%","−0.45","0.68","El Niño · ICCO · supply crisis 2023-24"),
        ("GAS TTF", "#3A8FFF","#7EC8FF","41.2", "EUR/MWh","2.10","4.0M","55%","−0.25","0.85","HDD seasonal · LNG flows · post-2022"),
        ("URANIUM", "#3FFF88","#7FFFC0","78.5", "USD/lb","0.30","27.6M","28%","−0.15","0.42","OTC market · Kazatomprom · nuclear policy"),
    ]
    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {BORD};border-radius:3px;padding:20px 24px;">
      <div style="color:{ACC};font-size:10px;font-weight:600;letter-spacing:2px;margin-bottom:14px;">CALIBRATED PARAMETERS</div>
    """, unsafe_allow_html=True)
    for name,c,ac,spot,unit,kappa,hl,schi,srho,snu,note in params_data:
        st.markdown(f"""
        <div style="border:1px solid {BORD};border-left:2px solid {c};border-radius:0 3px 3px 0;
          padding:12px 14px;margin-bottom:10px;background:{BG};">
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
            <span style="color:{ac};font-size:10px;font-weight:600;letter-spacing:1px;">{name}</span>
            <span style="color:{c};font-size:14px;font-weight:700;">{spot} <span style="font-size:8px;opacity:0.6;">{unit}</span></span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-bottom:8px;">
            <div style="background:{BG2};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT3};font-size:7px;letter-spacing:1px;">&kappa; / HL</div>
              <div style="color:{c};font-size:10px;font-weight:600;">{kappa} / {hl}</div>
            </div>
            <div style="background:{BG2};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT3};font-size:7px;">&sigma;&chi;</div>
              <div style="color:{c};font-size:10px;font-weight:600;">{schi}</div>
            </div>
            <div style="background:{BG2};padding:5px 8px;border-radius:2px;border:1px solid {BORD};">
              <div style="color:{TEXT3};font-size:7px;">SABR &rho; / &nu;</div>
              <div style="color:{c};font-size:10px;font-weight:600;">{srho} / {snu}</div>
            </div>
          </div>
          <div style="color:{TEXT3};font-size:8px;font-style:italic;">{note}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
      <div style="border-top:1px solid {BORD};padding-top:12px;margin-top:4px;">
        <div style="color:{ACC};font-size:9px;letter-spacing:2px;margin-bottom:8px;">REFERENCES</div>
        <div style="color:{TEXT2};font-size:8px;line-height:2.0;">
          Black (1976) · Pricing of Commodity Contracts<br>
          Schwartz (1997) · Stochastic Behavior of Commodities<br>
          Schwartz &amp; Smith (2000) · Two-Factor Model<br>
          Hagan et al. (2002) · Managing Smile Risk (SABR)<br>
          Working (1949) · Theory of Price of Storage
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-top:1px solid {BORD};padding-top:20px;margin-top:32px;
  display:flex;justify-content:space-between;align-items:center;">
  <div>
    <span style="color:{ACC};font-size:13px;font-weight:700;letter-spacing:2px;">QCEX</span>
    <span style="color:{TEXT3};font-size:9px;margin-left:10px;">Quantum Commodity Exchange</span>
  </div>
  <div style="text-align:right;">
    <div style="color:{TEXT2};font-size:9px;letter-spacing:1px;">
      by <strong style="color:{ACC};">QuantumPablo</strong> · Pablo M. Paniagua
    </div>
    <div style="color:{TEXT3};font-size:8px;margin-top:2px;">Commodity Derivatives · Quantitative Finance</div>
  </div>
</div>
""", unsafe_allow_html=True)
