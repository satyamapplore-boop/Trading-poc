import os
import random
import base64
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────────────────────────────────────────
# Logo
# ─────────────────────────────────────────────────────────────────────────────
def _logo_b64():
    p = os.path.join(os.path.dirname(__file__), "applore_logo.png")
    try:
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

LOGO = _logo_b64()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Applore Technologies Trading POC",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], .main {
    font-family: 'Inter', sans-serif !important;
    background-color: #0b0e11 !important;
    color: #e0e0e0 !important;
}
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="collapsedControl"], header { visibility: hidden !important; height: 0 !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }

div.stMarkdown p, div.stMetric { color: #e0e0e0 !important; }
div[data-testid="stHorizontalBlock"] { background-color: transparent !important; }
[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; color: #fff !important; }
[data-testid="stMetricDelta"]  { font-size: 0.9rem; font-weight: 600; }
[data-testid="stMetricLabel"]  { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8b929a !important; }

.card { background:#161a1e; border:1px solid #2b3139; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 4px 12px rgba(0,0,0,.4); }
.card-title { font-size:1.05rem; font-weight:600; color:#fff; margin-bottom:14px; border-bottom:1px solid #2b3139; padding-bottom:8px; }

.color-up   { color:#0ecb81 !important; }
.color-down { color:#f6465d !important; }
.badge-strategy { background:#2b3139; color:#e0e0e0; padding:4px 10px; border-radius:4px; font-size:.8rem; font-weight:600; }
hr { border-color:#2b3139 !important; }
h1,h2,h3,h4,strong,b { color:#fff !important; font-weight:600 !important; }
.stDataFrame { border:1px solid #2b3139; border-radius:6px; }

/* ── Tabs ── */
div[data-testid="stTabs"] > div:first-child {
    background: #161a1e;
    border: 1px solid #2b3139;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px !important;
    color: #848e9c !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 9px 16px !important;
    transition: all 0.2s !important;
    border-bottom: none !important;
}
button[data-baseweb="tab"]:hover {
    background: #1f2933 !important;
    color: #e0e0e0 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: #0ecb81 !important;
    color: #0b0e11 !important;
    box-shadow: 0 0 14px rgba(14,203,129,0.4) !important;
}
div[data-testid="stTabContent"] { padding-top: 16px !important; }
div[role="tablist"] > div[data-baseweb="tab-highlight"] { display:none !important; }
div[role="tablist"] > div[data-baseweb="tab-border"]    { display:none !important; }

/* ── Order book ── */
.ob-row { display:flex; align-items:center; padding:2px 4px; position:relative; }
.ob-bar  { position:absolute; right:0; top:0; bottom:0; opacity:.18; border-radius:2px; }
.ob-ask-bar { background:#f6465d; }
.ob-bid-bar { background:#0ecb81; }
.ob-price-ask { color:#f6465d; font-weight:500; font-size:12px; width:90px; z-index:1; }
.ob-price-bid { color:#0ecb81; font-weight:500; font-size:12px; width:90px; z-index:1; }
.ob-qty   { color:#848e9c; font-size:12px; width:72px; text-align:right; z-index:1; }
.ob-total { color:#5a6370; font-size:11px; width:68px; text-align:right; z-index:1; }

/* ── Price Flash ── */
@keyframes flash-up   { 0%{background:rgba(14,203,129,.4)} 100%{background:transparent} }
@keyframes flash-down { 0%{background:rgba(246,70, 93,.4)} 100%{background:transparent} }
.flash-up   { animation:flash-up   0.9s ease-out; border-radius:4px; padding:2px 6px; display:inline-block; }
.flash-down { animation:flash-down 0.9s ease-out; border-radius:4px; padding:2px 6px; display:inline-block; }

/* ── Trade row ── */
.trade-row { display:flex; justify-content:space-between; padding:2px 0; font-size:12px; font-family:monospace; }

/* Ticker bar */
.ticker-strip { background:#161a1e; border:1px solid #2b3139; border-radius:6px; padding:12px 20px;
               display:flex; flex-wrap:wrap; align-items:center; gap:0; margin-bottom:10px; }
.tick-sep { color:#2b3139; margin:0 14px; }
.sbox { display:flex; flex-direction:column; }
.slbl { font-size:.7rem; color:#848e9c; }
.sval { font-size:.88rem; color:#e0e0e0; font-weight:bold; }

/* Buttons */
.btn-buy  { background:#0ecb81; color:#0b0e11; width:100%; padding:11px; border:none; border-radius:4px; font-weight:700; cursor:pointer; font-size:14px; }
.btn-sell { background:#f6465d; color:#fff;    width:100%; padding:11px; border:none; border-radius:4px; font-weight:700; cursor:pointer; font-size:14px; }

/* ── Streamlit Primary Button Override (Orange Theme) ── */
button[kind="primary"] {
    background-color: #f7931a !important;
    border-color: #f7931a !important;
    color: #161a1e !important;
    font-weight: 800 !important;
    border-radius: 6px !important;
}
button[kind="primary"]:hover {
    background-color: #e88612 !important;
    border-color: #e88612 !important;
    color: #fff !important;
}

/* Eliminate Streamlit fragment update pulsing (Opacity flicker) */
[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"], .stElementContainer {
    opacity: 1 !important;
    transition: none !important;
}

/* Fix input label visibility (e.g. Price, Amount forms) */
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] div {
    color: #ffffff !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Binance API helpers  (separate caches for different refresh rates)
# ─────────────────────────────────────────────────────────────────────────────
BASE = "https://api.binance.com/api/v3"

@st.cache_data(ttl=2, show_spinner=False)
def api_ticker(sym="BTCUSDT"):
    try:
        return requests.get(f"{BASE}/ticker/24hr?symbol={sym}", timeout=4).json()
    except Exception:
        return None

@st.cache_data(ttl=1, show_spinner=False)
def api_depth(sym="BTCUSDT", lim=16):
    try:
        return requests.get(f"{BASE}/depth?symbol={sym}&limit={lim}", timeout=4).json()
    except Exception:
        return {}

@st.cache_data(ttl=2, show_spinner=False)
def api_trades(sym="BTCUSDT", lim=22):
    try:
        return requests.get(f"{BASE}/trades?symbol={sym}&limit={lim}", timeout=4).json()
    except Exception:
        return []

@st.cache_data(ttl=30, show_spinner=False)
def api_klines(sym="BTCUSDT", interval="5m", lim=80):
    try:
        return requests.get(f"{BASE}/klines?symbol={sym}&interval={interval}&limit={lim}", timeout=5).json()
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────
def init():
    if "inited" in st.session_state:
        return
    st.session_state.inited   = True
    st.session_state.balance  = 2_500_000.0
    st.session_state.invested = 1_850_000.0
    # Start manual holdings at 0 so test trades have a clean cost-basis (Avg Entry = Live Price)
    st.session_state.holdings = {"BTC": 0.0, "ETH": 0.0, "BNB": 0.0, "XRP": 0.0, "SOL": 0.0}
    st.session_state.active_asset = "BTC"
    st.session_state.prev_btc = None
    st.session_state.wallet_history = [
        {"Date": (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"), "Type":"Deposit","Amount":"$2,000,000","Status":"Completed"},
        {"Date": (datetime.now()-timedelta(days=15)).strftime("%Y-%m-%d"), "Type":"Deposit","Amount":"$500,000",  "Status":"Completed"},
    ]
    st.session_state.prices = {"BTC":69000,"ETH":3500,"BNB":590,"SOL":145,"XRP":0.62}
    st.session_state.avg_entry = {"BTC": 0.0, "ETH": 0.0, "BNB": 0.0, "XRP": 0.0, "SOL": 0.0}
    strats = ["Trend Following","Mean Reversion","Momentum Trading","Cross-Exchange Arbitrage","DCA"]
    st.session_state.positions = []
    for i, a in enumerate(["BTC","ETH","SOL","BNB"]):
        ep = st.session_state.prices[a] * (1 - random.uniform(-0.02, 0.05))
        sz = random.uniform(50_000, 300_000) / ep
        sl = random.choice(["Fixed","Trailing","ATR-based"])
        st.session_state.positions.append({
            "id":i,"asset":a,"strategy":random.choice(strats),
            "direction":random.choice(["LONG","SHORT"]),
            "entry":ep,"size":sz,"sl_type":sl,
            "sl_price":ep*(0.95 if sl=="Fixed" else 0.98),
        })
    st.session_state.trade_hist = []
    for _ in range(10):
        a = random.choice(["BTC","ETH","SOL"])
        st.session_state.trade_hist.append({
            "Time":(datetime.now()-timedelta(minutes=random.randint(10,1440))).strftime("%Y-%m-%d %H:%M"),
            "Asset":a,"Strategy":random.choice(strats),
            "Direction":"LONG" if random.random()>.5 else "SHORT",
            "P&L":random.uniform(-5000,15000),
        })
    st.session_state.notifs = ["System initialised — engine connected to exchange APIs."]

init()

# ─────────────────────────────────────────────────────────────────────────────
# Market tick (simulated for portfolio page)
# ─────────────────────────────────────────────────────────────────────────────
def tick():
    strats = ["Trend Following","Mean Reversion","Momentum Trading","Cross-Exchange Arbitrage","DCA"]
    for a in st.session_state.prices:
        vol = 0.001 if a in ("BTC","ETH") else 0.003
        st.session_state.prices[a] *= 1 + random.uniform(-vol, vol)

    if random.random() < 0.1 and st.session_state.positions:
        idx  = random.randint(0, len(st.session_state.positions)-1)
        pos  = st.session_state.positions.pop(idx)
        curr = st.session_state.prices[pos["asset"]]
        pnl  = (curr-pos["entry"])*pos["size"] if pos["direction"]=="LONG" else (pos["entry"]-curr)*pos["size"]
        st.session_state.trade_hist.insert(0, {
            "Time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Asset":pos["asset"],"Strategy":pos["strategy"],
            "Direction":pos["direction"],"P&L":pnl,
        })
        st.session_state.notifs.insert(0,
            f"🤖 {pos['direction']} exit on {pos['asset']} via {pos['strategy']}. P&L: ${pnl:+,.2f}")
        a2  = random.choice(["BTC","ETH","SOL","BNB","XRP"])
        ep2 = st.session_state.prices[a2]
        sl2 = random.choice(["Fixed","Trailing","ATR-based"])
        np2 = {"id":random.randint(100,999),"asset":a2,"strategy":random.choice(strats),
               "direction":random.choice(["LONG","SHORT"]),"entry":ep2,
               "size":random.uniform(50_000,200_000)/ep2,"sl_type":sl2,"sl_price":ep2*0.95}
        st.session_state.positions.append(np2)
        st.session_state.notifs.insert(0,
            f"⚡ Signal: Opening {np2['direction']} {np2['asset']} via {np2['strategy']}.")

tick()
st.session_state.notifs = st.session_state.notifs[:5]

# ─────────────────────────────────────────────────────────────────────────────
# Removed st_autorefresh to prevent full-page flicker, using st.fragment instead.
# ─────────────────────────────────────────────────────────────────────────────

@st.fragment(run_every=3)
def render_header():
    hc1, hc2, hc3 = st.columns([3, 4, 2])
    with hc1:
        logo_img = (f"<img src='data:image/png;base64,{LOGO}' "
                    f"style='height:48px;width:auto;object-fit:contain;' alt='Applore'>") if LOGO else "🚀"
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:12px;padding:6px 0;'>
            {logo_img}
            <div>
                <div style='font-size:1.1rem;font-weight:800;color:#fff;letter-spacing:-.01em;line-height:1.2;'>Applore Technologies</div>
                <div style='font-size:.82rem;font-weight:600;color:#a0a8b0;line-height:1.3;'>Trading POC</div>
                <div style='color:#0ecb81;font-size:11px;font-weight:700;margin-top:2px;letter-spacing:.08em;'>● LIVE CONNECTION SECURED</div>
            </div>
        </div>""", unsafe_allow_html=True)
    with hc2:
        tk = api_ticker()
        if tk:
            hp  = float(tk.get("lastPrice", 0))
            hpc = float(tk.get("priceChangePercent", 0))
            hcl = "#0ecb81" if hpc >= 0 else "#f6465d"
            harr = "▲" if hpc >= 0 else "▼"
            st.markdown(f"""
            <div style='display:flex;align-items:center;height:100%;padding-top:14px;gap:8px;'>
                <span style='color:#f7931a;font-weight:700;font-size:13px;'>₿ BTC/USDT</span>
                <span style='color:{hcl};font-size:1.3rem;font-weight:900;'>${hp:,.2f}</span>
                <span style='color:{hcl};font-size:12px;font-weight:600;'>{harr} {abs(hpc):.2f}%</span>
            </div>""", unsafe_allow_html=True)
    with hc3:
        st.markdown(
            f"<div style='text-align:right;font-size:11px;color:#848e9c;padding-top:22px;'>🕐 {datetime.now().strftime('%H:%M:%S IST')}</div>",
            unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

render_header()

# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION — st.tabs() — IMMUNE to st_autorefresh resets
# ─────────────────────────────────────────────────────────────────────────────
tab_portfolio, tab_terminal, tab_risk, tab_wallet = st.tabs([
    "💼  Portfolio & Executions",
    "📈  Trading Terminal",
    "🎛️  Risk & Strategies",
    "🏦  Wallet",
])

# ─────────────────────────────────────────────────────────────────────────────
# Global Logs & Notifications (shared across all tabs)
# ─────────────────────────────────────────────────────────────────────────────
@st.fragment(run_every=3)
def render_global_logs():
    local_hist = [t for t in st.session_state.trade_hist if t["Strategy"] == "Manual Trade"][:5]
    if local_hist:
        with st.expander("📖 Your Local Execution Logs (Manual)", expanded=True):
            thtm = "<div style='font-family:monospace; font-size:12px;'>"
            thtm += "<div style='display:flex; color:#848e9c; margin-bottom:6px; padding-bottom:6px; border-bottom:1px solid #1f2933; font-weight:600;'>"
            thtm += "<span style='width:60px'>Action</span><span style='width:60px'>Asset</span><span style='width:100px'>Price</span><span style='width:80px'>Qty</span><span style='width:100px;text-align:right'>Net PnL</span><span style='flex-grow:1;text-align:right;color:#5a6370;font-size:11px;'>Time</span></div>"
            for t in local_hist:
                act_col = "#0ecb81" if t['Direction']=='BUY' else "#f6465d"
                pnl = t.get('P&L', 0)
                pnl_str = "—" if t['Direction'] == 'BUY' else (f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}")
                pnl_col = "#0ecb81" if pnl > 0 else ("#f6465d" if pnl < 0 else "#5a6370")
                if t['Direction'] == 'BUY': pnl_col = "#5a6370"
                price = t.get('Price', 0)
                qty = t.get('Qty', 0)
                
                thtm += f"<div style='display:flex; color:#e0e0e0; padding:6px 0; border-bottom:1px solid #1a1f26; align-items:center;'>"
                thtm += f"<span style='width:60px; color:{act_col}; font-weight:800'>{t['Direction']}</span>"
                thtm += f"<span style='width:60px; color:#f7931a; font-weight:600'>{t['Asset']}</span>"
                thtm += f"<span style='width:100px;'>${price:,.4f}</span>"
                thtm += f"<span style='width:80px;'>{qty:.4f}</span>"
                thtm += f"<span style='width:100px; text-align:right; color:{pnl_col}; font-weight:700;'>{pnl_str}</span>"
                thtm += f"<span style='flex-grow:1; text-align:right; color:#5a6370; font-size:11px;'>{t['Time']}</span>"
                thtm += "</div>"
            thtm += "</div>"
            st.markdown(thtm, unsafe_allow_html=True)
            
    with st.expander("🔔 Active Engine Notifications", expanded=False):
        for n in st.session_state.notifs:
            st.markdown(
                f"<div style='font-size:.85rem;background:#161a1e;padding:10px;border-radius:4px;"
                f"margin-bottom:6px;border-left:2px solid #0ecb81;color:#e0e0e0;'>{n}</div>",
                unsafe_allow_html=True)

render_global_logs()
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Portfolio & Executions
# ═══════════════════════════════════════════════════════════════════════════════
with tab_portfolio:
    @st.fragment(run_every=3)
    def render_portfolio():
        st.markdown("<h1>💼 Investor Portfolio</h1>", unsafe_allow_html=True)
        st.caption("Real-time portfolio tracking and automated trading visibility.")

        # P&L helpers
        total_upnl = 0
        for pos in st.session_state.positions:
            cur = st.session_state.prices[pos["asset"]]
            pnl = (cur-pos["entry"])*pos["size"] if pos["direction"]=="LONG" else (pos["entry"]-cur)*pos["size"]
            total_upnl += pnl
        total_rpnl  = sum(t["P&L"] for t in st.session_state.trade_hist)
        total_equity = st.session_state.balance + total_rpnl + total_upnl

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Equity",          f"${total_equity:,.2f}")
        c2.metric("Invested Capital",       f"${st.session_state.invested:,.2f}")
        c3.metric("Unrealized P&L",
                  f"${total_upnl:+,.2f}",
                  f"{(total_upnl/st.session_state.invested)*100:+.2f}%",
                  delta_color="normal" if total_upnl>=0 else "inverse")
        c4.metric("Realized P&L (All Time)",
                  f"${total_rpnl:+,.2f}",
                  delta_color="normal" if total_rpnl>=0 else "inverse")

        st.markdown("---")
        col1, col2 = st.columns([2,1])

        with col1:
            st.markdown("<div class='card'><div class='card-title'>🔴 Live Open Positions & AI Stop-Loss Tracking</div>", unsafe_allow_html=True)
            rows = []
            for pos in st.session_state.positions:
                cur = st.session_state.prices[pos["asset"]]
                pnl = (cur-pos["entry"])*pos["size"] if pos["direction"]=="LONG" else (pos["entry"]-cur)*pos["size"]
                rows.append({
                    "Asset":           f"{pos['direction']} {pos['asset']}",
                    "Strategy":        pos["strategy"],
                    "Entry Price":     f"${pos['entry']:,.2f}",
                    "Live Price":      f"${cur:,.2f}",
                    "Unrealized P&L":  f"{'🟢 +' if pnl>0 else '🔴 -'}${abs(pnl):,.2f}",
                    "Stop-Loss":       f"${pos['sl_price']:,.2f} ({pos['sl_type']})",
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No open positions — strategy engine scanning markets…")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card'><div class='card-title'>🥧 Portfolio Allocation</div>", unsafe_allow_html=True)
            fig = go.Figure(data=[go.Pie(
                labels=["Stablecoins","BTC","ETH","Altcoins"],
                values=[st.session_state.balance-st.session_state.invested,
                        st.session_state.invested*.5,
                        st.session_state.invested*.3,
                        st.session_state.invested*.2],
                hole=.5, textinfo="percent",
                marker=dict(colors=["#2b3139","#f7931a","#627eea","#00d4ff"]),
            )])
            fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)",
                              font_color="#e0e0e0", showlegend=True,
                              legend=dict(yanchor="bottom",y=-0.28,xanchor="center",x=0.5))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'><div class='card-title'>📜 Engine Execution History</div>", unsafe_allow_html=True)
        hist = []
        for t in st.session_state.trade_hist:
            hist.append({
                "Execution Time":  t["Time"],
                "Asset":           t["Asset"],
                "Direction":       t["Direction"],
                "Strategy":        t["Strategy"],
                "Realized P&L":    f"{'🟢 +' if t['P&L']>0 else '🔴 -'}${abs(t['P&L']):,.2f}",
            })
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    render_portfolio()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Trading Terminal (LIVE BINANCE)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_terminal:
    st.markdown("""
        <style>
        div[data-testid="stRadio"] > div {background: #161a1e; padding: 6px 16px; border-radius: 8px; border: 1px solid #2b3139;}
        </style>
    """, unsafe_allow_html=True)
    st.session_state.active_asset = st.radio(
        "⚡ Select Trade Asset:", ["BTC", "ETH", "BNB", "XRP", "SOL"],
        horizontal=True, index=["BTC", "ETH", "BNB", "XRP", "SOL"].index(st.session_state.get("active_asset", "BTC"))
    )
    
    @st.fragment(run_every=2)
    def render_ticker_strip():
        sym = st.session_state.active_asset + "USDT"
        ticker = api_ticker(sym)
        if not ticker: return
        lp = float(ticker.get("lastPrice", 0))
        pc = float(ticker.get("priceChangePercent", 0))
        pc_col = "#0ecb81" if pc >= 0 else "#f6465d"
        pc_arr = "▲" if pc >= 0 else "▼"
        pc_sign = "+" if pc >= 0 else ""
        prev = st.session_state.get("prev_term_"+sym, lp)
        flash = ("flash-up" if lp > prev else "flash-down") if prev and prev != lp else ""
        st.session_state["prev_term_"+sym] = lp
        st.markdown(f"""
        <div class='ticker-strip'>
            <div style='margin-right:24px;'>
                <div style='font-size:1rem;font-weight:800;color:#fff;'>{st.session_state.active_asset}<span style='color:#848e9c;'>/USDT</span></div>
                <div style='font-size:.7rem;color:#f7931a;'>Binance Spot · Live</div>
            </div>
            <div class='sbox'>
                <span class='{flash}' style='color:{pc_col};font-size:1.7rem;font-weight:900;letter-spacing:-.02em;'>${lp:,.4f}</span>
                <span class='slbl'>≈ ${lp:,.4f} USD</span>
            </div>
            <span class='tick-sep'>|</span>
            <div class='sbox'><span class='slbl'>24h Change</span>
                <span style='color:{pc_col};font-weight:700;'>{pc_arr} {pc_sign}{pc:.2f}%</span></div>
            <span class='tick-sep'>|</span>
            <div class='sbox'><span class='slbl'>24h High</span><span class='sval'>${float(ticker.get('highPrice',0)):,.4f}</span></div>
            <span class='tick-sep'>|</span>
            <div class='sbox'><span class='slbl'>24h Low</span><span class='sval'>${float(ticker.get('lowPrice',0)):,.4f}</span></div>
            <span class='tick-sep'>|</span>
            <div class='sbox'><span class='slbl'>24h Vol (USDT)</span><span class='sval'>${float(ticker.get('quoteVolume',0))/1e6:.2f}M</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    render_ticker_strip()
    col_ob, col_chart, col_tr = st.columns([1.1, 2.3, 1.1])

    with col_ob:
        @st.fragment(run_every=2)
        def render_ob():
            sym = st.session_state.active_asset + "USDT"
            ticker = api_ticker(sym)
            depth = api_depth(sym, 14)
            if not ticker or not depth: return
            lp = float(ticker.get("lastPrice", 0))
            pc_col = "#0ecb81" if float(ticker.get("priceChangePercent", 0)) >= 0 else "#f6465d"
            st.markdown("<div class='card-title' style='font-size:13px;margin-bottom:8px;'>📖 Order Book</div>", unsafe_allow_html=True)
            asks_raw, bids_raw = depth.get("asks", []), depth.get("bids", [])
            all_sz = [float(q) for _,q in asks_raw+bids_raw]
            max_sz = max(all_sz) if all_sz else 1

            ask_html = ""
            cum = 0.0
            for p,q in reversed(asks_raw):
                cum += float(q)
                ask_html += f"<div class='ob-row' style='position:relative;'><div class='ob-bar ob-ask-bar' style='width:{float(q)/max_sz*100:.1f}%;'></div><span class='ob-price-ask'>{float(p):,.4f}</span><span class='ob-qty'>{float(q):.4f}</span><span class='ob-total'>{cum:.3f}</span></div>"

            sp = float(asks_raw[0][0])-float(bids_raw[0][0]) if asks_raw and bids_raw else 0
            mid = f"<div style='display:flex;justify-content:space-between;align-items:center;margin:4px 0;background:#1f2933;border-radius:4px;padding:3px 8px;'><span style='color:#848e9c;font-size:10px;'>Spread</span><span style='color:{pc_col};font-size:14px;font-weight:900;'>${lp:,.4f}</span><span style='color:#848e9c;font-size:10px;'>{sp:.4f}</span></div>"

            bid_html = ""
            cum = 0.0
            for p,q in bids_raw:
                cum += float(q)
                bid_html += f"<div class='ob-row' style='position:relative;'><div class='ob-bar ob-bid-bar' style='width:{float(q)/max_sz*100:.1f}%;'></div><span class='ob-price-bid'>{float(p):,.4f}</span><span class='ob-qty'>{float(q):.4f}</span><span class='ob-total'>{cum:.3f}</span></div>"

            st.markdown(f"<div style='font-family:monospace;'><div style='display:flex;justify-content:space-between;color:#5a6370;font-size:10px;margin-bottom:4px;padding:0 4px;'><span style='width:90px'>Price(USDT)</span><span style='width:72px;text-align:right'>Qty</span><span style='width:68px;text-align:right'>Total</span></div>{ask_html}{mid}{bid_html}</div>", unsafe_allow_html=True)
        render_ob()

    with col_chart:
        @st.fragment(run_every=60)
        def render_chart():
            sym = st.session_state.active_asset + "USDT"
            klines = api_klines(sym, "5m", 80)
            if not klines: return
            st.markdown(f"<div class='card-title' style='font-size:13px;margin-bottom:8px;'>📊 {st.session_state.active_asset}/USDT — 5m Live Candlestick</div>", unsafe_allow_html=True)
            df = pd.DataFrame(klines, columns=["ot","o","h","l","c","v","ct","qav","nt","tbbav","tbqav","ig"])
            df["ot"] = pd.to_datetime(df["ot"], unit="ms")
            for col in ["o","h","l","c","v"]: df[col] = df[col].astype(float)
            vcols = ["#0ecb81" if c>=o else "#f6465d" for o,c in zip(df["o"],df["c"])]
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df["ot"], open=df["o"], high=df["h"], low=df["l"], close=df["c"], name="Price", increasing=dict(line=dict(color="#0ecb81",width=1), fillcolor="#0ecb81"), decreasing=dict(line=dict(color="#f6465d",width=1), fillcolor="#f6465d")))
            fig.add_trace(go.Bar(x=df["ot"], y=df["v"], name="Vol", marker_color=vcols, opacity=0.35, yaxis="y2"))
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#848e9c",size=11), xaxis_rangeslider_visible=False, xaxis=dict(gridcolor="#1a1f26",showgrid=True,zeroline=False), yaxis=dict(gridcolor="#1a1f26",showgrid=True,side="right",zeroline=False), yaxis2=dict(overlaying="y",side="left",showgrid=False,showticklabels=False, range=[0, df["v"].max()*5]), legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1, font=dict(size=10),bgcolor="rgba(0,0,0,0)"), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        render_chart()

        @st.fragment(run_every=3)
        def render_form():
            a = st.session_state.active_asset
            sym = a + "USDT"
            ticker = api_ticker(sym)
            depth = api_depth(sym, 5)
            lp = float(ticker.get("lastPrice", 0)) if ticker else 0.0
            
            best_ask = float(depth['asks'][0][0]) if depth and depth.get('asks') else lp
            best_bid = float(depth['bids'][0][0]) if depth and depth.get('bids') else lp

            # Reset auto-sync trackers when switching coins
            if st.session_state.get("form_asset") != a:
                st.session_state.form_asset = a
                st.session_state.bp = best_ask
                st.session_state.auto_bp = best_ask
                st.session_state.sp2 = best_bid
                st.session_state.auto_sp2 = best_bid

            # Initialize if empty
            if "auto_bp" not in st.session_state: st.session_state.auto_bp = best_ask
            if "auto_sp2" not in st.session_state: st.session_state.auto_sp2 = best_bid
            if "bp" not in st.session_state: st.session_state.bp = best_ask
            if "sp2" not in st.session_state: st.session_state.sp2 = best_bid

            # Auto-sync bounds if user has not overridden them manually
            if st.session_state.bp == st.session_state.auto_bp:
                st.session_state.bp = best_ask
                st.session_state.auto_bp = best_ask
            if st.session_state.sp2 == st.session_state.auto_sp2:
                st.session_state.sp2 = best_bid
                st.session_state.auto_sp2 = best_bid

            def exec_buy():
                price = st.session_state.get("bp", best_ask)
                qty = st.session_state.get("ba", 0.01 if a in ["BTC", "ETH"] else 1.0)
                cost = price * qty
                if (st.session_state.balance - st.session_state.invested) >= cost:
                    st.session_state.balance -= cost
                    old_qty = st.session_state.holdings[a]
                    new_qty = old_qty + qty
                    if new_qty > 0:
                        st.session_state.avg_entry[a] = ((old_qty * st.session_state.avg_entry[a]) + cost) / new_qty
                    st.session_state.holdings[a] += qty
                    st.session_state.trade_hist.insert(0, {"Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Asset": a, "Strategy": "Manual Trade", "Direction": "BUY", "P&L": 0.0, "Price": price, "Qty": qty})
                    st.session_state.notifs.insert(0, f"✅ Executed Manual BUY of {qty:.4f} {a} at ${price:,.4f}")
                    # Re-sync to live price tracker
                    st.session_state.bp = best_ask
                    st.session_state.auto_bp = best_ask

            def exec_sell():
                price = st.session_state.get("sp2", best_bid)
                qty = st.session_state.get("sa", 0.01 if a in ["BTC", "ETH"] else 1.0)
                rev = price * qty
                if st.session_state.holdings[a] >= qty:
                    pnl = (price - st.session_state.avg_entry[a]) * qty
                    st.session_state.holdings[a] -= qty
                    st.session_state.balance += rev
                    st.session_state.trade_hist.insert(0, {"Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Asset": a, "Strategy": "Manual Trade", "Direction": "SELL", "P&L": pnl, "Price": price, "Qty": qty})
                    st.session_state.notifs.insert(0, f"✅ Executed Manual SELL of {qty:.4f} {a} at ${price:,.4f}")
                    # Re-sync to live price tracker
                    st.session_state.sp2 = best_bid
                    st.session_state.auto_sp2 = best_bid

            st.markdown("<div class='card-title' style='font-size:13px;margin-top:8px;margin-bottom:8px;'>⚡ Spot Trading (Simulated)</div>", unsafe_allow_html=True)
            oc1, oc2 = st.columns(2)
            
            with oc1:
                st.markdown(f"<div style='color:#f7931a;font-size:12px;font-weight:600;margin-bottom:4px;'>BUY {a} &nbsp;|&nbsp; Avbl: {st.session_state.balance - st.session_state.invested:,.2f} USDT</div>", unsafe_allow_html=True)
                st.number_input("Price (USDT)", step=0.1, format="%.4f", key="bp", min_value=0.0)
                st.number_input(f"Amount ({a})", value=0.01 if a in ["BTC", "ETH"] else 1.0, step=0.001 if a in ["BTC", "ETH"] else 1.0, format="%.4f", key="ba", min_value=0.0)
                st.button(f"▲ Buy / Long {a}", key="b_btn", use_container_width=True, type="primary", on_click=exec_buy)

            with oc2:
                hld = st.session_state.holdings.get(a, 0.0)
                current_p = st.session_state.get("sp2", best_bid)
                current_q = st.session_state.get("sa", 0.01 if a in ["BTC", "ETH"] else 1.0)
                unr_pnl = 0.0
                if hld > 0:
                    unr_pnl = (current_p - st.session_state.avg_entry[a]) * current_q
                
                pnl_color = "#0ecb81" if unr_pnl > 0 else ("#f6465d" if unr_pnl < 0 else "#848e9c")
                pnl_str = f" <span style='color:#848e9c;font-weight:500'>| Avg: ${st.session_state.avg_entry[a]:,.1f} | Unr. PnL: <span style='color:{pnl_color}'>${unr_pnl:+,.1f}</span></span>" if hld > 0 else ""
                
                st.markdown(f"<div style='color:#f7931a;font-size:12px;font-weight:600;margin-bottom:4px;white-space:nowrap;'>SELL {a} &nbsp;|&nbsp; Avbl: {hld:.4f} {a}{pnl_str}</div>", unsafe_allow_html=True)
                
                st.number_input("Price (USDT)", step=0.1, format="%.4f", key="sp2", min_value=0.0)
                st.number_input(f"Amount ({a})", value=0.01 if a in ["BTC", "ETH"] else 1.0, step=0.001 if a in ["BTC", "ETH"] else 1.0, format="%.4f", key="sa", min_value=0.0)
                st.button(f"▼ Sell / Short {a}", key="s_btn", use_container_width=True, type="primary", on_click=exec_sell)
                        
        render_form()
        # Form fragment complete

    with col_tr:
        @st.fragment(run_every=2)
        def render_trades_and_ai():
            sym = st.session_state.active_asset + "USDT"
            
            # --- AI Signal Engine Logic ---
            depth = api_depth(sym, 14)
            klines = api_klines(sym, "5m", 80)
            signal, sig_color, conf, reasons = "NEUTRAL", "#848e9c", 50, []
            
            if klines and len(klines) > 20 and depth:
                closes = [float(k[4]) for k in klines]
                ema9 = pd.Series(closes).ewm(span=9, adjust=False).mean().iloc[-1]
                ema21 = pd.Series(closes).ewm(span=21, adjust=False).mean().iloc[-1]
                deltas = np.diff(closes[-15:])
                gains = deltas[deltas > 0].sum()
                losses = -deltas[deltas < 0].sum()
                rs = 0 if losses == 0 else gains/losses
                rsi = 100 - (100 / (1 + rs))

                asks_raw, bids_raw = depth.get("asks", []), depth.get("bids", [])
                bid_vol = sum(float(q) for _,q in bids_raw)
                ask_vol = sum(float(q) for _,q in asks_raw)
                tot_vol = bid_vol + ask_vol or 1
                bid_pct = bid_vol / tot_vol
                
                scores = 0
                if ema9 > ema21: scores += 30; reasons.append("EMA 9/21 Bullish Cross")
                else: scores -= 30; reasons.append("EMA 9/21 Bearish Cross")

                if rsi < 30: scores += 40; reasons.append(f"RSI Oversold ({rsi:.1f})")
                elif rsi > 70: scores -= 40; reasons.append(f"RSI Overbought ({rsi:.1f})")
                else: reasons.append(f"RSI Neutral ({rsi:.1f})")

                if bid_pct > 0.6: scores += 30; reasons.append("Heavy Buy Wall")
                elif bid_pct < 0.4: scores -= 30; reasons.append("Heavy Sell Wall")

                conf = min(100, max(0, 50 + scores))
                if conf >= 65: signal, sig_color = "STRONG BUY", "#0ecb81"
                elif conf <= 35: signal, sig_color = "STRONG SELL", "#f6465d"
                elif conf >= 55: signal, sig_color = "BUY", "#0ecb81"
                elif conf <= 45: signal, sig_color = "SELL", "#f6465d"

            st.markdown(f"""
            <div style='background:#1f2933; border:1px solid #2b3139; border-radius:6px; padding:6px 12px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                <span style='color:#848e9c; font-size:11px; font-weight:600;'>AI NUDGE:</span>
                <span style='color:{sig_color}; font-weight:900; font-size:14px; letter-spacing:1px;'>{signal}</span>
                <span style='color:#fff; font-size:12px; font-weight:700;'>{conf}% Conf</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='card-title' style='font-size:13px;margin-bottom:8px;'>🧠 AI Engine Reasoning</div>", unsafe_allow_html=True)
            reason_html = "".join([f"<div style='font-size:11px; color:#e0e0e0; margin-bottom:4px; padding-left:8px; border-left:2px solid {sig_color};'>{r}</div>" for r in reasons])
            st.markdown(f"<div style='background:#161a1e; border:1px solid #2b3139; border-radius:6px; padding:10px; margin-bottom:20px;'>{reason_html}</div>", unsafe_allow_html=True)


            trades = api_trades(sym, 20)
            if not trades: return
            st.markdown("<div class='card-title' style='font-size:13px;margin-bottom:8px;'>⚡ Live Binance Chain Stream</div>", unsafe_allow_html=True)
            tr_rows = ""
            for t in trades:
                tcl = "#f6465d" if t.get("isBuyerMaker") else "#0ecb81"
                tr_rows += f"<div class='trade-row'><span style='color:{tcl};'>{float(t['price']):,.4f}</span><span style='color:#848e9c;'>{float(t['qty']):.4f}</span><span style='color:#5a6370;'>{pd.to_datetime(t['time'], unit='ms').strftime('%H:%M:%S')}</span></div>"
            st.markdown(f"<div style='font-family:monospace;'><div style='display:flex;justify-content:space-between;color:#5a6370;font-size:10px;margin-bottom:4px;'><span>Price(USDT)</span><span>Qty</span><span>Time</span></div>{tr_rows}</div>", unsafe_allow_html=True)
        render_trades_and_ai()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Risk & Strategies
# ═══════════════════════════════════════════════════════════════════════════════
with tab_risk:
    st.markdown("<h1>🎛️ Algorithmic Control Center</h1>", unsafe_allow_html=True)
    st.caption("Manage investor risk tolerance and view active strategy allocations.")

    r1, r2 = st.columns([1,2])
    with r1:
        st.markdown("<div class='card'><div class='card-title'>🛡️ Investor Risk Profile</div>", unsafe_allow_html=True)
        risk = st.radio("Profile", ["Moderate (Capital Preservation)","Balanced (Growth + Yield)","Aggressive (Max Alpha)"],
                        index=1, key="risk_radio")
        st.markdown("### Impact Matrix:")
        if "Moderate" in risk:
            st.markdown("- **Position Sizing:** max 2%\n- **Stop-Loss:** Fixed 2%\n- **Focus:** Mean Reversion, Arb\n- **Leverage:** 1x (Spot)")
        elif "Balanced" in risk:
            st.markdown("- **Position Sizing:** max 5%\n- **Stop-Loss:** ATR Trailing\n- **Focus:** All strategies\n- **Leverage:** up to 3x")
        else:
            st.markdown("- **Position Sizing:** max 10%\n- **Stop-Loss:** Volume-based\n- **Focus:** Momentum, Trend\n- **Leverage:** up to 10x")
        st.markdown("</div>", unsafe_allow_html=True)

    with r2:
        st.markdown("<div class='card'><div class='card-title'>⚙️ 5 Core Strategies — Active</div>", unsafe_allow_html=True)
        st.markdown("""
        1. <span class='badge-strategy'>Trend Following</span> — EMA 9/21 crossovers on 1H/4H — captures multi-day swings.
        2. <span class='badge-strategy'>Mean Reversion</span> — RSI extremes (>80 / <20) fade strategy.
        3. <span class='badge-strategy'>Momentum Trading</span> — Volume + order-book imbalance breakout engine.
        4. <span class='badge-strategy'>Cross-Exchange Arbitrage</span> — Spread scanner across Binance, Kraken, Coinbase.
        5. <span class='badge-strategy'>DCA</span> — Algorithmic scale-in at key support zones.
        """, unsafe_allow_html=True)
        st.markdown("### System Deployment:")
        st.progress(0.7, text="70% deployed — market is presenting clear alpha opportunities.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Live strategy performance metrics
    st.markdown("<div class='card'><div class='card-title'>📊 Strategy Performance Summary (Simulated)</div>", unsafe_allow_html=True)
    perf_data = [
        {"Strategy":"Trend Following",       "Trades":47, "Win Rate":"68%","Avg P&L":"$1,240","Total P&L":"$58,280"},
        {"Strategy":"Mean Reversion",         "Trades":63, "Win Rate":"72%","Avg P&L":"$680", "Total P&L":"$42,840"},
        {"Strategy":"Momentum Trading",       "Trades":29, "Win Rate":"55%","Avg P&L":"$2,100","Total P&L":"$60,900"},
        {"Strategy":"Cross-Exchange Arb",     "Trades":112,"Win Rate":"91%","Avg P&L":"$140", "Total P&L":"$15,680"},
        {"Strategy":"DCA",                    "Trades":18, "Win Rate":"83%","Avg P&L":"$3,400","Total P&L":"$61,200"},
    ]
    st.dataframe(pd.DataFrame(perf_data), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Wallet
# ═══════════════════════════════════════════════════════════════════════════════
with tab_wallet:
    st.markdown("<h1>🏦 Investor Wallet & Ledger</h1>", unsafe_allow_html=True)

    wc1,wc2,wc3 = st.columns(3)
    wc1.metric("Available USDT",      f"${st.session_state.balance - st.session_state.invested:,.2f}")
    wc2.metric("Total Deposits",      "$2,500,000.00")
    wc3.metric("Pending Withdrawals", "$0.00")

    st.markdown("<div class='card'><div class='card-title'>💳 Transaction History</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(st.session_state.wallet_history), use_container_width=True, hide_index=True)

    st.markdown("### Actions")
    wa1, wa2, _ = st.columns([1,1,3])
    with wa1:
        if st.button("💰 Simulate Deposit (+$100K)", type="primary", key="dep_btn"):
            st.session_state.balance += 100_000
            st.session_state.wallet_history.insert(0,{
                "Date":datetime.now().strftime("%Y-%m-%d"),
                "Type":"Deposit","Amount":"$100,000","Status":"Completed"
            })
            st.rerun()
    with wa2:
        if st.button("📤 Request Withdrawal", key="wdr_btn"):
            st.info("Withdrawal request submitted for review.")
    st.markdown("</div>", unsafe_allow_html=True)
