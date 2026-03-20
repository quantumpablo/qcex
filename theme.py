"""
theme.py — QCEX shared design tokens
Single source of truth for colors, CSS, and Plotly layout.
"""

# ── Design tokens ─────────────────────────────────────────────────────────────
BG      = "#0A0D12"   # page background
BG2     = "#111620"   # card / sidebar background
BG3     = "#0D1018"   # inner card background
ACC     = "#4AFF99"   # primary accent (green)
GOLD    = "#F5D060"   # futures / gold accent
BLUE    = "#5BAEFF"   # options / blue accent
PINK    = "#FF7EB3"   # risk / pink accent
TEXT    = "#C8D8C8"   # primary text
TEXT2   = "#6A8A6A"   # secondary text / labels
BORD    = "#1E2E1E"   # borders
GRID    = "#141E14"   # chart gridlines
RED     = "#FF4455"
GREEN   = "#3AEF80"

COMM_COLORS = {
    "cocoa":   "#D4A85A",
    "gas":     "#5BAEFF",
    "uranium": "#4AFF99",
    "gold":    "#FFE566",
}

# ── Minimal CSS — only custom elements, let config.toml handle base theme ────
CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

  /* Override Streamlit fonts */
  html, body, [class*="css"], .stMarkdown, .stText, button, label {{
    font-family: 'IBM Plex Mono', 'Courier New', monospace !important;
  }}

  /* Metric cards */
  [data-testid="metric-container"] {{
    background: {BG2};
    border: 1px solid {BORD};
    border-radius: 4px;
    padding: 10px 14px;
  }}
  [data-testid="metric-container"] label {{
    color: {TEXT2} !important;
    font-size: 9px !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {ACC} !important;
    font-size: 20px !important;
    font-weight: 600 !important;
  }}

  /* Tables */
  [data-testid="stDataFrame"] {{ border: 1px solid {BORD} !important; border-radius: 4px; }}
  [data-testid="stDataFrame"] th {{ background: {BG2} !important; color: {TEXT2} !important; font-size: 10px !important; }}
  [data-testid="stDataFrame"] td {{ color: {TEXT} !important; font-size: 10px !important; }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {BORD};
    gap: 0;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {TEXT2} !important;
    font-size: 9px !important;
    letter-spacing: 2px;
    padding: 10px 20px;
    border-bottom: 2px solid transparent !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {ACC} !important;
    border-bottom: 2px solid {ACC} !important;
  }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{
    border-right: 1px solid {BORD};
  }}

  /* Buttons */
  .stButton button {{
    background: transparent !important;
    border: 1px solid {ACC} !important;
    color: {ACC} !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 1.5px;
    border-radius: 3px;
  }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 3px; }}
  ::-webkit-scrollbar-thumb {{ background: {BORD}; border-radius: 2px; }}

  /* Divider */
  hr {{ border-color: {BORD} !important; margin: 16px 0; }}
</style>
"""

# ── Plotly base layout ────────────────────────────────────────────────────────
PLOTLY = dict(
    paper_bgcolor=BG,
    plot_bgcolor=BG3,
    font=dict(family="IBM Plex Mono", color=TEXT2, size=10),
    margin=dict(l=50, r=20, t=35, b=45),
)

# Use this when you need legend in update_layout
LEGEND = dict(bgcolor=BG2, bordercolor=BORD, borderwidth=1, font=dict(size=9, color=TEXT))

# Reusable axis style
def ax(title="", **kwargs):
    return dict(
        gridcolor=GRID,
        showgrid=True,
        zeroline=False,
        linecolor=BORD,
        tickcolor=TEXT2,
        tickfont=dict(color=TEXT2, size=9),
        title=dict(text=title, font=dict(color=TEXT2, size=10)),
        **kwargs,
    )

def card(content, color=None, padding="14px 16px"):
    """Render a styled card."""
    border_top = f"border-top:2px solid {color};" if color else ""
    return f"""
    <div style="background:{BG2};border:1px solid {BORD};{border_top}
      border-radius:4px;padding:{padding};margin-bottom:8px;">
      {content}
    </div>"""

def label(text):
    return f'<div style="color:{TEXT2};font-size:8px;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">{text}</div>'

def value(text, color=None):
    c = color or ACC
    return f'<div style="color:{c};font-size:15px;font-weight:600;">{text}</div>'

def footer(page_name=""):
    return f"""
    <div style="border-top:1px solid {BORD};padding-top:16px;margin-top:40px;
      display:flex;justify-content:space-between;align-items:center;">
      <div>
        <span style="color:{ACC};font-size:12px;font-weight:700;letter-spacing:2px;">QCEX</span>
        <span style="color:{TEXT2};font-size:8px;margin-left:10px;letter-spacing:1px;">
          QUANTUM COMMODITY EXCHANGE{" · " + page_name if page_name else ""}
        </span>
      </div>
      <div style="color:{TEXT2};font-size:8px;letter-spacing:1px;">
        by <strong style="color:{ACC};">QuantumPablo</strong> · Pablo M. Paniagua
      </div>
    </div>"""
