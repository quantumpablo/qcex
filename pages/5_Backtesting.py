"""pages/5_Backtesting.py — QCEX Backtesting Engine"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from theme import (CSS, LEGEND, BG, BG2, BG3, ACC, GOLD, BLUE, PINK,
                   TEXT, TEXT2, BORD, GRID, PLOTLY, ax, footer, COMM_COLORS)
from data.fetcher import fetch_prices, compute_returns, TICKERS
from analytics.backtest import (run_all_strategies, benchmark_buy_hold,
                                  STRATEGY_PARAMS)

st.set_page_config(page_title="QCEX · Backtesting", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='color:{GOLD};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>BACKTESTING ENGINE</div>", unsafe_allow_html=True)
    commodity = st.selectbox("Commodity", ["cocoa","gas","uranium"],
                              format_func=lambda x: TICKERS[x]["name"])
    period = st.select_slider("Period", options=[252, 504, 756, 1008], value=504,
                               format_func=lambda x: {252:"1Y",504:"2Y",756:"3Y",1008:"4Y"}[x])
    capital = st.number_input("Initial capital (USD)", value=100_000, step=10_000)
    tc = st.slider("Transaction cost (bps)", 0, 50, 10) / 10_000
    st.markdown("---")
    st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:1px;margin-bottom:8px;'>STRATEGIES</div>", unsafe_allow_html=True)
    for name, cfg in STRATEGY_PARAMS.items():
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{cfg["color"]};flex-shrink:0;"></div>'
            f'<div style="color:{TEXT2};font-size:8px;">{name}</div>'
            f'</div>', unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load(c, days):
    df = fetch_prices(c, days)
    return df["Close"].dropna()

with st.spinner("Running backtest..."):
    prices  = load(commodity, period)
    results = run_all_strategies(prices, commodity, float(capital), tc)
    bh      = benchmark_buy_hold(prices, float(capital))

comm_color = COMM_COLORS.get(commodity, ACC)

st.markdown(f"## BACKTESTING — {TICKERS[commodity]['name'].upper()}")
st.markdown(f"<div style='color:{TEXT2};font-size:9px;margin-bottom:16px;'>{len(prices)} days · ${capital:,.0f} initial capital · {tc*10000:.0f} bps transaction cost</div>", unsafe_allow_html=True)
st.markdown("---")

# ── Best strategy highlight ───────────────────────────────────────────────────
valid = {k:v for k,v in results.items() if "error" not in v}
if valid:
    best_name = max(valid, key=lambda k: valid[k]["metrics"]["sharpe"])
    best_m    = valid[best_name]["metrics"]

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Best Strategy",  best_name.split("(")[0].strip())
    c2.metric("Sharpe Ratio",   f"{best_m['sharpe']:.2f}")
    c3.metric("Total Return",   f"{best_m['total_return']:+.1f}%")
    c4.metric("Max Drawdown",   f"{best_m['max_drawdown']:.1f}%")
    c5.metric("Win Rate",       f"{best_m['win_rate']:.1f}%")
    st.markdown("---")

# ── Equity curves ─────────────────────────────────────────────────────────────
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:8px;'>EQUITY CURVES vs BUY & HOLD</div>", unsafe_allow_html=True)

fig = go.Figure()

# Buy & Hold benchmark
fig.add_trace(go.Scatter(
    x=bh["bt"].index, y=bh["bt"]["cum_pnl"],
    name="Buy & Hold", line=dict(color="#555555", width=1.5, dash="dot")))

# All strategies
for name, res in valid.items():
    if "bt" not in res: continue
    width = 2.5 if name == best_name else 1.2
    fig.add_trace(go.Scatter(
        x=res["bt"].index, y=res["bt"]["cum_pnl"],
        name=name, line=dict(color=res["color"], width=width)))

fig.add_hline(y=0, line_color=BORD, line_dash="dot")
fig.update_layout(**PLOTLY, height=360,
    xaxis=ax(), yaxis=ax("PnL (USD)"),
    legend=LEGEND)
st.plotly_chart(fig, use_container_width=True)

# ── Metrics comparison table ──────────────────────────────────────────────────
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin:16px 0 8px;'>STRATEGY COMPARISON</div>", unsafe_allow_html=True)

rows = []
for name, res in valid.items():
    m = res["metrics"]
    rows.append({
        "Strategy"    : name,
        "Ann. Return" : f"{m['ann_return']:+.1f}%",
        "Sharpe"      : f"{m['sharpe']:.2f}",
        "Sortino"     : f"{m['sortino']:.2f}",
        "Max DD"      : f"{m['max_drawdown']:.1f}%",
        "Calmar"      : f"{m['calmar']:.2f}",
        "Win Rate"    : f"{m['win_rate']:.1f}%",
        "Total PnL"   : f"${m['total_pnl']:+,.0f}",
        "Trades"      : str(m["n_trades"]),
    })

# Add benchmark
bh_m = bh["metrics"]
rows.append({
    "Strategy"    : "★ Buy & Hold",
    "Ann. Return" : f"{bh_m['ann_return']:+.1f}%",
    "Sharpe"      : f"{bh_m['sharpe']:.2f}",
    "Sortino"     : f"{bh_m['sortino']:.2f}",
    "Max DD"      : f"{bh_m['max_drawdown']:.1f}%",
    "Calmar"      : f"{bh_m['calmar']:.2f}",
    "Win Rate"    : f"{bh_m['win_rate']:.1f}%",
    "Total PnL"   : f"${bh_m['total_pnl']:+,.0f}",
    "Trades"      : "0",
})

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Best strategy deep dive ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>DEEP DIVE — {best_name.upper()}</div>", unsafe_allow_html=True)

best_bt = valid[best_name]["bt"]
best_color = valid[best_name]["color"]

col_dd, col_sig = st.columns(2)

with col_dd:
    st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:1px;margin-bottom:6px;'>DRAWDOWN</div>", unsafe_allow_html=True)
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=best_bt.index, y=best_bt["drawdown"],
        fill="tozeroy", name="Drawdown",
        line=dict(color="#FF4455", width=1),
        fillcolor="rgba(255,68,85,0.12)"))
    fig_dd.add_hline(y=best_m["max_drawdown"], line_dash="dash",
        line_color=PINK, annotation_text=f"Max DD: {best_m['max_drawdown']:.1f}%",
        annotation_font_color=PINK, annotation_font_size=9)
    fig_dd.update_layout(**PLOTLY, height=240, xaxis=ax(), yaxis=ax("DD (%)"))
    st.plotly_chart(fig_dd, use_container_width=True)

with col_sig:
    st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:1px;margin-bottom:6px;'>POSITION SIGNAL</div>", unsafe_allow_html=True)
    fig_sig = go.Figure()
    fig_sig.add_trace(go.Scatter(
        x=best_bt.index, y=best_bt["signal"],
        name="Signal", line=dict(color=best_color, width=1),
        fill="tozeroy", fillcolor=f"rgba(100,200,100,0.08)"))
    fig_sig.add_hline(y=0, line_color=BORD)
    fig_sig.add_hline(y=1,  line_dash="dot", line_color=GRID)
    fig_sig.add_hline(y=-1, line_dash="dot", line_color=GRID)
    fig_sig.update_layout(**PLOTLY, height=240,
        xaxis=ax(), yaxis=ax("Position", range=[-1.2, 1.2]))
    st.plotly_chart(fig_sig, use_container_width=True)

# ── Return distribution ───────────────────────────────────────────────────────
st.markdown(f"<div style='color:{TEXT2};font-size:8px;letter-spacing:1px;margin:12px 0 6px;'>DAILY RETURN DISTRIBUTION — {best_name}</div>", unsafe_allow_html=True)

col_hist, col_metrics = st.columns([2, 1])

with col_hist:
    daily_rets = best_bt["strategy_ret"].dropna() * 100
    fig_h = go.Figure()
    fig_h.add_trace(go.Histogram(
        x=daily_rets, nbinsx=60,
        marker_color=best_color, opacity=0.75, name="Strategy"))
    fig_h.add_trace(go.Histogram(
        x=bh["bt"]["strategy_ret"].dropna()*100, nbinsx=60,
        marker_color="#555555", opacity=0.4, name="Buy & Hold"))
    fig_h.update_layout(**PLOTLY, height=240, barmode="overlay",
        xaxis=ax("Daily return (%)"), yaxis=ax("Frequency"),
        legend=LEGEND)
    st.plotly_chart(fig_h, use_container_width=True)

with col_metrics:
    m = best_m
    stat_items = [
        ("Ann. Return",  f"{m['ann_return']:+.1f}%",  ACC if m['ann_return']>0 else "#FF4455"),
        ("Ann. Vol",     f"{m['ann_vol']:.1f}%",       GOLD),
        ("Sharpe",       f"{m['sharpe']:.2f}",         ACC if m['sharpe']>0.5 else GOLD),
        ("Sortino",      f"{m['sortino']:.2f}",        ACC if m['sortino']>0.5 else GOLD),
        ("Calmar",       f"{m['calmar']:.2f}",         ACC if m['calmar']>0.5 else GOLD),
        ("Best day",     f"{m['best_day']:+.2f}%",     ACC),
        ("Worst day",    f"{m['worst_day']:+.2f}%",    "#FF4455"),
        ("# Trades",     str(m["n_trades"]),            TEXT),
    ]
    for label, val, color in stat_items:
        st.markdown(
            f'<div style="background:{BG2};border:1px solid {BORD};padding:7px 12px;'
            f'border-radius:3px;margin-bottom:4px;display:flex;justify-content:space-between;">'
            f'<span style="color:{TEXT2};font-size:9px;">{label}</span>'
            f'<span style="color:{color};font-size:11px;font-weight:600;">{val}</span>'
            f'</div>', unsafe_allow_html=True)

# ── Cross-commodity comparison ────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"<div style='color:{TEXT2};font-size:9px;letter-spacing:2px;margin-bottom:12px;'>COMBINED STRATEGY — ALL COMMODITIES</div>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def run_all_commodities(days, cap, cost):
    out = {}
    for c in ["cocoa","gas","uranium"]:
        p = fetch_prices(c, days)["Close"].dropna()
        r = run_all_strategies(p, c, cap, cost)
        bh_c = benchmark_buy_hold(p, cap)
        out[c] = {"results": r, "bh": bh_c, "prices": p}
    return out

with st.spinner("Running cross-commodity analysis..."):
    all_results = run_all_commodities(period, float(capital), tc)

fig_cross = go.Figure()
for c, data in all_results.items():
    valid_c = {k:v for k,v in data["results"].items() if "error" not in v}
    if not valid_c: continue
    best_c = max(valid_c, key=lambda k: valid_c[k]["metrics"]["sharpe"])
    bt_c   = valid_c[best_c]["bt"]
    color  = COMM_COLORS.get(c, "#888")
    fig_cross.add_trace(go.Scatter(
        x=bt_c.index, y=bt_c["cum_pnl"],
        name=f"{TICKERS[c]['name']} ({best_c.split('(')[0].strip()})",
        line=dict(color=color, width=2)))

fig_cross.add_hline(y=0, line_color=BORD, line_dash="dot")
fig_cross.update_layout(**PLOTLY, height=300,
    xaxis=ax(), yaxis=ax("PnL (USD)"),
    legend=LEGEND)
st.plotly_chart(fig_cross, use_container_width=True)

# Summary table cross-commodity
cross_rows = []
for c, data in all_results.items():
    valid_c = {k:v for k,v in data["results"].items() if "error" not in v}
    if not valid_c: continue
    best_c = max(valid_c, key=lambda k: valid_c[k]["metrics"]["sharpe"])
    m = valid_c[best_c]["metrics"]
    bh_m_c = data["bh"]["metrics"]
    cross_rows.append({
        "Commodity"   : TICKERS[c]["name"],
        "Best Strategy": best_c.split("(")[0].strip(),
        "Sharpe"      : f"{m['sharpe']:.2f}",
        "Ann. Return" : f"{m['ann_return']:+.1f}%",
        "Max DD"      : f"{m['max_drawdown']:.1f}%",
        "Win Rate"    : f"{m['win_rate']:.1f}%",
        "vs B&H"      : f"{m['total_return']-bh_m_c['total_return']:+.1f}pp",
    })

st.dataframe(pd.DataFrame(cross_rows), use_container_width=True, hide_index=True)

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{BG3};border:1px solid {BORD};border-left:3px solid {GOLD};
  padding:12px 16px;border-radius:0 4px 4px 0;margin-top:16px;">
  <div style="color:{GOLD};font-size:8px;letter-spacing:2px;margin-bottom:6px;">DISCLAIMER</div>
  <div style="color:{TEXT2};font-size:8px;line-height:1.8;">
    Past performance is not indicative of future results. This backtest uses synthetic or
    ETF-proxy price data (CC=F, NG=F, URA) and does not account for slippage, market impact,
    margin requirements, or roll costs on futures contracts. Transaction costs are approximated.
    For research and educational purposes only.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(footer("Backtesting"), unsafe_allow_html=True)
