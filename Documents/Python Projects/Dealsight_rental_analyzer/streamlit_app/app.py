"""
DealSight — Rental Property Deal Analyzer
Slick professional UI with Google Maps integration
Run: streamlit run streamlit_app/app.py  (from project root)
"""

import sys, os, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import asdict
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from python_core.calculations import PropertyInputs, DealAnalyzer, grade_deal, amortization_schedule
from python_core.data_sources import RentCastClient, FREDClient
from python_core.listings import ListingsFetcher, DEMO_LISTINGS

import braintrust
braintrust.init_logger(project="DealSight")
braintrust.auto_instrument()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)
    
def n(val: int | float | None, default: float = 0.0) -> float:
    """Coerce st.number_input output to float, never None."""
    return float(val) if val is not None else default

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DealSight – Deal Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS — Premium Fintech Real Estate theme
# ─────────────────────────────────────────────
def inject_css() -> None:
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

    /* ── CSS Variables ───────────────────────── */
    :root {
        --bg-deep: #050511;
        --bg-card: #0b0b1e;
        --bg-surface: #10102a;
        --bg-sidebar: #06060f;
        --accent-blue: #4f72ff;
        --accent-blue-dim: rgba(79,114,255,0.18);
        --accent-blue-glow: rgba(79,114,255,0.28);
        --accent-gold: #d4a843;
        --accent-gold-dim: rgba(212,168,67,0.15);
        --accent-purple: #8b5cf6;
        --text-primary: #e8e6f4;
        --text-sec: rgba(205,200,230,0.58);
        --text-muted: rgba(205,200,230,0.3);
        --green: #34d399;
        --red: #f87171;
        --border: rgba(255,255,255,0.07);
    }

    /* ── Hide default Streamlit chrome ───────── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    section[data-testid="stSidebar"] > div { padding-top: 0 !important; }

    /* ── App background with subtle gradient mesh ── */
    .stApp { background: var(--bg-deep) !important; }

    /* ── Sidebar ─────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text-sec) !important; }
    [data-testid="stSidebar"] .stNumberInput input,
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox select {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 13px !important;
    }
    [data-testid="stSidebar"] .stNumberInput input:focus,
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 2px var(--accent-blue-dim) !important;
    }
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
    }
    [data-testid="stSidebar"] .stSlider [data-baseweb="track-background"] div {
        background: rgba(79,114,255,0.15) !important;
    }
    [data-testid="stSidebar"] .stSlider [data-baseweb="track-foreground"] div {
        background: var(--accent-blue) !important;
    }

    /* ── Main area ───────────────────────────── */
    .main-wrapper { padding: 0; min-height: 100vh; }

    /* ── Top bar ─────────────────────────────── */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 36px;
        height: 62px;
        background: rgba(5,5,17,0.95);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        position: sticky; top: 0; z-index: 100;
        position: relative;
}
    /* Gradient accent line at bottom of topbar */
    .topbar::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(79,114,255,0.6) 30%, rgba(212,168,67,0.5) 70%, transparent 100%);
    }
    .topbar-logo {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.25rem; font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #ffffff 0%, var(--accent-gold) 120%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        display: flex; align-items: center; gap: 10px;
    }
    .topbar-logo .logo-box {
        width: 30px; height: 30px;
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 15px;
        box-shadow: 0 0 18px rgba(79,114,255,0.4);
        -webkit-text-fill-color: initial;
        color: white; flex-shrink: 0;
    }
    .topbar-address {
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.05em;
        padding: 6px 16px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 100px;
        max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        transition: border-color .2s;
    }
    .topbar-status {
        display: flex; align-items: center; gap: 8px;
        font-size: 11px; color: var(--text-muted);
        font-family: 'Space Mono', monospace;
    }
    .status-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 10px rgba(52,211,153,0.6);
        animation: pulse-green 2s infinite;
    }
    @keyframes pulse-green {
        0%,100% { opacity:1; box-shadow: 0 0 10px rgba(52,211,153,0.6); }
        50%      { opacity:0.55; box-shadow: 0 0 4px rgba(52,211,153,0.2); }
    }

    /* ── Section headers ─────────────────────── */
    .section-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.75rem; font-weight: 600;
        color: var(--text-primary);
        padding: 20px 0 12px;
        display: flex; align-items: center; gap: 10px;
        text-transform: uppercase; letter-spacing: 0.1em;
    }
    .section-title::after {
        content: ''; flex: 1; height: 1px;
        background: linear-gradient(90deg, rgba(255,255,255,0.08), transparent);
    }

    /* ── Property detail pills ───────────────── */
    .detail-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 16px; }
    .detail-pill {
        background: rgba(255,255,255,0.03);
        border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px;
        transition: border-color .2s, background .2s;
    }
    .detail-pill:hover { background: rgba(79,114,255,0.05); border-color: rgba(79,114,255,0.2); }
    .detail-pill .dp-label {
        font-size: 9px; font-family: 'Space Mono', monospace;
        color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px;
    }
    .detail-pill .dp-value { font-family: 'Space Mono', monospace; font-size: 13px; font-weight: 500; color: var(--text-primary); }

    /* ── Expense rows ────────────────────────── */
    .expense-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px;
    }
    .expense-row:last-child { border-bottom: none; }
    .expense-row .er-label { color: var(--text-sec); font-family: 'Plus Jakarta Sans', sans-serif; }
    .expense-row .er-value { font-family: 'Space Mono', monospace; color: var(--red); font-size: 12.5px; }
    .expense-row .er-value.positive { color: var(--green); }
    .expense-row .er-value.gold     { color: var(--accent-gold); }
    .expense-row .er-value.neutral  { color: var(--text-primary); }

    /* ── Stat rows ───────────────────────────── */
    .stat-row {
        display: flex; justify-content: space-between;
        padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px;
    }
    .stat-row .sr-label { color: var(--text-sec); font-family: 'Plus Jakarta Sans', sans-serif; }
    .stat-row .sr-value { font-family: 'Space Mono', monospace; font-size: 12.5px; color: var(--text-primary); }

    /* ── Tabs ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid var(--border) !important;
        gap: 4px !important; padding: 0 36px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        color: var(--text-sec) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 12px !important; font-weight: 500 !important;
        text-transform: uppercase !important; letter-spacing: 0.06em !important;
        padding: 12px 18px !important;
        transition: all .2s !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background: rgba(79,114,255,0.05) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent-blue) !important;
        border-bottom-color: var(--accent-blue) !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding: 28px 36px !important; background: transparent !important; }

    /* ── Buttons ─────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%) !important;
        color: #ffffff !important; border: none !important; border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important;
        font-size: 13px !important; padding: 10px 24px !important;
        transition: all .2s !important; letter-spacing: 0.02em !important;
        box-shadow: 0 4px 18px rgba(79,114,255,0.32) !important;
    }
    .stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 24px rgba(79,114,255,0.48) !important; }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ── Sidebar section labels ──────────────── */
    .sidebar-section {
        font-size: 9px; font-family: 'Space Mono', monospace;
        text-transform: uppercase; letter-spacing: 0.14em;
        color: rgba(79,114,255,0.65);
        padding: 16px 0 6px;
        border-top: 1px solid rgba(255,255,255,0.05); margin-top: 8px;
    }
    .sidebar-section:first-child { border-top: none; margin-top: 0; }

    /* ── BRRRR steps ─────────────────────────── */
    .brrrr-step {
        display: flex; justify-content: space-between; align-items: center;
        padding: 11px 14px; background: rgba(255,255,255,0.02);
        border-radius: 8px; margin-bottom: 6px;
        border-left: 3px solid rgba(255,255,255,0.07);
        transition: background .15s;
    }
    .brrrr-step:hover { background: rgba(255,255,255,0.04); }
    .brrrr-step.highlight { border-left-color: var(--accent-gold); background: var(--accent-gold-dim); }
    .brrrr-step.positive  { border-left-color: var(--green); background: rgba(52,211,153,0.04); }
    .brrrr-step.negative  { border-left-color: var(--red); background: rgba(248,113,113,0.04); }
    .brrrr-step .bs-label { font-size: 12.5px; color: var(--text-sec); font-family: 'Plus Jakarta Sans', sans-serif; }
    .brrrr-step .bs-val   { font-family: 'Space Mono', monospace; font-size: 13px; color: var(--text-primary); }

    /* ── Comps table ─────────────────────────── */
    .comp-row {
        display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
        padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.04);
        font-size: 12.5px; transition: background .15s;
    }
    .comp-row:hover { background: rgba(79,114,255,0.04); }
    .comp-row.comp-header {
        font-family: 'Space Mono', monospace; font-size: 9px; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--text-muted);
        border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; margin-bottom: 2px;
    }
    .comp-row .cr-addr { color: var(--text-sec); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .comp-row .cr-rent { font-family: 'Space Mono', monospace; color: var(--green); font-weight: 500; }
    .comp-row .cr-stat { font-family: 'Space Mono', monospace; color: var(--text-muted); }

    /* ── Macro ticker ────────────────────────── */
    .macro-ticker {
        display: flex; background: rgba(255,255,255,0.02);
        border: 1px solid var(--border); border-radius: 14px; overflow: hidden;
    }
    .macro-item {
        flex: 1; padding: 18px 14px;
        border-right: 1px solid rgba(255,255,255,0.05); text-align: center;
        transition: background .15s;
    }
    .macro-item:hover { background: rgba(79,114,255,0.04); }
    .macro-item:last-child { border-right: none; }
    .macro-item .mi-label {
        font-size: 9px; font-family: 'Space Mono', monospace; color: var(--text-muted);
        text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;
    }
    .macro-item .mi-val { font-family: 'Space Mono', monospace; font-size: 1.15rem; font-weight: 400; color: var(--text-primary); }
    .macro-item .mi-val.up   { color: var(--green); }
    .macro-item .mi-val.warn { color: #fb923c; }

    /* ── Banners ─────────────────────────────── */
    .info-banner {
        background: rgba(79,114,255,0.06);
        border: 1px solid rgba(79,114,255,0.2); border-radius: 10px; padding: 14px 18px;
        font-size: 13px; color: rgba(180,190,255,0.8); margin: 12px 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .success-banner {
        background: rgba(52,211,153,0.06);
        border: 1px solid rgba(52,211,153,0.2); border-radius: 10px; padding: 14px 18px;
        font-size: 13px; color: rgba(52,211,153,0.85); margin: 12px 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ── Scrollbar ───────────────────────────── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(79,114,255,0.25); border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(79,114,255,0.45); }

    /* ── Plotly charts ───────────────────────── */
    .js-plotly-plot .plotly .modebar { display: none !important; }
    .stPlotlyChart { border-radius: 12px; overflow: hidden; }

    /* ── Grade colors ────────────────────────── */
    .cf-pos { color: var(--green); }
    .cf-neg { color: var(--red); }
    .cf-neu { color: var(--accent-gold); }
    .grade-A { color: var(--green); }
    .grade-B { color: #a3e635; }
    .grade-C { color: #fbbf24; }
    .grade-F { color: var(--red); }
    .grade-bg-A { background: rgba(52,211,153,0.1);  color: var(--green); }
    .grade-bg-B { background: rgba(163,230,53,0.1);  color: #a3e635; }
    .grade-bg-C { background: rgba(251,191,36,0.1);  color: #fbbf24; }
    .grade-bg-F { background: rgba(248,113,113,0.1); color: var(--red); }

    /* ── Listing cards ───────────────────────── */
    .listing-card {
        background: var(--bg-card); border: 1px solid var(--border);
        border-radius: 14px; overflow: hidden;
        transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s; height: 100%;
    }
    .listing-card:hover {
        border-color: rgba(79,114,255,0.35); transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(79,114,255,0.12);
    }
    .listing-card img { width: 100%; height: 200px; object-fit: cover; display: block; background: var(--bg-surface); }
    /* ── Photo carousel reel ── */
    .photo-reel-wrap { position: relative; border-radius: 14px 14px 0 0; overflow: hidden; }
    .photo-reel {
        display: flex; overflow-x: auto; scroll-snap-type: x mandatory;
        scrollbar-width: none; height: 200px;
    }
    .photo-reel::-webkit-scrollbar { display: none; }
    .photo-reel img {
        min-width: 100%; height: 200px; object-fit: cover;
        scroll-snap-align: start; flex-shrink: 0;
        background: var(--bg-surface);
    }
    .photo-count-badge {
        position: absolute; bottom: 8px; right: 8px;
        background: rgba(0,0,0,0.60); backdrop-filter: blur(4px);
        color: rgba(255,255,255,0.82); font-size: 9.5px;
        font-family: 'Space Mono', monospace;
        padding: 2px 8px; border-radius: 100px; pointer-events: none;
    }
    .sale-price-badge {
        color: var(--accent-gold) !important;
    }
    .listing-card-body { padding: 14px 16px 16px; }
    .listing-card-rent {
        font-family: 'Space Mono', monospace; font-size: 1.25rem; font-weight: 700;
        color: var(--accent-blue); margin-bottom: 4px;
    }
    .listing-card-addr {
        font-size: 12.5px; color: var(--text-sec); margin-bottom: 10px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .listing-card-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
    .listing-badge {
        background: var(--accent-blue-dim); border: 1px solid rgba(79,114,255,0.18);
        border-radius: 100px; padding: 3px 10px;
        font-family: 'Space Mono', monospace; font-size: 10px; color: rgba(160,170,255,0.75);
    }
    .listing-card-meta { font-size: 10.5px; color: var(--text-muted); font-family: 'Space Mono', monospace; }
    .listing-card-type {
        display: inline-block; background: var(--accent-gold-dim);
        border: 1px solid rgba(212,168,67,0.22); border-radius: 100px;
        padding: 2px 9px; font-size: 9.5px; color: rgba(212,168,67,0.8);
        text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;
        font-family: 'Space Mono', monospace;
    }
    </style>
    """, unsafe_allow_html=True)
inject_css()
# Plotly theme factory
# ─────────────────────────────────────────────
def apply_theme(fig: go.Figure, height: int = 380, **kwargs) -> go.Figure:
    """Apply consistent dark theme to any Plotly figure."""

    axis_defaults = dict(
        gridcolor = "rgba(255,255,255,0.04)",
        linecolor = "rgba(255,255,255,0.08)",
        zeroline  = False,
    )

    layout: dict = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "#0b0b1e",
        "font":          dict(family="Space Mono, monospace", color="rgba(205,200,230,0.5)", size=11),
        "legend":        dict(orientation="h", y=1.08, font=dict(size=10)),
        "margin":        dict(t=40, b=40, l=12, r=12),
        "height":        height,
        "xaxis":         axis_defaults,
        "yaxis":         axis_defaults,
    }

    layout.update(kwargs)
    return fig
GOLD   = "#d4a843"
GREEN  = "#34d399"
RED    = "#f87171"
BLUE   = "#4f72ff"
PURPLE = "#8b5cf6"
# ─────────────────────────────────────────────
# Session-state defaults (address search writes here)
# ─────────────────────────────────────────────
st.session_state.setdefault("sb_address",  "123 Main St")
st.session_state.setdefault("sb_city_st",  "Phoenix, AZ")
st.session_state.setdefault("sb_zip_code", "85001")

# Apply pending address updates before widgets are instantiated
for _wk, _pk in [("sb_address", "_pending_sb_address"),
                 ("sb_city_st", "_pending_sb_city_st"),
                 ("sb_zip_code", "_pending_sb_zip_code")]:
    if _pk in st.session_state:
        st.session_state[_wk] = st.session_state.pop(_pk)

# ─────────────────────────────────────────────
# Sidebar — Inputs
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 16px;display:flex;align-items:center;gap:10px;
         border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:8px">
        <div style="width:28px;height:28px;border-radius:7px;flex-shrink:0;
             background:linear-gradient(135deg,#4f72ff 0%,#8b5cf6 100%);
             display:flex;align-items:center;justify-content:center;font-size:14px;
             box-shadow:0 0 14px rgba(79,114,255,0.4)">🏠</div>
        <span style="font-family:'Space Grotesk',sans-serif;font-size:13px;font-weight:700;
              letter-spacing:-0.01em;
              background:linear-gradient(135deg,#ffffff,#d4a843);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text">DealSight</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">Property</div>', unsafe_allow_html=True)
    address: str  = st.text_input("Street Address", key="sb_address",  label_visibility="collapsed", placeholder="Street address")
    city_st: str  = st.text_input("City, State",    key="sb_city_st",  label_visibility="collapsed", placeholder="City, State")
    zip_code: str = st.text_input("ZIP",             key="sb_zip_code", label_visibility="collapsed", placeholder="ZIP code")

    st.markdown('<div class="sidebar-section">Purchase</div>', unsafe_allow_html=True)
    purchase_price: int = st.number_input("Purchase Price",  value=350_000, step=5_000, format="%d", label_visibility="collapsed")
    st.caption("Purchase price ($)")
    down_pct: float = st.slider("Down Payment", 5, 50, 20, label_visibility="collapsed") / 100
    st.caption(f"Down payment  {int(down_pct*100)}%  ·  ${purchase_price*down_pct:,.0f}")
    closing_costs: int = st.number_input("Closing Costs",   value=6_000, step=500, format="%d", label_visibility="collapsed")
    st.caption("Closing costs ($)")
    rehab_costs    = st.number_input("Rehab Costs",     value=0,     step=1_000, format="%d", label_visibility="collapsed")
    st.caption("Rehab costs ($)")
    arv            = st.number_input("After Repair Value", value=0, step=5_000, format="%d", label_visibility="collapsed")
    st.caption("ARV for BRRRR ($) — leave 0 to skip")

    st.markdown('<div class="sidebar-section">Financing</div>', unsafe_allow_html=True)
    interest_rate = st.slider("Rate", 3.0, 12.0, 7.0, 0.125, label_visibility="collapsed") / 100
    st.caption(f"Interest rate  {interest_rate*100:.3f}%")
    loan_term     = st.selectbox("Term", [30, 20, 15, 10], label_visibility="collapsed")
    st.caption(f"Loan term  {loan_term} years")
    interest_only = st.checkbox("Interest Only", value=False)

    st.markdown('<div class="sidebar-section">Income</div>', unsafe_allow_html=True)
    monthly_rent = st.number_input("Monthly Rent", value=2_400, step=50, format="%d", label_visibility="collapsed")
    st.caption("Monthly rent ($)")
    other_income = st.number_input("Other Income", value=0, step=25, format="%d", label_visibility="collapsed")
    st.caption("Other monthly income ($)")

    st.markdown('<div class="sidebar-section">Expenses</div>', unsafe_allow_html=True)
    prop_tax_annual  = st.number_input("Property Tax/yr", value=5_000, step=100, format="%d", label_visibility="collapsed")
    st.caption("Annual property tax ($)")
    insurance_annual = st.number_input("Insurance/yr",    value=1_500, step=100, format="%d", label_visibility="collapsed")
    st.caption("Annual insurance ($)")
    hoa_monthly      = st.number_input("HOA/mo",          value=0,     step=25,  format="%d", label_visibility="collapsed")
    st.caption("HOA monthly ($)")
    mgmt_pct         = st.slider("Management",  0, 20, 10, label_visibility="collapsed") / 100
    st.caption(f"Property mgmt  {int(mgmt_pct*100)}%")
    vacancy_rate     = st.slider("Vacancy",     0, 20,  5, label_visibility="collapsed") / 100
    st.caption(f"Vacancy rate  {int(vacancy_rate*100)}%")
    maintenance_pct  = st.slider("Maintenance", 3, 15,  5, label_visibility="collapsed") / 100
    st.caption(f"Maintenance + CapEx  {int(maintenance_pct*100)}%")
    utilities_mo     = st.number_input("Utilities/mo", value=0, step=25, format="%d", label_visibility="collapsed")
    st.caption("Utilities monthly ($)")

    st.markdown('<div class="sidebar-section">STR / Airbnb</div>', unsafe_allow_html=True)
    with st.expander("Configure STR"):
        str_nightly   = st.number_input("Nightly Rate ($)", value=150, step=5)
        str_occ       = st.slider("Occupancy (%)", 30, 100, 65) / 100
        str_clean_fee = st.number_input("Cleaning Fee ($)", value=85, step=5)
        str_avg_stay  = st.number_input("Avg Stay (nights)", value=3, step=1, min_value=1)
        str_platform  = st.slider("Platform Fee (%)", 0.0, 5.0, 3.0, 0.5) / 100

    st.markdown('<div class="sidebar-section">BRRRR Refinance</div>', unsafe_allow_html=True)
    with st.expander("Configure Refi"):
        refi_ltv     = st.slider("Refi LTV (%)", 50, 80, 75) / 100
        refi_rate    = st.slider("Refi Rate (%)", 3.0, 12.0, 7.0, 0.125) / 100
        refi_term    = st.selectbox("Refi Term", [30, 20, 15], key="refi_t")
        refi_closing = st.number_input("Refi Closing ($)", value=3_000, step=500)

# ─────────────────────────────────────────────
# Build Inputs & Run Analysis
# ─────────────────────────────────────────────
inputs = PropertyInputs(
    purchase_price=purchase_price,
    down_payment_pct=down_pct,
    closing_costs=closing_costs,
    rehab_costs=rehab_costs,
    after_repair_value=arv,
    loan_interest_rate=interest_rate,
    loan_term_years=loan_term,
    is_interest_only=interest_only,
    monthly_rent=monthly_rent,
    other_monthly_income=other_income,
    str_nightly_rate=str_nightly,
    str_occupancy_rate=str_occ,
    str_cleaning_fee=str_clean_fee,
    str_avg_stay_nights=str_avg_stay,
    str_platform_fee_pct=str_platform,
    property_tax_annual=prop_tax_annual,
    insurance_annual=insurance_annual,
    hoa_monthly=hoa_monthly,
    property_mgmt_pct=mgmt_pct,
    vacancy_rate=vacancy_rate,
    maintenance_pct=maintenance_pct,
    utilities_monthly=utilities_mo,
    refi_ltv=refi_ltv,
    refi_interest_rate=refi_rate,
    refi_term_years=refi_term,
    refi_closing_costs=refi_closing,
)
analyzer = DealAnalyzer(inputs)
metrics  = analyzer.analyze()
grades   = grade_deal(metrics)
full_address = f"{address}, {city_st} {zip_code}".strip(", ")

# ─────────────────────────────────────────────
# Top Bar
# ─────────────────────────────────────────────
cf_color = "cf-pos" if metrics.monthly_cash_flow > 0 else ("cf-neg" if metrics.monthly_cash_flow < 0 else "cf-neu")
st.markdown(f"""
<div class="topbar">
    <div class="topbar-logo">
        <div class="logo-box" style="width:38px;height:38px;font-size:18px;border-radius:10px;">🏠</div>
        DealSight
    </div>
    <div class="topbar-address" style="color:{'#e8e6f4' if address != '123 Main St' else 'rgba(180,185,255,0.55)'};
         {'font-weight:500;' if address != '123 Main St' else ''}">
        {'🔍 ' if address == '123 Main St' else ''}{full_address if address != "123 Main St" else "Enter an address below →"}
    </div>
    <div class="topbar-status">
        <div class="status-dot"></div>
        Analysis ready
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Address Search Strip
# ─────────────────────────────────────────────
st.markdown("""
<div style="padding:16px 36px 0;background:linear-gradient(180deg,rgba(11,10,30,0.6) 0%,transparent 100%);">
</div>""", unsafe_allow_html=True)

_srch_c, _srch_btn_c = st.columns([7, 1], gap="small")
with _srch_c:
    _search_query = st.text_input(
        "address_search",
        placeholder="🔍  Search any property address  —  e.g. 4521 N Central Ave, Phoenix, AZ 85012",
        label_visibility="collapsed",
        key="addr_search_box",
    )
with _srch_btn_c:
    _search_go = st.button("Analyze →", key="btn_addr_search", use_container_width=True)

if _search_go and _search_query.strip():
    _txt = _search_query.strip()
    _zip_m = re.search(r'\b(\d{5})(?:-\d{4})?\s*$', _txt)
    _pzip  = _zip_m.group(1) if _zip_m else ""
    _no_zip = _txt[:_zip_m.start()].strip(", ") if _zip_m else _txt
    _parts  = _no_zip.rsplit(",", 1)
    _paddr  = _parts[0].strip()
    _pcity  = _parts[1].strip() if len(_parts) == 2 else ""
    st.session_state["_pending_sb_address"]  = _paddr
    st.session_state["_pending_sb_city_st"]  = _pcity
    st.session_state["_pending_sb_zip_code"] = _pzip
    st.rerun()

# ─────────────────────────────────────────────
# Map + Property Info Row
# ─────────────────────────────────────────────
maps_key = get_secret("GOOGLE_MAPS_API_KEY")
encoded_address = urllib.parse.quote(full_address)

st.markdown('<div style="padding: 16px 36px 0;">', unsafe_allow_html=True)

map_col, info_col = st.columns([3, 2], gap="large")

with map_col:
    st.markdown('<div class="section-title">📍 Property Location</div>', unsafe_allow_html=True)

    if maps_key:
        # Google Maps Embed — shows map + street view toggle
        map_html = f"""
        <div style="position:relative;border-radius:12px;overflow:hidden;
             border:1px solid rgba(255,255,255,0.07);height:340px;">
            <div style="position:absolute;top:12px;left:12px;z-index:10;
                 background:rgba(5,5,17,0.88);backdrop-filter:blur(10px);
                 border:1px solid rgba(79,114,255,0.3);border-radius:6px;
                 padding:5px 10px;font-size:10px;font-family:monospace;
                 color:#d4a843;text-transform:uppercase;letter-spacing:0.1em;">
                Google Maps
            </div>
            <iframe
                width="100%" height="340"
                frameborder="0" style="border:0;display:block;"
                referrerpolicy="no-referrer-when-downgrade"
                src="https://www.google.com/maps/embed/v1/place?key={maps_key}&q={encoded_address}&zoom=15&maptype=roadmap"
                allowfullscreen>
            </iframe>
        </div>
        """
        components.html(map_html, height=350)

        # Street View
        with st.expander("🏠 Street View"):
            sv_html = f"""
            <div style="border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);">
                <iframe
                    width="100%" height="260"
                    frameborder="0" style="border:0;display:block;"
                    src="https://www.google.com/maps/embed/v1/streetview?key={maps_key}&location={encoded_address}&heading=210&pitch=10&fov=90"
                    allowfullscreen>
                </iframe>
            </div>
            """
            components.html(sv_html, height=270)
    else:
        # Fallback — OpenStreetMap via iframe (no key needed)
        osm_html = f"""
        <div style="position:relative;border-radius:12px;overflow:hidden;
             border:1px solid rgba(255,255,255,0.07);height:340px;">
            <div style="position:absolute;top:12px;left:12px;z-index:10;
                 background:rgba(5,5,17,0.88);backdrop-filter:blur(10px);
                 border:1px solid rgba(79,114,255,0.3);border-radius:6px;
                 padding:5px 10px;font-size:10px;font-family:monospace;
                 color:#d4a843;text-transform:uppercase;letter-spacing:0.1em;">
                OpenStreetMap · Add GOOGLE_MAPS_API_KEY for Google Maps
            </div>
            <iframe
                width="100%" height="340"
                frameborder="0" scrolling="no"
                marginheight="0" marginwidth="0"
                style="border:0;display:block;filter:invert(0.9) hue-rotate(180deg) saturate(0.7);"
                src="https://www.openstreetmap.org/export/embed.html?bbox=-112.2,33.3,-111.8,33.5&layer=mapnik&marker=33.4,{encoded_address}"
                src="https://maps.google.com/maps?q={encoded_address}&t=&z=15&ie=UTF8&iwloc=&output=embed">
            </iframe>
        </div>
        <div style="font-size:10px;color:rgba(205,200,230,0.28);padding:6px 0;
             font-family:monospace;text-align:center;">
            Add GOOGLE_MAPS_API_KEY to secrets.toml for Google Maps + Street View
        </div>
        """
        # Clean OSM embed
        osm_url = f"https://www.openstreetmap.org/export/embed.html?query={encoded_address}&layer=mapnik"
        osm_clean = f"""
        <div style="border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);height:340px;position:relative;">
            <div style="position:absolute;top:12px;left:12px;z-index:10;
                 background:rgba(5,5,17,0.92);backdrop-filter:blur(10px);
                 border:1px solid rgba(79,114,255,0.3);border-radius:6px;
                 padding:5px 10px;font-size:10px;font-family:monospace;
                 color:#d4a843;text-transform:uppercase;letter-spacing:0.1em;">
                Map Preview
            </div>
            <iframe
                width="100%" height="340" frameborder="0" scrolling="no"
                style="border:0;display:block;filter:invert(0.88) hue-rotate(195deg) saturate(0.6) brightness(0.9);"
                src="https://maps.google.com/maps?q={encoded_address}&t=&z=15&ie=UTF8&iwloc=&output=embed"
                allowfullscreen>
            </iframe>
        </div>
        <div style="text-align:center;padding:6px 0;font-size:10px;
             color:rgba(205,200,230,0.25);font-family:monospace;">
            Add GOOGLE_MAPS_API_KEY to secrets.toml for the full Google Maps + Street View experience
        </div>
        """
        components.html(osm_clean, height=370)

with info_col:
    st.markdown('<div class="section-title">🏡 Deal Summary</div>', unsafe_allow_html=True)

    loan_amount = metrics.loan_amount
    monthly_pmt = metrics.monthly_payment

    st.markdown(f"""
    <div class="detail-grid">
        <div class="detail-pill">
            <div class="dp-label">List Price</div>
            <div class="dp-value">${purchase_price:,.0f}</div>
        </div>
        <div class="detail-pill">
            <div class="dp-label">Down</div>
            <div class="dp-value">${metrics.down_payment:,.0f}</div>
        </div>
        <div class="detail-pill">
            <div class="dp-label">Loan</div>
            <div class="dp-value">${loan_amount:,.0f}</div>
        </div>
        <div class="detail-pill">
            <div class="dp-label">Cash In</div>
            <div class="dp-value">${metrics.total_cash_invested:,.0f}</div>
        </div>
        <div class="detail-pill">
            <div class="dp-label">Mortgage/mo</div>
            <div class="dp-value">${monthly_pmt:,.0f}</div>
        </div>
        <div class="detail-pill">
            <div class="dp-label">Rate</div>
            <div class="dp-value">{interest_rate*100:.3f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key expenses
    bd = metrics.expense_breakdown
    gross = metrics.gross_monthly_income
    net   = metrics.monthly_cash_flow
    noi   = metrics.net_operating_income

    st.markdown(f"""
    <div class="expense-row">
        <span class="er-label">Gross rent / mo</span>
        <span class="er-value positive">${gross:,.0f}</span>
    </div>
    <div class="expense-row">
        <span class="er-label">All expenses / mo</span>
        <span class="er-value">(${metrics.total_monthly_expenses:,.0f})</span>
    </div>
    <div class="expense-row">
        <span class="er-label">Net cash flow / mo</span>
        <span class="er-value {'positive' if net>0 else ''}">${net:+,.0f}</span>
    </div>
    <div class="expense-row">
        <span class="er-label">NOI / year</span>
        <span class="er-value gold">${noi:,.0f}</span>
    </div>
    <div class="expense-row">
        <span class="er-label">Break-even occupancy</span>
        <span class="er-value neutral">{metrics.break_even_occupancy:.1f}%</span>
    </div>
    <div class="expense-row">
        <span class="er-label">Gross Rent Multiplier</span>
        <span class="er-value neutral">{metrics.gross_rent_multiplier:.1f}x</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI Strip
# ─────────────────────────────────────────────
def kpi_card(label: str, value: str, grade: str, desc: str, sub: str = "") -> str:
    grade_colors = {
        "A": ("#34d399", "rgba(52,211,153,0.1)",  "rgba(52,211,153,0.3)"),
        "B": ("#a3e635", "rgba(163,230,53,0.1)",  "rgba(163,230,53,0.3)"),
        "C": ("#fbbf24", "rgba(251,191,36,0.1)",  "rgba(251,191,36,0.3)"),
        "F": ("#f87171", "rgba(248,113,113,0.1)", "rgba(248,113,113,0.3)"),
    }
    val_color, badge_bg, glow = grade_colors.get(grade, ("#d4a843", "rgba(212,168,67,0.1)", "rgba(212,168,67,0.3)"))
    return f"""
    <div style="background:#0b0b1e;padding:24px 20px;position:relative;overflow:hidden;
         border-right:1px solid rgba(255,255,255,0.05);flex:1;transition:background 0.2s;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;
             background:linear-gradient(90deg,transparent,{val_color}50,transparent)"></div>
        <div style="font-size:9px;font-family:'Space Mono',monospace;
             color:rgba(205,200,230,0.35);text-transform:uppercase;
             letter-spacing:0.14em;margin-bottom:12px">{label}</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.8rem;
             font-weight:400;line-height:1;margin-bottom:10px;
             color:{val_color};text-shadow:0 0 24px {glow}">{value}</div>
        <div style="display:inline-flex;align-items:center;gap:5px;
             font-size:10px;font-family:'Space Mono',monospace;
             padding:3px 9px;border-radius:100px;
             background:{badge_bg};color:{val_color};
             border:1px solid {val_color}35">
            {grade} · {desc[:28]}
        </div>
        {"<div style='font-size:10px;color:rgba(205,200,230,0.3);font-family:Space Mono,monospace;margin-top:8px'>" + sub + "</div>" if sub else ""}
    </div>"""

# Build the 5 KPI cards
g = grades  # shorthand
cf_fmt   = f"${metrics.monthly_cash_flow:+,.0f}"
cap_fmt  = f"{metrics.cap_rate*100:.2f}%"
coc_fmt  = f"{metrics.cash_on_cash_return:.1f}%"
dscr_fmt = f"{metrics.dscr:.2f}x"
grm_fmt  = f"{metrics.gross_rent_multiplier:.1f}x"

# Height adjuster — number_input has built-in ↑↓ arrows
_, _kpi_ctl_col = st.columns([8, 1])
with _kpi_ctl_col:
    _kpi_h = st.number_input(
        "H", value=170, min_value=130, max_value=320, step=5,
        key="kpi_strip_h", label_visibility="collapsed",
        help="Adjust KPI strip height (↑↓) if cards overlap the tab bar",
    )

kpi_strip_html = f"""
<div style="display:flex;background:rgba(255,255,255,0.03);
     border-top:1px solid rgba(255,255,255,0.06);
     border-bottom:1px solid rgba(255,255,255,0.06);">
    {kpi_card("Monthly Cash Flow", cf_fmt,   g["cash_flow"][0], g["cash_flow"][1], f"${metrics.annual_cash_flow:,.0f}/yr")}
    {kpi_card("Cap Rate",          cap_fmt,  g["cap_rate"][0],  g["cap_rate"][1],  "NOI / price")}
    {kpi_card("Cash-on-Cash",      coc_fmt,  g["coc"][0],       g["coc"][1],       f"on ${metrics.total_cash_invested:,.0f}")}
    {kpi_card("DSCR",              dscr_fmt, g["dscr"][0],      g["dscr"][1],      "≥1.25 lender pref")}
    {kpi_card("GRM",               grm_fmt,  g["grm"][0],       g["grm"][1],       "lower = better")}
</div>
"""
components.html(kpi_strip_html, height=_kpi_h)

# ─────────────────────────────────────────────
# Main Tabs
# ─────────────────────────────────────────────
tab_cf, tab_brrrr, tab_str, tab_comps, tab_amort, tab_macro, tab_listings = st.tabs([
    "Cash Flow",  "BRRRR",  "STR / Airbnb",
    "Rent Comps", "Amortization", "Market Data", "Local Listings",
])

# ───────────────────────────────
# TAB: Cash Flow
# ───────────────────────────────
with tab_cf:
    col_wf, col_exp = st.columns(2, gap="large")

    with col_wf:
        st.markdown('<div class="section-title">Waterfall</div>', unsafe_allow_html=True)
        bd = metrics.expense_breakdown
        labels   = ["Gross Rent"] + [k.replace("_"," ").title() for k in bd] + ["Net Cash Flow"]
        values   = [metrics.gross_monthly_income] + [-v for v in bd.values()] + [metrics.monthly_cash_flow]
        measures = ["absolute"] + ["relative"] * len(bd) + ["total"]

        fig = go.Figure(go.Waterfall(
            orientation="v", measure=measures, x=labels, y=values,
            text=[f"${abs(v):,.0f}" for v in values], textposition="outside",
            textfont=dict(family="Space Mono, monospace", size=10),
            connector=dict(line=dict(color="rgba(255,255,255,0.08)")),
            decreasing=dict(marker=dict(color=RED,   line=dict(width=0))),
            increasing=dict(marker=dict(color=GREEN, line=dict(width=0))),
            totals=dict(    marker=dict(color=GOLD,  line=dict(width=0))),
        ))
        apply_theme(fig, height=380,
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickangle=-20, tickfont=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True, key="chart_waterfall")
        
    with col_exp:
        st.markdown('<div class="section-title">Expense Breakdown</div>', unsafe_allow_html=True)
        exp_labels = [k.replace("_"," ").title() for k in bd]
        exp_vals   = list(bd.values())
        colors_pie = ["#e86e4a", "#60a5fa", "#a78bfa", "#34d399", "#fb923c", "#f472b6", "#94a3b8"]

        fig2 = go.Figure(go.Pie(
            labels=exp_labels, values=exp_vals, hole=0.58,
            textinfo="percent", textfont=dict(family="Space Mono, monospace", size=10),
            marker=dict(colors=colors_pie[:len(exp_vals)],
                        line=dict(color="#050511", width=2)),
        ))
        fig2.add_annotation(
            text=f"${sum(exp_vals):,.0f}<br><span style='font-size:10px'>per month</span>",
            font=dict(size=15, color="#e8e6f4", family="Space Mono, monospace"),
            showarrow=False,
        )
        apply_theme(fig, height=380,
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickangle=-20, tickfont=dict(size=10)))
        st.plotly_chart(fig2, use_container_width=True, key="chart_expense_donut")

    # Itemized expense table
    st.markdown('<div class="section-title">Itemized Expenses</div>', unsafe_allow_html=True)
    icol1, icol2 = st.columns(2, gap="large")
    items = list(bd.items())
    half  = len(items) // 2

    with icol1:
        for k, v in items[:half+1]:
            label = k.replace("_"," ").title()
            st.markdown(f"""
            <div class="expense-row">
                <span class="er-label">{label}</span>
                <span class="er-value">(${v:,.0f}/mo)</span>
            </div>""", unsafe_allow_html=True)

    with icol2:
        for k, v in items[half+1:]:
            label = k.replace("_"," ").title()
            st.markdown(f"""
            <div class="expense-row">
                <span class="er-label">{label}</span>
                <span class="er-value">(${v:,.0f}/mo)</span>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="expense-row" style="margin-top:8px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.1);">
            <span class="er-label" style="color:#e8e6e0;font-weight:500">Total / month</span>
            <span class="er-value">(${metrics.total_monthly_expenses:,.0f})</span>
        </div>""", unsafe_allow_html=True)

    # 10-Year projection
    st.markdown('<div class="section-title" style="margin-top:28px">10-Year Projection</div>', unsafe_allow_html=True)
    sl1, sl2, sl3 = st.columns(3)
    with sl1:
        rent_growth  = st.slider("Rent growth %/yr",  0.0, 8.0, 2.5, 0.5, key="rg") / 100
    with sl2:
        exp_growth   = st.slider("Expense growth %/yr", 0.0, 6.0, 2.0, 0.5, key="eg") / 100
    with sl3:
        appreciation = st.slider("Appreciation %/yr", 0.0, 8.0, 3.0, 0.5, key="ap") / 100

    years, cfs, vals, equity_l = [], [], [], []
    r_now, e_now, pv = metrics.effective_gross_income, metrics.total_monthly_expenses, purchase_price
    amort_data = amortization_schedule(metrics.loan_amount, interest_rate, loan_term) if metrics.loan_amount > 0 else []

    for yr in range(1, 11):
        r_now *= (1 + rent_growth); e_now *= (1 + exp_growth); pv *= (1 + appreciation)
        cf_yr  = (r_now - e_now) * 12
        idx    = min(yr * 12 - 1, len(amort_data) - 1)
        bal    = amort_data[idx]["balance"] if amort_data else metrics.loan_amount
        eq     = pv - bal
        years.append(yr); cfs.append(round(cf_yr)); vals.append(round(pv)); equity_l.append(round(eq))

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=years, y=cfs, name="Annual CF",
                           marker_color=GOLD, marker_line=dict(width=0), yaxis="y"))
    fig3.add_trace(go.Scatter(x=years, y=equity_l, name="Equity",
                               line=dict(color=GREEN, width=2), mode="lines+markers",
                               marker=dict(size=5), yaxis="y2"))
    fig3.add_trace(go.Scatter(x=years, y=vals, name="Property Value",
                               line=dict(color=BLUE, width=2, dash="dot"), yaxis="y2"))
    apply_theme(fig3, height=360,
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Cash Flow ($)", tickprefix="$"),
    yaxis2=dict(title="Value ($)", overlaying="y", side="right",
                gridcolor="rgba(0,0,0,0)", tickprefix="$",
                tickfont=dict(family="Space Mono, monospace", size=10)),
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Year", dtick=1),
    legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig3, use_container_width=True, key="chart_projection")

# ───────────────────────────────
# TAB: BRRRR
# ───────────────────────────────
with tab_brrrr:
    if not metrics.brrrr:
        st.markdown("""
        <div class="info-banner">
            💡 Enter an <strong>After Repair Value (ARV)</strong> in the sidebar to unlock BRRRR analysis.
        </div>""", unsafe_allow_html=True)
    else:
        b = metrics.brrrr
        bc1, bc2, bc3, bc4 = st.columns(4)
        def brrrr_kpi(col, label, val, color=GOLD):
            col.markdown(f"""
            <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);
                 border-radius:12px;padding:22px 16px;text-align:center;
                 position:relative;overflow:hidden;">
                <div style="position:absolute;top:0;left:0;right:0;height:2px;
                     background:linear-gradient(90deg,transparent,{color}55,transparent)"></div>
                <div style="font-size:9px;font-family:'Space Mono',monospace;
                     color:rgba(205,200,230,0.35);text-transform:uppercase;
                     letter-spacing:0.12em;margin-bottom:10px">{label}</div>
                <div style="font-family:'Space Mono',monospace;font-size:1.5rem;
                     font-weight:400;color:{color};text-shadow:0 0 20px {color}44">{val}</div>
            </div>""", unsafe_allow_html=True)

        cash_color = GREEN if b["cash_left_in_deal"] < 10_000 else GOLD
        brrrr_kpi(bc1, "Cash Left In Deal",  f"${b['cash_left_in_deal']:,.0f}", cash_color)
        brrrr_kpi(bc2, "Cash Out at Refi",   f"${b['cash_out_at_refi']:,.0f}",  GOLD)
        cf_col = GREEN if b["post_refi_monthly_cf"] > 0 else RED
        brrrr_kpi(bc3, "Post-Refi CF / mo",  f"${b['post_refi_monthly_cf']:+,.0f}", cf_col)
        coc_label = "∞ Infinite" if b["infinite_returns"] else f"{b['post_refi_coc_return']:.1f}%"
        brrrr_kpi(bc4, "Post-Refi CoC",      coc_label, GREEN)

        if b["infinite_returns"]:
            st.markdown("""
            <div class="success-banner" style="margin-top:16px">
                🎯 <strong>Infinite returns achieved</strong> — the refinance returns ALL of your invested capital
                while the property still cash flows positively. This is the holy grail of the BRRRR strategy.
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        bl, br = st.columns(2, gap="large")

        with bl:
            st.markdown('<div class="section-title">BRRRR Flow</div>', unsafe_allow_html=True)
            steps = [
                ("Purchase Price",      f"${b['arv'] - b['equity_captured']:,.0f}", ""),
                ("+ Rehab Costs",       f"${rehab_costs:,.0f}",                     ""),
                ("= Total All-In",      f"${purchase_price + rehab_costs:,.0f}",    "highlight"),
                ("After Repair Value",  f"${b['arv']:,.0f}",                         "positive"),
                ("Refi Loan (75% LTV)", f"${b['refi_loan_amount']:,.0f}",            ""),
                ("− Refi Closing",      f"(${b['refi_closing_costs']:,.0f})",        ""),
                ("Cash Returned",       f"${b['cash_out_at_refi']:,.0f}",            "positive"),
                ("Cash Left In Deal",   f"${b['cash_left_in_deal']:,.0f}",           "highlight"),
                ("Equity Captured",     f"${b['equity_captured']:,.0f}",             "positive"),
            ]
            for label, val, cls in steps:
                st.markdown(f"""
                <div class="brrrr-step {cls}">
                    <span class="bs-label">{label}</span>
                    <span class="bs-val">{val}</span>
                </div>""", unsafe_allow_html=True)

        with br:
            st.markdown('<div class="section-title">Post-Refinance Snapshot</div>', unsafe_allow_html=True)
            post_items = [
                ("Refi loan amount",      f"${b['refi_loan_amount']:,.0f}"),
                ("New monthly payment",   f"${b['refi_monthly_payment']:,.0f}"),
                ("Post-refi CF / mo",     f"${b['post_refi_monthly_cf']:+,.0f}"),
                ("Post-refi CF / yr",     f"${b['post_refi_monthly_cf']*12:,.0f}"),
                ("Cash-on-cash (post)",   coc_label),
                ("Infinite returns",      "✅ Yes" if b["infinite_returns"] else "✗ No"),
            ]
            for label, val in post_items:
                st.markdown(f"""
                <div class="stat-row">
                    <span class="sr-label">{label}</span>
                    <span class="sr-value">{val}</span>
                </div>""", unsafe_allow_html=True)

# ───────────────────────────────
# TAB: STR / Airbnb
# ───────────────────────────────
with tab_str:
    sc1, sc2, sc3, sc4 = st.columns(4)
    def str_kpi(col, label, val, color=GOLD):
        col.markdown(f"""
        <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);
             border-radius:12px;padding:22px 16px;text-align:center;
             position:relative;overflow:hidden;">
            <div style="position:absolute;top:0;left:0;right:0;height:2px;
                 background:linear-gradient(90deg,transparent,{color}55,transparent)"></div>
            <div style="font-size:9px;font-family:'Space Mono',monospace;
                 color:rgba(205,200,230,0.35);text-transform:uppercase;
                 letter-spacing:0.12em;margin-bottom:10px">{label}</div>
            <div style="font-family:'Space Mono',monospace;font-size:1.4rem;
                 font-weight:400;color:{color};text-shadow:0 0 18px {color}44">{val}</div>
        </div>""", unsafe_allow_html=True)

    str_kpi(sc1, "STR Monthly Revenue",  f"${metrics.str_monthly_revenue:,.0f}")
    str_kpi(sc2, "STR Annual Revenue",   f"${metrics.str_annual_revenue:,.0f}")
    cf_col = GREEN if metrics.str_monthly_cash_flow > 0 else RED
    str_kpi(sc3, "STR Monthly CF",       f"${metrics.str_monthly_cash_flow:+,.0f}", cf_col)
    coc_col = GREEN if metrics.str_coc_return >= 8 else GOLD
    str_kpi(sc4, "STR CoC Return",       f"{metrics.str_coc_return:.1f}%", coc_col)

    st.markdown('<div class="section-title" style="margin-top:24px">LTR vs STR Comparison</div>', unsafe_allow_html=True)

    compare_data = {
        "":                ["Long-Term (LTR)",                        "Short-Term (STR)"],
        "Monthly Revenue": [f"${metrics.gross_monthly_income:,.0f}", f"${metrics.str_monthly_revenue:,.0f}"],
        "Monthly CF":      [f"${metrics.monthly_cash_flow:+,.0f}",   f"${metrics.str_monthly_cash_flow:+,.0f}"],
        "Annual CF":       [f"${metrics.annual_cash_flow:,.0f}",      f"${metrics.str_monthly_cash_flow*12:,.0f}"],
        "CoC Return":      [f"{metrics.cash_on_cash_return:.1f}%",    f"{metrics.str_coc_return:.1f}%"],
    }

    # Visual comparison bars
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="LTR", x=["Revenue", "Cash Flow", "Annual CF"],
        y=[metrics.gross_monthly_income, max(metrics.monthly_cash_flow,0), max(metrics.annual_cash_flow,0)],
        marker_color=BLUE, marker_line=dict(width=0)))
    fig_comp.add_trace(go.Bar(name="STR", x=["Revenue", "Cash Flow", "Annual CF"],
        y=[metrics.str_monthly_revenue, max(metrics.str_monthly_cash_flow,0), max(metrics.str_monthly_cash_flow*12,0)],
        marker_color=GOLD, marker_line=dict(width=0)))
    apply_theme(fig_comp, height=300, barmode="group",
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickprefix="$"))
st.plotly_chart(fig_comp, use_container_width=True, key="chart_str_comparison")

    # Occupancy sensitivity
st.markdown('<div class="section-title">Occupancy Sensitivity</div>', unsafe_allow_html=True)
occ_range = [i/100 for i in range(30, 100, 5)]
orig = inputs.str_occupancy_rate
sens = []
for occ in occ_range:
        inputs.str_occupancy_rate = occ
        tmp = DealAnalyzer(inputs).analyze()
        sens.append({"occ": occ*100, "rev": tmp.str_monthly_revenue, "cf": tmp.str_monthly_cash_flow})
inputs.str_occupancy_rate = orig

fig_s = go.Figure()
fig_s.add_trace(go.Scatter(x=[s["occ"] for s in sens], y=[s["rev"] for s in sens],
        name="STR Revenue", line=dict(color=GOLD, width=2)))
fig_s.add_trace(go.Scatter(x=[s["occ"] for s in sens], y=[s["cf"] for s in sens],
        name="STR Cash Flow", line=dict(color=GREEN, width=2)))
fig_s.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.4)
fig_s.add_vline(x=str_occ*100, line_dash="dot", line_color=GOLD, opacity=0.5,
        annotation_text=f"Current {str_occ*100:.0f}%", annotation_font_color=GOLD)
apply_theme(fig_s, height=320,
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Occupancy (%)", ticksuffix="%"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="$/month",        tickprefix="$"))
st.plotly_chart(fig_s, use_container_width=True, key="chart_str_sensitivity")

# ───────────────────────────────
# TAB: Rent Comps
# ───────────────────────────────
with tab_comps:
    cc1, cc2 = st.columns([3, 1], gap="large")
    with cc1:
        st.markdown('<div class="section-title">Rent Comparables</div>', unsafe_allow_html=True)
    with cc2:
        comp_beds = st.number_input("Beds filter", value=3, min_value=1, max_value=6, step=1)

    fetch_btn = st.button("🔍  Fetch Live Comps from RentCast")

    if fetch_btn:
        rc_key = get_secret("RENTCAST_API_KEY")
        if not rc_key:
            st.markdown("""
            <div class="info-banner">
                ⚠️ Add <code>RENTCAST_API_KEY</code> to <code>.streamlit/secrets.toml</code> to fetch live comps.
            </div>""", unsafe_allow_html=True)
        else:
            with st.spinner("Fetching from RentCast..."):
                rc = RentCastClient(rc_key)
                fa = f"{address}, {city_st}"
                est   = rc.rent_estimate(address=fa, bedrooms=comp_beds)
                comps = rc.rent_comps(address=fa, bedrooms=comp_beds, limit=10)

            if est:
                em1, em2, em3 = st.columns(3)
                def est_card(col, label, val):
                    col.markdown(f"""
                    <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);
                         border-radius:12px;padding:16px 16px;text-align:center;margin-bottom:12px;
                         position:relative;overflow:hidden;">
                        <div style="position:absolute;top:0;left:0;right:0;height:2px;
                             background:linear-gradient(90deg,transparent,#34d39955,transparent)"></div>
                        <div style="font-size:9px;font-family:'Space Mono',monospace;
                             color:rgba(205,200,230,0.3);text-transform:uppercase;
                             letter-spacing:0.12em;margin-bottom:6px">{label}</div>
                        <div style="font-family:'Space Mono',monospace;font-size:1.2rem;
                             color:#34d399;text-shadow:0 0 16px rgba(52,211,153,0.35)">{val}</div>
                    </div>""", unsafe_allow_html=True)
                est_card(em1, "Rent Low",    f"${est['rent_low']:,.0f}"    if est['rent_low']    else "—")
                est_card(em2, "Rent Median", f"${est['rent_median']:,.0f}" if est['rent_median'] else "—")
                est_card(em3, "Rent High",   f"${est['rent_high']:,.0f}"   if est['rent_high']   else "—")

            if comps:
                st.session_state["live_comps"] = comps
            else:
                st.markdown('<div class="info-banner">No comps returned — check address or API key.</div>',
                            unsafe_allow_html=True)

    # Display comps
    comps_data = st.session_state.get("live_comps", [
        {"address": "245 W Elliot Rd", "rent": 2350, "beds": 3, "baths": 2.0, "sqft": 1400, "days_on": 12, "distance": 0.3},
        {"address": "1820 S Dobson Rd", "rent": 2500, "beds": 3, "baths": 2.0, "sqft": 1550, "days_on": 5,  "distance": 0.7},
        {"address": "3901 E Baseline",  "rent": 2200, "beds": 3, "baths": 1.0, "sqft": 1200, "days_on": 22, "distance": 0.9},
        {"address": "604 N Arizona Ave","rent": 2450, "beds": 3, "baths": 2.5, "sqft": 1480, "days_on": 8,  "distance": 1.1},
        {"address": "910 W Hunt Hwy",   "rent": 2600, "beds": 3, "baths": 2.0, "sqft": 1700, "days_on": 3,  "distance": 1.4},
    ])

    # Custom comps table
    st.markdown("""
    <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);border-radius:14px;
         overflow:hidden;margin-top:8px">
        <div class="comp-row comp-header">
            <span>Address</span><span>Rent/mo</span><span>Bed/Bath</span>
            <span>Sq Ft</span><span>Days on Market</span>
        </div>""", unsafe_allow_html=True)

    for c in comps_data:
        addr  = str(c.get("address",""))[:35]
        rent  = f"${c.get('rent',0):,.0f}" if c.get("rent") else "—"
        beds  = c.get("beds","—"); baths = c.get("baths","—")
        sqft  = f"{c.get('sqft',0):,.0f}" if c.get("sqft") else "—"
        days  = c.get("days_on","—")
        st.markdown(f"""
        <div class="comp-row">
            <span class="cr-addr">{addr}</span>
            <span class="cr-rent">{rent}</span>
            <span class="cr-stat">{beds}bd / {baths}ba</span>
            <span class="cr-stat">{sqft}</span>
            <span class="cr-stat">{days}d</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Comps chart
    rents = [c.get("rent", 0) for c in comps_data if c.get("rent")]
    if rents:
        avg_rent = sum(rents) / len(rents)
        labels   = [str(c.get("address",""))[:20] for c in comps_data if c.get("rent")]
        bar_cols = [GREEN if r >= monthly_rent else GOLD for r in rents]

        fig_rc = go.Figure()
        fig_rc.add_trace(go.Bar(x=labels, y=rents, marker_color=bar_cols,
                                 marker_line=dict(width=0), name="Comp Rent"))
        fig_rc.add_hline(y=monthly_rent, line_color=BLUE, line_dash="dash",
                          annotation_text=f"Your rent  ${monthly_rent:,.0f}",
                          annotation_font_color=BLUE)
        fig_rc.add_hline(y=avg_rent, line_color=GOLD, line_dash="dot",
                          annotation_text=f"Avg comp  ${avg_rent:,.0f}",
                          annotation_font_color=GOLD, annotation_position="bottom right")
        apply_theme(fig_rc, height=300,
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickangle=-20),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", tickprefix="$"))
        st.plotly_chart(fig_rc, use_container_width=True, key="chart_rent_comps")

        pct_diff = ((monthly_rent - avg_rent) / avg_rent) * 100
        if pct_diff > 5:
            st.markdown(f'<div class="info-banner">⚠️ Your rent is <strong>{pct_diff:.1f}% above</strong> the comp average of ${avg_rent:,.0f}. Consider stress-testing at the lower comp rent.</div>', unsafe_allow_html=True)
        elif pct_diff < -5:
            st.markdown(f'<div class="success-banner">✅ Your rent is <strong>{abs(pct_diff):.1f}% below</strong> comp average — potential upside of ${avg_rent - monthly_rent:,.0f}/mo.</div>', unsafe_allow_html=True)

# ───────────────────────────────
# TAB: Amortization
# ───────────────────────────────
with tab_amort:
    if metrics.loan_amount > 0 and not interest_only:
        amort = amortization_schedule(metrics.loan_amount, interest_rate, loan_term)
        adf   = pd.DataFrame(amort)
        yearly = adf.groupby("year").agg(
            Principal_Paid=("principal", "sum"),
            Interest_Paid =("interest",  "sum"),
            Balance       =("balance",   "last"),
        ).reset_index()
        yearly.columns = ["Year","Principal Paid","Interest Paid","Balance"]
        yearly = yearly.map(lambda x: round(x, 0) if isinstance(x, float) else x)

        am1, am2, am3 = st.columns(3)
        def am_kpi(col, label, val):
            col.markdown(f"""
            <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);
                 border-radius:12px;padding:18px 16px;text-align:center;
                 position:relative;overflow:hidden;">
                <div style="position:absolute;top:0;left:0;right:0;height:2px;
                     background:linear-gradient(90deg,transparent,#d4a84355,transparent)"></div>
                <div style="font-size:9px;font-family:'Space Mono',monospace;
                     color:rgba(205,200,230,0.3);text-transform:uppercase;
                     letter-spacing:0.12em;margin-bottom:8px">{label}</div>
                <div style="font-family:'Space Mono',monospace;font-size:1.1rem;
                     color:#d4a843;text-shadow:0 0 16px rgba(212,168,67,0.35)">{val}</div>
            </div>""", unsafe_allow_html=True)

        total_interest = adf["interest"].sum()
        am_kpi(am1, "Loan Amount",   f"${metrics.loan_amount:,.0f}")
        am_kpi(am2, "Total Interest",f"${total_interest:,.0f}")
        am_kpi(am3, "Total Cost",    f"${metrics.loan_amount + total_interest:,.0f}")

        st.markdown("<br>", unsafe_allow_html=True)
        fig_am = go.Figure()
        fig_am.add_trace(go.Bar(x=yearly["Year"], y=yearly["Principal Paid"],
            name="Principal", marker_color=GREEN, marker_line=dict(width=0)))
        fig_am.add_trace(go.Bar(x=yearly["Year"], y=yearly["Interest Paid"],
            name="Interest", marker_color=RED, marker_line=dict(width=0)))
        fig_am.add_trace(go.Scatter(x=yearly["Year"], y=yearly["Balance"],
            name="Balance", line=dict(color=GOLD, width=2),
            mode="lines+markers", marker=dict(size=4), yaxis="y2"))
        apply_theme(fig_am, height=380, barmode="stack",
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Year", dtick=5),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="$/Year", tickprefix="$"),
    yaxis2=dict(title="Balance", overlaying="y", side="right",
                gridcolor="rgba(0,0,0,0)", tickprefix="$",
                tickfont=dict(family="Space Mono, monospace", size=10)))
        st.plotly_chart(fig_am, use_container_width=True, key="chart_amortization")

        if st.checkbox("Show full monthly schedule"):
            display_df = adf[["month","year","payment","principal","interest","balance"]].copy()
            display_df.columns = ["Month","Year","Payment","Principal","Interest","Balance"]
            st.dataframe(display_df, hide_index=True, use_container_width=True)
    else:
        st.markdown('<div class="info-banner">Amortization not available for interest-only or zero-loan scenarios.</div>',
                    unsafe_allow_html=True)

# ───────────────────────────────
# TAB: Market Data
# ───────────────────────────────
with tab_macro:
    st.markdown('<div class="section-title">FRED Economic Indicators</div>', unsafe_allow_html=True)

    if st.button("🔄  Refresh Market Data"):
        fred_key = get_secret("FRED_API_KEY")
        if not fred_key:
            st.markdown('<div class="info-banner">Add <code>FRED_API_KEY</code> to secrets.toml (free at fred.stlouisfed.org)</div>',
                        unsafe_allow_html=True)
        else:
            with st.spinner("Fetching from FRED..."):
                fred = FREDClient(fred_key)
                st.session_state["macro"] = fred.get_market_summary()

    macro = st.session_state.get("macro", {
        "mortgage_30yr":     0.0693,
        "mortgage_15yr":     0.0631,
        "fed_funds_rate":    0.053,
        "cpi":               314.2,
        "unemployment":      3.9,
        "house_price_index": 421.0,
    })

    st.markdown(f"""
    <div class="macro-ticker">
        <div class="macro-item">
            <div class="mi-label">30-yr Fixed</div>
            <div class="mi-val warn">{macro.get('mortgage_30yr',0)*100:.2f}%</div>
        </div>
        <div class="macro-item">
            <div class="mi-label">15-yr Fixed</div>
            <div class="mi-val warn">{macro.get('mortgage_15yr',0)*100:.2f}%</div>
        </div>
        <div class="macro-item">
            <div class="mi-label">Fed Funds</div>
            <div class="mi-val">{macro.get('fed_funds_rate',0)*100:.2f}%</div>
        </div>
        <div class="macro-item">
            <div class="mi-label">CPI Index</div>
            <div class="mi-val">{macro.get('cpi',0):,.1f}</div>
        </div>
        <div class="macro-item">
            <div class="mi-label">Unemployment</div>
            <div class="mi-val up">{macro.get('unemployment',0):.1f}%</div>
        </div>
        <div class="macro-item">
            <div class="mi-label">HPI (National)</div>
            <div class="mi-val">{macro.get('house_price_index',0):,.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Rate impact on deal
    st.markdown('<div class="section-title">Rate Sensitivity on This Deal</div>', unsafe_allow_html=True)
    rate_range = [r/100 for r in range(400, 1050, 25)]
    orig_rate  = inputs.loan_interest_rate
    rate_sens  = []
    for r in rate_range:
        inputs.loan_interest_rate = r
        tmp = DealAnalyzer(inputs).analyze()
        rate_sens.append({"rate": r*100, "cf": tmp.monthly_cash_flow, "dscr": tmp.dscr})
    inputs.loan_interest_rate = orig_rate

    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(
        x=[s["rate"] for s in rate_sens], y=[s["cf"] for s in rate_sens],
        name="Monthly CF", line=dict(color=GOLD, width=2), fill="tozeroy",
        fillcolor="rgba(79,114,255,0.06)"))
    fig_rate.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.5)
    fig_rate.add_vline(x=interest_rate*100, line_dash="dot", line_color=BLUE, opacity=0.6,
        annotation_text=f"Your rate {interest_rate*100:.2f}%",
        annotation_font_color=BLUE)
    apply_theme(fig_rate, height=320,
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Interest Rate (%)", ticksuffix="%"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", title="Monthly CF ($)",    tickprefix="$"))
    st.plotly_chart(fig_rate, use_container_width=True, key="chart_rate_sensitivity")

    st.markdown("""
    <div class="info-banner">
        <strong>Reading the macro environment</strong><br>
        Higher Fed Funds → elevated mortgage rates → lower cash flow.
        Rising CPI → inflation erodes fixed mortgage costs but raises expenses.
        Low unemployment → strong rental demand → lower vacancy risk.
        Rising HPI → property appreciates → stronger BRRRR equity.
    </div>""", unsafe_allow_html=True)

# ───────────────────────────────
# TAB: Local Listings
# ───────────────────────────────
with tab_listings:
    st.markdown('<div class="section-title">Listings Near This Property</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:12.5px;color:rgba(205,200,230,0.45);margin-bottom:16px">'
        'Active rental and for-sale listings in the same area — powered by RentCast. '
        'Scroll photos left/right inside each card to browse all listing images.</p>',
        unsafe_allow_html=True,
    )

    # ── Controls row ──────────────────────────────
    lc0, lc1, lc2, lc3, lc4 = st.columns([2, 2, 1, 1, 1])
    with lc0:
        listing_type = st.radio(
            "Type", ["Rental", "For Sale"],
            horizontal=True, label_visibility="collapsed",
            key="listing_type",
        )
        st.caption("Listing type")
    with lc1:
        listing_zip = st.text_input(
            "Search ZIP", value=zip_code,
            placeholder="ZIP code", label_visibility="collapsed",
            key="listing_zip_input",
        )
        st.caption(f"ZIP code to search  (currently {zip_code})")
    with lc2:
        listing_beds = st.selectbox(
            "Beds", ["Any", 1, 2, 3, 4, 5],
            label_visibility="collapsed", key="listing_beds",
        )
        st.caption("Bedrooms filter")
    with lc3:
        listing_max_price = st.number_input(
            "Max Price", value=0, step=100, format="%d",
            label_visibility="collapsed", key="listing_max_rent",
        )
        st.caption("Max price (0 = any)")
    with lc4:
        listing_limit = st.selectbox(
            "Show", [6, 9, 12, 18],
            label_visibility="collapsed", key="listing_limit",
        )
        st.caption("Results to show")

    fetch_btn = st.button("Search Listings", key="btn_fetch_listings",
                          use_container_width=False)

    rc_key_listings = get_secret("RENTCAST_API_KEY")
    gmaps_key_listings = get_secret("GOOGLE_MAPS_API_KEY")

    _cache_key = f"local_listings_{listing_type}"
    if fetch_btn or _cache_key not in st.session_state:
        if rc_key_listings:
            spinner_label = "Fetching rental listings…" if listing_type == "Rental" else "Fetching for-sale listings…"
            with st.spinner(spinner_label):
                fetcher = ListingsFetcher(
                    rentcast_key=rc_key_listings,
                    gmaps_key=gmaps_key_listings,
                )
                beds_filter  = None if listing_beds == "Any" else int(listing_beds)
                price_filter = int(listing_max_price) if listing_max_price else None
                if listing_type == "Rental":
                    results = fetcher.fetch_by_zip(
                        zip_code=listing_zip or zip_code,
                        bedrooms=beds_filter,
                        max_rent=price_filter,
                        limit=int(listing_limit),
                    )
                else:
                    results = fetcher.fetch_for_sale_by_zip(
                        zip_code=listing_zip or zip_code,
                        bedrooms=beds_filter,
                        max_price=price_filter,
                        limit=int(listing_limit),
                    )
                st.session_state[_cache_key] = results or []
        else:
            st.session_state[_cache_key] = DEMO_LISTINGS[:int(listing_limit)]

    listings_to_show = st.session_state.get(_cache_key, DEMO_LISTINGS[:6])

    if not listings_to_show:
        st.markdown(
            '<div class="info-banner">No active listings found for that ZIP. '
            'Try a nearby ZIP or remove filters.</div>',
            unsafe_allow_html=True,
        )
    else:
        if not rc_key_listings:
            st.markdown(
                '<div class="info-banner">No RentCast API key — showing demo listings. '
                'Add <code>RENTCAST_API_KEY</code> to secrets.toml for live data.</div>',
                unsafe_allow_html=True,
            )

        # ── Photo card grid (3 per row) ──────────
        is_sale_tab = listing_type == "For Sale"
        cols_per_row = 3
        rows = [listings_to_show[i:i + cols_per_row]
                for i in range(0, len(listings_to_show), cols_per_row)]

        for row in rows:
            grid_cols = st.columns(cols_per_row, gap="medium")
            for col, listing in zip(grid_cols, row):
                addr       = listing.get("address", "")
                city       = listing.get("city", "")
                state      = listing.get("state", "")
                price      = listing.get("rent", 0)
                beds       = listing.get("beds", "—")
                baths      = listing.get("baths", "—")
                sqft       = listing.get("sqft", 0)
                days       = listing.get("days_on", "—")
                ptype      = listing.get("property_type", "")
                photo_urls = listing.get("photo_urls") or [listing.get("photo_url", "")]
                url        = listing.get("listing_url", "")

                if is_sale_tab or listing.get("is_sale"):
                    price_str = f"${price:,.0f}" if price else "—"
                    price_cls = "listing-card-rent sale-price-badge"
                else:
                    price_str = f"${price:,.0f}/mo" if price else "—"
                    price_cls = "listing-card-rent"

                sqft_str  = f"{sqft:,.0f} sqft" if sqft else ""
                beds_str  = f"{beds} bd" if beds != "—" else "—"
                baths_str = f"{baths} ba" if baths != "—" else "—"

                link_open  = f'<a href="{url}" target="_blank" style="text-decoration:none">' if url else "<div>"
                link_close = "</a>" if url else "</div>"

                # Build photo carousel — all photos, scroll-snap
                photo_imgs = "".join(
                    f'<img src="{p}" alt="{addr}" loading="lazy" '
                    f'onerror="this.style.display=\'none\'">'
                    for p in photo_urls
                )
                n_photos    = len(photo_urls)
                count_badge = (
                    f'<div class="photo-count-badge">{n_photos} photo{"s" if n_photos != 1 else ""}</div>'
                    if n_photos > 1 else ""
                )

                col.markdown(f"""
{link_open}
<div class="listing-card">
    <div class="photo-reel-wrap">
        <div class="photo-reel">{photo_imgs}</div>
        {count_badge}
    </div>
    <div class="listing-card-body">
        <div class="{price_cls}">{price_str}</div>
        <div class="listing-card-addr">{addr}, {city}, {state}</div>
        {"" if not ptype else f'<div class="listing-card-type">{ptype}</div>'}
        <div class="listing-card-badges">
            {"" if beds == "—" else f'<span class="listing-badge">{beds_str}</span>'}
            {"" if baths == "—" else f'<span class="listing-badge">{baths_str}</span>'}
            {"" if not sqft_str else f'<span class="listing-badge">{sqft_str}</span>'}
        </div>
        <div class="listing-card-meta">{days}d on market</div>
    </div>
</div>
{link_close}
""", unsafe_allow_html=True)

        st.markdown(
            f'<p style="font-size:10.5px;color:rgba(205,200,230,0.25);'
            f'font-family:Space Mono,monospace;margin-top:16px">'
            f'{len(listings_to_show)} listings · ZIP {listing_zip or zip_code} · '
            f'{"For Sale" if is_sale_tab else "Rental"} · '
            f'Source: RentCast{"" if rc_key_listings else " (demo)"}</p>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;padding:20px 36px;border-top:1px solid rgba(255,255,255,0.05);
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <span style="font-family:'Space Mono',monospace;font-size:10px;color:rgba(205,200,230,0.25);
          text-transform:uppercase;letter-spacing:0.1em">
        DealSight · Not financial advice
    </span>
    <span style="font-family:'Space Mono',monospace;font-size:10px;color:rgba(205,200,230,0.2)">
        Data: RentCast · Zillow · FRED · ATTOM · Census · Google Maps
    </span>
</div>
""", unsafe_allow_html=True)