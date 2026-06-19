"""
DealSight — Rental Property Deal Analyzer
Slick professional UI with Google Maps integration
Run: streamlit run streamlit_app/app.py  (from project root)
"""

import sys, os, re, base64
_app_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _app_dir)  # makes python_core importable on Streamlit Cloud

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import asdict, replace as dc_replace
import urllib.parse
import streamlit.components.v1 as components
from python_core.calculations import PropertyInputs, DealAnalyzer, grade_deal, amortization_schedule
from python_core.data_sources import RentCastClient, FREDClient
from python_core.listings import ListingsFetcher, DEMO_LISTINGS
from python_core.db import sign_in, sign_up, sign_out, is_authenticated, current_user
from python_core.utils import (
    GOLD, GREEN, RED, BLUE, PURPLE,
    fmt_usd, fmt_pct, fmt_label,
    kpi_card, simple_kpi, apply_theme,
)

try:
    import braintrust
    braintrust.init_logger(project="DealSight")
    braintrust.auto_instrument()
except Exception:
    pass

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _logo_b64(filename: str = "logo.png") -> str:
    """Return a base64 data-URL for a file in streamlit_app/assets/."""
    _path = os.path.join(os.path.dirname(__file__), "assets", filename)
    try:
        with open(_path, "rb") as _f:
            return "data:image/png;base64," + base64.b64encode(_f.read()).decode()
    except FileNotFoundError:
        return ""

def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

def logo_url(domain: str, size: int = 32) -> str:
    """Return a Logo.dev image URL for the given domain."""
    token = get_secret("LOGO_DEV_TOKEN")
    base = f"https://img.logo.dev/{domain}?size={size}&format=png"
    return f"{base}&token={token}" if token else base

def n(val: int | float | None, default: float = 0.0) -> float:
    """Coerce st.number_input output to float, never None."""
    return float(val) if val is not None else default


# ─────────────────────────────────────────────
# Landing / Login page
# ─────────────────────────────────────────────
def show_auth_page() -> None:
    """Render landing + login page, then call st.stop()."""
    sb_ok = bool(get_secret("SUPABASE_URL") and get_secret("SUPABASE_ANON_KEY"))

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding: 48px 5% 40px !important; max-width: 100% !important; }
    .stApp { background: #f4f7f5 !important; }

    /* Auth page background glow */
    .stApp::before {
        content: "";
        position: fixed; inset: 0; z-index: -1; pointer-events: none;
        background:
            radial-gradient(ellipse 60% 55% at 15% 55%, rgba(22,163,74,0.10) 0%, transparent 60%),
            radial-gradient(ellipse 50% 45% at 85% 20%, rgba(34,197,94,0.08) 0%, transparent 55%);
    }

    /* Auth form styling */
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid rgba(12,40,28,0.10) !important;
        border-radius: 16px !important;
        padding: 28px 24px !important;
        box-shadow: 0 12px 40px rgba(12,40,28,0.08) !important;
    }
    div[data-testid="stForm"] .stTextInput input {
        background: #f4f7f5 !important;
        border: 1px solid rgba(12,40,28,0.12) !important;
        border-radius: 8px !important;
        color: #0b1410 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
    }
    div[data-testid="stForm"] .stTextInput input:focus {
        border-color: #16a34a !important;
        box-shadow: 0 0 0 2px rgba(22,163,74,0.2) !important;
    }
    div[data-testid="stForm"] .stTextInput label { color: rgba(17,40,30,0.66) !important; font-size: 12px !important; }
    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #22c55e 0%, #15803d 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        height: 44px !important;
        box-shadow: 0 4px 18px rgba(22,163,74,0.32) !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        opacity: 0.92 !important;
        transform: translateY(-1px) !important;
    }
    /* Demo button */
    .auth-demo-btn button {
        background: #ffffff !important;
        border: 1px solid rgba(12,40,28,0.12) !important;
        border-radius: 8px !important;
        color: rgba(17,40,30,0.7) !important;
        font-size: 13px !important;
    }
    .auth-demo-btn button:hover {
        border-color: rgba(22,163,74,0.5) !important;
        color: #15803d !important;
    }
    /* Radio toggle as pill tabs */
    div[data-testid="stRadio"] > div {
        gap: 0 !important;
        background: #eef3f0 !important;
        border: 1px solid rgba(12,40,28,0.10) !important;
        border-radius: 8px !important;
        padding: 3px !important;
        width: 100% !important;
    }
    div[data-testid="stRadio"] label {
        flex: 1 !important;
        justify-content: center !important;
        border-radius: 6px !important;
        padding: 6px 0 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: rgba(17,40,30,0.6) !important;
        transition: all 0.15s !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: rgba(22,163,74,0.16) !important;
        color: #15803d !important;
    }
    div[data-testid="stRadio"] input { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    col_hero, col_form = st.columns([1.25, 1], gap="large")

    # ── Hero ──────────────────────────────────
    with col_hero:
        _hero_metrics = [
            ("$412/mo", "Cash Flow"),
            ("6.8%",    "Cap Rate"),
            ("1.34×",   "DSCR"),
            ("9.2%",    "Cash-on-Cash"),
            ("∞",       "BRRRR CoC"),
        ]
        _pills = "".join(
            f"""<div style="background:#f9fbfa;border:1px solid #e3e9e5;border-radius:12px;
                 padding:11px 16px;min-width:92px;box-shadow:0 1px 3px rgba(12,40,28,0.05)">
              <div style="font-family:'Space Mono',monospace;font-size:18px;font-weight:500;
                   color:#16a34a;line-height:1">{_v}</div>
              <div style="font-size:10px;color:#51635a;text-transform:uppercase;letter-spacing:0.08em;
                   margin-top:5px;font-family:'Plus Jakarta Sans',sans-serif">{_l}</div>
            </div>"""
            for _v, _l in _hero_metrics
        )
        st.markdown(f"""
        <div style="padding:20px 0 0">
          <div style="margin-bottom:26px">
            <img src="{_logo_b64('logo.png')}" height="64"
                 style="object-fit:contain;display:block;
                        filter:drop-shadow(0 0 24px rgba(22,163,74,0.55))">
          </div>

          <div style="display:inline-flex;align-items:center;gap:8px;
               background:rgba(22,163,74,0.10);border:1px solid rgba(22,163,74,0.20);
               border-radius:100px;padding:6px 14px;margin-bottom:24px;
               font-family:'Space Mono',monospace;font-size:11.5px;color:#15803d">
            <span style="width:6px;height:6px;border-radius:50%;background:#22c55e;
                 box-shadow:0 0 8px #22c55e"></span>
            Live data · RentCast · Zillow · FRED · ATTOM · Census
          </div>

          <h1 style="font-family:'Space Grotesk',sans-serif;font-size:44px;font-weight:700;
               line-height:1.08;color:#0b1410;margin:0 0 18px;letter-spacing:-0.025em">
            Stop guessing.<br>
            <span style="background:linear-gradient(130deg,#16a34a,#22c55e);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text">Analyze deals</span><br>
            in 30 seconds.
          </h1>

          <p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:16px;
               color:rgba(17,40,30,0.65);line-height:1.65;margin:0 0 30px;max-width:440px">
            The only rental analyzer that grades every deal A–F — cash flow, cap rate,
            DSCR, BRRRR, and Airbnb STR with live rent comps, all in one tool.
          </p>

          <div style="display:flex;flex-wrap:wrap;gap:12px">{_pills}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Auth form ─────────────────────────────
    with col_form:
        st.markdown("""
        <div style="padding:20px 0 12px">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:20px;font-weight:700;
               color:#0b1410;margin-bottom:4px">Get Started Free</div>
          <div style="font-size:13px;color:rgba(17,40,30,0.45);font-family:'Plus Jakarta Sans',sans-serif;
               margin-bottom:20px">No credit card required</div>
        </div>
        """, unsafe_allow_html=True)

        auth_mode = st.radio(
            "auth_toggle",
            ["Sign In", "Create Account"],
            horizontal=True,
            key="auth_mode_radio",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        auth_feedback = st.empty()

        if sb_ok:
            with st.form("auth_form_main", clear_on_submit=False):
                name_in = ""
                if auth_mode == "Create Account":
                    name_in = st.text_input("Full Name", placeholder="Jane Smith", key="auth_name_in")
                email_in = st.text_input("Email Address", placeholder="you@example.com", key="auth_email_in")
                pass_in  = st.text_input(
                    "Password", type="password", key="auth_pass_in",
                    placeholder="Min 8 characters" if auth_mode == "Create Account" else "••••••••",
                )
                go = st.form_submit_button(
                    "Sign In →" if auth_mode == "Sign In" else "Create Free Account →",
                    use_container_width=True,
                )

            if go:
                if auth_mode == "Sign In":
                    res = sign_in(email_in, pass_in)
                    if res["error"]:
                        auth_feedback.error(res["error"])
                    else:
                        st.rerun()
                else:
                    res = sign_up(email_in, pass_in, name_in)
                    if res["error"]:
                        auth_feedback.error(res["error"])
                    else:
                        auth_feedback.success("Account created! Check your email to confirm, then sign in.")
        else:
            st.info("Supabase not configured — use Demo mode to explore the app.")

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="auth-demo-btn">', unsafe_allow_html=True)
        if st.button("Try Demo — No Account Needed →", use_container_width=True, key="btn_demo_mode"):
            st.session_state["demo_mode"] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(12,40,28,0.08);
             font-size:11.5px;color:rgba(17,40,30,0.3);font-family:'Space Mono',monospace;
             text-align:center;line-height:1.6">
          Free: 3 analyses &nbsp;·&nbsp; Pro $29/mo: 100 analyses + live data<br>
          Team $79/mo: unlimited
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
_favicon_path = os.path.join(os.path.dirname(__file__), 'assets', 'favicon.png')
try:
    from PIL import Image as _PILImage
    _favicon = _PILImage.open(_favicon_path)
except Exception:
    _favicon = '💎'

st.set_page_config(
    page_title='DealSight - Deal Analyzer',
    page_icon=_favicon,
    layout='wide',
    initial_sidebar_state='expanded',
)

# ─────────────────────────────────────────────
# Global CSS — Premium Fintech Real Estate theme
# ─────────────────────────────────────────────
def inject_css() -> None:
    _css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(_css_path) as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)
inject_css()

# ─────────────────────────────────────────────
# Session-state defaults (address search writes here)
# ─────────────────────────────────────────────
DEMO_ADDRESS       = "123 Main St"
DEMO_CITY_STATE    = "Phoenix, AZ"
DEMO_ZIP           = "85001"
LISTINGS_COLS_PER_ROW = 3

st.session_state.setdefault("sb_address",  DEMO_ADDRESS)
st.session_state.setdefault("sb_city_st",  DEMO_CITY_STATE)
st.session_state.setdefault("sb_zip_code", DEMO_ZIP)

# Apply pending address updates before widgets are instantiated
for _wk, _pk in [("sb_address", "_pending_sb_address"),
                 ("sb_city_st", "_pending_sb_city_st"),
                 ("sb_zip_code", "_pending_sb_zip_code")]:
    if _pk in st.session_state:
        st.session_state[_wk] = st.session_state.pop(_pk)

# ─────────────────────────────────────────────
# Auth gate — show landing page if not signed in
# (demo_mode bypasses auth for anonymous usage)
# ─────────────────────────────────────────────
if not is_authenticated() and not st.session_state.get("demo_mode"):
    show_auth_page()  # calls st.stop() internally

# ─────────────────────────────────────────────
# Sidebar — Inputs
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 0 14px;display:flex;align-items:center;gap:11px;
         border-bottom:1px solid rgba(12,40,28,0.10);margin-bottom:8px">
        <img src="{_logo_b64('icon.png')}" width="54" height="54"
             style="object-fit:contain;flex-shrink:0;
                    filter:drop-shadow(0 2px 8px rgba(22,163,74,0.35))">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:20px;font-weight:700;
              letter-spacing:-0.02em;
              background:linear-gradient(135deg,#0b1410,#16a34a);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text">DealSight</span>
    </div>
    """, unsafe_allow_html=True)

    # ── User / session pill ───────────────────
    _user = current_user()
    if _user:
        _email = getattr(_user, "email", "") or ""
        st.markdown(
            f'<div style="font-size:11px;color:rgba(17,40,30,0.4);'
            f'font-family:Space Mono,monospace;padding:0 4px 8px;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            f'● {_email}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="btn_sign_out", use_container_width=True):
            sign_out()
            st.session_state.pop("demo_mode", None)
            st.rerun()
    elif st.session_state.get("demo_mode"):
        st.markdown(
            '<div style="font-size:11px;color:rgba(22,163,74,0.7);'
            'font-family:Space Mono,monospace;padding:0 4px 4px">◆ Demo mode</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign In / Create Account", key="btn_go_login", use_container_width=True):
            st.session_state.pop("demo_mode", None)
            st.rerun()

    st.markdown('<div class="sidebar-section">Property</div>', unsafe_allow_html=True)
    address: str  = st.text_input("Street Address", key="sb_address",  label_visibility="collapsed", placeholder="Street address")
    city_st: str  = st.text_input("City, State",    key="sb_city_st",  label_visibility="collapsed", placeholder="City, State")
    zip_code: str = st.text_input("ZIP",             key="sb_zip_code", label_visibility="collapsed", placeholder="ZIP code")

    st.markdown('<div class="sidebar-section">Purchase</div>', unsafe_allow_html=True)
    purchase_price: int = st.number_input("Purchase Price",  value=350_000, step=5_000, format="%d", label_visibility="collapsed")
    st.caption("Purchase price ($)")
    down_pct: float = st.slider("Down Payment", 5, 50, 20, label_visibility="collapsed") / 100
    st.caption(f"Down payment  {int(down_pct*100)}%  Â·  ${purchase_price*down_pct:,.0f}")
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
        <img src="{_logo_b64('logo.png')}" height="60"
             style="object-fit:contain;display:block;
                    filter:drop-shadow(0 0 18px rgba(34,197,94,0.55))">
    </div>
    <div class="topbar-address" style="color:{'#eafff4' if address != '123 Main St' else 'rgba(210,240,225,0.6)'};
         {'font-weight:500;' if address != '123 Main St' else ''}">
        {'🔍 ' if address == '123 Main St' else ''}{full_address if address != "123 Main St" else "Enter an address below ↑"}
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
    _search_go = st.button("Analyze ↑", key="btn_addr_search", use_container_width=True)

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
    st.markdown('<div class="section-title">🔍 Property Location</div>', unsafe_allow_html=True)

    if maps_key:
        # Google Maps Embed — shows map + street view toggle
        map_html = f"""
        <div style="position:relative;border-radius:12px;overflow:hidden;
             border:1px solid rgba(12,40,28,0.10);height:340px;">
            <div style="position:absolute;top:12px;left:12px;z-index:10;
                 background:rgba(5,5,17,0.88);backdrop-filter:blur(10px);
                 border:1px solid rgba(22,163,74,0.3);border-radius:6px;
                 padding:5px 10px;font-size:10px;font-family:monospace;
                 color:#15803d;text-transform:uppercase;letter-spacing:0.1em;">
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
        with st.expander("📸 Street View"):
            sv_html = f"""
            <div style="border-radius:10px;overflow:hidden;border:1px solid rgba(12,40,28,0.10);">
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
        osm_clean = f"""
        <div style="border-radius:12px;overflow:hidden;border:1px solid rgba(12,40,28,0.10);height:340px;position:relative;">
            <div style="position:absolute;top:12px;left:12px;z-index:10;
                 background:rgba(5,5,17,0.92);backdrop-filter:blur(10px);
                 border:1px solid rgba(22,163,74,0.3);border-radius:6px;
                 padding:5px 10px;font-size:10px;font-family:monospace;
                 color:#15803d;text-transform:uppercase;letter-spacing:0.1em;">
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
             color:rgba(17,40,30,0.25);font-family:monospace;">
            Add GOOGLE_MAPS_API_KEY to secrets.toml for the full Google Maps + Street View experience
        </div>
        """
        components.html(osm_clean, height=370)

with info_col:
    st.markdown('<div class="section-title">ðŸ¡ Deal Summary</div>', unsafe_allow_html=True)

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

# Build the 5 KPI cards
g = grades  # shorthand
cf_fmt   = fmt_usd(metrics.monthly_cash_flow, sign=True)
cap_fmt  = fmt_pct(metrics.cap_rate * 100, decimals=2)
coc_fmt  = fmt_pct(metrics.cash_on_cash_return)
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
<div style="display:flex;background:rgba(17,40,30,0.04);
     border-top:1px solid rgba(12,40,28,0.08);
     border-bottom:1px solid rgba(12,40,28,0.08);">
    {kpi_card("Monthly Cash Flow", cf_fmt,   g["cash_flow"][0], g["cash_flow"][1], f"{fmt_usd(metrics.annual_cash_flow)}/yr")}
    {kpi_card("Cap Rate",          cap_fmt,  g["cap_rate"][0],  g["cap_rate"][1],  "NOI / price")}
    {kpi_card("Cash-on-Cash",      coc_fmt,  g["coc"][0],       g["coc"][1],       f"on {fmt_usd(metrics.total_cash_invested)}")}
    {kpi_card("DSCR",              dscr_fmt, g["dscr"][0],      g["dscr"][1],      "â‰¥1.25 lender pref")}
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
        labels   = ["Gross Rent"] + [fmt_label(k) for k in bd] + ["Net Cash Flow"]
        values   = [metrics.gross_monthly_income] + [-v for v in bd.values()] + [metrics.monthly_cash_flow]
        measures = ["absolute"] + ["relative"] * len(bd) + ["total"]

        fig = go.Figure(go.Waterfall(
            orientation="v", measure=measures, x=labels, y=values,
            text=[f"${abs(v):,.0f}" for v in values], textposition="outside",
            textfont=dict(family="Space Mono, monospace", size=10),
            connector=dict(line=dict(color="rgba(17,40,30,0.18)")),
            decreasing=dict(marker=dict(color=RED,   line=dict(width=0))),
            increasing=dict(marker=dict(color=GREEN, line=dict(width=0))),
            totals=dict(    marker=dict(color=GOLD,  line=dict(width=0))),
        ))
        apply_theme(fig, height=380,
        xaxis=dict(gridcolor="rgba(17,40,30,0.08)", tickangle=-20, tickfont=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True, key="chart_waterfall")
        
    with col_exp:
        st.markdown('<div class="section-title">Expense Breakdown</div>', unsafe_allow_html=True)
        exp_labels = [fmt_label(k) for k in bd]
        exp_vals   = list(bd.values())
        colors_pie = ["#16a34a", "#22c55e", "#15803d", "#4ade80", "#0f766e", "#84cc16", "#94a3b8"]

        fig2 = go.Figure(go.Pie(
            labels=exp_labels, values=exp_vals, hole=0.58,
            textinfo="percent", textfont=dict(family="Space Mono, monospace", size=10),
            marker=dict(colors=colors_pie[:len(exp_vals)],
                        line=dict(color="#ffffff", width=2)),
        ))
        fig2.add_annotation(
            text=f"${sum(exp_vals):,.0f}<br><span style='font-size:10px'>per month</span>",
            font=dict(size=15, color="#0b1410", family="Space Mono, monospace"),
            showarrow=False,
        )
        apply_theme(fig2, height=380,
        xaxis=dict(gridcolor="rgba(17,40,30,0.08)", tickangle=-20, tickfont=dict(size=10)))
        st.plotly_chart(fig2, use_container_width=True, key="chart_expense_donut")

    # Itemized expense table
    st.markdown('<div class="section-title">Itemized Expenses</div>', unsafe_allow_html=True)
    icol1, icol2 = st.columns(2, gap="large")
    items = list(bd.items())
    half  = len(items) // 2

    with icol1:
        for k, v in items[:half+1]:
            label = fmt_label(k)
            st.markdown(f"""
            <div class="expense-row">
                <span class="er-label">{label}</span>
                <span class="er-value">(${v:,.0f}/mo)</span>
            </div>""", unsafe_allow_html=True)

    with icol2:
        for k, v in items[half+1:]:
            label = fmt_label(k)
            st.markdown(f"""
            <div class="expense-row">
                <span class="er-label">{label}</span>
                <span class="er-value">(${v:,.0f}/mo)</span>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="expense-row" style="margin-top:8px;padding-top:12px;border-top:1px solid rgba(12,40,28,0.12);">
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
    yaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Cash Flow ($)", tickprefix="$"),
    yaxis2=dict(title="Value ($)", overlaying="y", side="right",
                gridcolor="rgba(0,0,0,0)", tickprefix="$",
                tickfont=dict(family="Space Mono, monospace", size=10)),
    xaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Year", dtick=1),
    legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig3, use_container_width=True, key="chart_projection")

# ───────────────────────────────
# TAB: BRRRR
# ───────────────────────────────
with tab_brrrr:
    if not metrics.brrrr:
        st.markdown("""
        <div class="info-banner">
            ðŸ'¡ Enter an <strong>After Repair Value (ARV)</strong> in the sidebar to unlock BRRRR analysis.
        </div>""", unsafe_allow_html=True)
    else:
        b = metrics.brrrr
        bc1, bc2, bc3, bc4 = st.columns(4)
        cash_color = GREEN if b.cash_left_in_deal < 10_000 else GOLD
        simple_kpi(bc1, "Cash Left In Deal",  fmt_usd(b.cash_left_in_deal),        cash_color)
        simple_kpi(bc2, "Cash Out at Refi",   fmt_usd(b.cash_out_at_refi),         GOLD)
        cf_col    = GREEN if b.post_refi_monthly_cf > 0 else RED
        simple_kpi(bc3, "Post-Refi CF / mo",  fmt_usd(b.post_refi_monthly_cf, sign=True), cf_col)
        coc_label = "∞ Infinite" if b.infinite_returns else fmt_pct(b.post_refi_coc_return)
        simple_kpi(bc4, "Post-Refi CoC",      coc_label, GREEN)

        if b.infinite_returns:
            st.markdown("""
            <div class="success-banner" style="margin-top:16px">
                ðŸŽ¯ <strong>Infinite returns achieved</strong> — the refinance returns ALL of your invested capital
                while the property still cash flows positively. This is the holy grail of the BRRRR strategy.
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        bl, br = st.columns(2, gap="large")

        with bl:
            st.markdown('<div class="section-title">BRRRR Flow</div>', unsafe_allow_html=True)
            steps = [
                ("Purchase Price",      fmt_usd(b.arv - b.equity_captured),              ""),
                ("+ Rehab Costs",       fmt_usd(rehab_costs),                            ""),
                ("= Total All-In",      fmt_usd(purchase_price + rehab_costs),           "highlight"),
                ("After Repair Value",  fmt_usd(b.arv),                                  "positive"),
                ("Refi Loan (75% LTV)", fmt_usd(b.refi_loan_amount),                     ""),
                ("− Refi Closing",      f"({fmt_usd(b.refi_closing_costs)})",            ""),
                ("Cash Returned",       fmt_usd(b.cash_out_at_refi),                     "positive"),
                ("Cash Left In Deal",   fmt_usd(b.cash_left_in_deal),                    "highlight"),
                ("Equity Captured",     fmt_usd(b.equity_captured),                      "positive"),
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
                ("Refi loan amount",      fmt_usd(b.refi_loan_amount)),
                ("New monthly payment",   fmt_usd(b.refi_monthly_payment)),
                ("Post-refi CF / mo",     fmt_usd(b.post_refi_monthly_cf, sign=True)),
                ("Post-refi CF / yr",     fmt_usd(b.post_refi_monthly_cf * 12)),
                ("Cash-on-cash (post)",   coc_label),
                ("Infinite returns",      "✅ Yes" if b.infinite_returns else "✗ No"),
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
    simple_kpi(sc1, "STR Monthly Revenue", fmt_usd(metrics.str_monthly_revenue))
    simple_kpi(sc2, "STR Annual Revenue",  fmt_usd(metrics.str_annual_revenue))
    cf_col  = GREEN if metrics.str_monthly_cash_flow > 0 else RED
    simple_kpi(sc3, "STR Monthly CF",      fmt_usd(metrics.str_monthly_cash_flow, sign=True), cf_col)
    coc_col = GREEN if metrics.str_coc_return >= 8 else GOLD
    simple_kpi(sc4, "STR CoC Return",      fmt_pct(metrics.str_coc_return), coc_col)

    st.markdown('<div class="section-title" style="margin-top:24px">LTR vs STR Comparison</div>', unsafe_allow_html=True)

    # Visual comparison bars
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="LTR", x=["Revenue", "Cash Flow", "Annual CF"],
        y=[metrics.gross_monthly_income, max(metrics.monthly_cash_flow,0), max(metrics.annual_cash_flow,0)],
        marker_color=BLUE, marker_line=dict(width=0)))
    fig_comp.add_trace(go.Bar(name="STR", x=["Revenue", "Cash Flow", "Annual CF"],
        y=[metrics.str_monthly_revenue, max(metrics.str_monthly_cash_flow,0), max(metrics.str_monthly_cash_flow*12,0)],
        marker_color=GOLD, marker_line=dict(width=0)))
    apply_theme(fig_comp, height=300, barmode="group",
    yaxis=dict(gridcolor="rgba(17,40,30,0.08)", tickprefix="$"))
    st.plotly_chart(fig_comp, use_container_width=True, key="chart_str_comparison")

    # Occupancy sensitivity
    st.markdown('<div class="section-title">Occupancy Sensitivity</div>', unsafe_allow_html=True)
    occ_range = [i/100 for i in range(30, 100, 5)]
    sens = []
    for occ in occ_range:
        tmp = DealAnalyzer(dc_replace(inputs, str_occupancy_rate=occ)).analyze()
        sens.append({"occ": occ*100, "rev": tmp.str_monthly_revenue, "cf": tmp.str_monthly_cash_flow})

    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(x=[s["occ"] for s in sens], y=[s["rev"] for s in sens],
            name="STR Revenue", line=dict(color=GOLD, width=2)))
    fig_s.add_trace(go.Scatter(x=[s["occ"] for s in sens], y=[s["cf"] for s in sens],
            name="STR Cash Flow", line=dict(color=GREEN, width=2)))
    fig_s.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.4)
    fig_s.add_vline(x=str_occ*100, line_dash="dot", line_color=GOLD, opacity=0.5,
            annotation_text=f"Current {str_occ*100:.0f}%", annotation_font_color=GOLD)
    apply_theme(fig_s, height=320,
        xaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Occupancy (%)", ticksuffix="%"),
        yaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="$/month",        tickprefix="$"))
    st.plotly_chart(fig_s, use_container_width=True, key="chart_str_sensitivity")

# ───────────────────────────────
# TAB: Rent Comps
# ───────────────────────────────
with tab_comps:
    cc1, cc2 = st.columns([3, 1], gap="large")
    with cc1:
        st.markdown(
            f'<div class="section-title" style="display:inline-flex;align-items:center;gap:8px">'
            f'Rent Comparables'
            f'<img src="{logo_url("rentcast.io", 24)}" width="18" height="18"'
            f'     style="border-radius:4px;opacity:.65;object-fit:contain"'
            f'     onerror="this.style.display=\'none\'">'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cc2:
        comp_beds = st.number_input("Beds filter", value=3, min_value=1, max_value=6, step=1)

    fetch_btn = st.button("🔍  Fetch Live Comps from RentCast")

    if fetch_btn:
        rc_key = get_secret("RENTCAST_API_KEY")
        if not rc_key:
            st.markdown("""
            <div class="info-banner">
                âš ï¸ Add <code>RENTCAST_API_KEY</code> to <code>.streamlit/secrets.toml</code> to fetch live comps.
            </div>""", unsafe_allow_html=True)
        else:
            with st.spinner("Fetching from RentCast..."):
                rc = RentCastClient(rc_key)
                fa = f"{address}, {city_st}"
                est   = rc.rent_estimate(address=fa, bedrooms=comp_beds)
                comps = rc.rent_comps(address=fa, bedrooms=comp_beds, limit=10)

            if est:
                em1, em2, em3 = st.columns(3)
                simple_kpi(em1, "Rent Low",    fmt_usd(est['rent_low'])    if est['rent_low']    else "N/A", GREEN, "1.2rem")
                simple_kpi(em2, "Rent Median", fmt_usd(est['rent_median']) if est['rent_median'] else "N/A", GREEN, "1.2rem")
                simple_kpi(em3, "Rent High",   fmt_usd(est['rent_high'])   if est['rent_high']   else "N/A", GREEN, "1.2rem")

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
    <div style="background:#ffffff;border:1px solid rgba(12,40,28,0.10);border-radius:14px;
         overflow:hidden;margin-top:8px;box-shadow:0 1px 3px rgba(12,40,28,0.05)">
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
        xaxis=dict(gridcolor="rgba(17,40,30,0.08)", tickangle=-20),
        yaxis=dict(gridcolor="rgba(17,40,30,0.08)", tickprefix="$"))
        st.plotly_chart(fig_rc, use_container_width=True, key="chart_rent_comps")

        pct_diff = ((monthly_rent - avg_rent) / avg_rent) * 100
        if pct_diff > 5:
            st.markdown(f'<div class="info-banner">âš ï¸ Your rent is <strong>{pct_diff:.1f}% above</strong> the comp average of ${avg_rent:,.0f}. Consider stress-testing at the lower comp rent.</div>', unsafe_allow_html=True)
        elif pct_diff < -5:
            st.markdown(f'<div class="success-banner">âœ… Your rent is <strong>{abs(pct_diff):.1f}% below</strong> comp average — potential upside of ${avg_rent - monthly_rent:,.0f}/mo.</div>', unsafe_allow_html=True)

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
        total_interest = adf["interest"].sum()
        simple_kpi(am1, "Loan Amount",    fmt_usd(metrics.loan_amount),                      font_size="1.1rem")
        simple_kpi(am2, "Total Interest", fmt_usd(total_interest),                            font_size="1.1rem")
        simple_kpi(am3, "Total Cost",     fmt_usd(metrics.loan_amount + total_interest),      font_size="1.1rem")

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
    xaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Year", dtick=5),
    yaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="$/Year", tickprefix="$"),
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
    rate_sens  = []
    for r in rate_range:
        tmp = DealAnalyzer(dc_replace(inputs, loan_interest_rate=r)).analyze()
        rate_sens.append({"rate": r*100, "cf": tmp.monthly_cash_flow, "dscr": tmp.dscr})

    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(
        x=[s["rate"] for s in rate_sens], y=[s["cf"] for s in rate_sens],
        name="Monthly CF", line=dict(color=GOLD, width=2), fill="tozeroy",
        fillcolor="rgba(22,163,74,0.06)"))
    fig_rate.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.5)
    fig_rate.add_vline(x=interest_rate*100, line_dash="dot", line_color=BLUE, opacity=0.6,
        annotation_text=f"Your rate {interest_rate*100:.2f}%",
        annotation_font_color=BLUE)
    apply_theme(fig_rate, height=320,
    xaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Interest Rate (%)", ticksuffix="%"),
    yaxis=dict(gridcolor="rgba(17,40,30,0.08)", title="Monthly CF ($)",    tickprefix="$"))
    st.plotly_chart(fig_rate, use_container_width=True, key="chart_rate_sensitivity")

    st.markdown("""
    <div class="info-banner">
        <strong>Reading the macro environment</strong><br>
        Higher Fed Funds ↑ elevated mortgage rates ↑ lower cash flow.
        Rising CPI ↑ inflation erodes fixed mortgage costs but raises expenses.
        Low unemployment ↑ strong rental demand ↑ lower vacancy risk.
        Rising HPI ↑ property appreciates ↑ stronger BRRRR equity.
    </div>""", unsafe_allow_html=True)

# ───────────────────────────────
# TAB: Local Listings
# ───────────────────────────────
with tab_listings:
    st.markdown('<div class="section-title">Listings Near This Property</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:12.5px;color:rgba(17,40,30,0.45);margin-bottom:16px">'
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
            spinner_label = "Fetching rental listingsâ€¦" if listing_type == "Rental" else "Fetching for-sale listingsâ€¦"
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

                # Build photo carousel with inline styles (avoids Streamlit sanitizer
                # stripping JS event handlers and breaking the HTML block)
                _img_s = (
                    "min-width:100%;height:200px;object-fit:cover;"
                    "scroll-snap-align:start;flex-shrink:0;"
                    "display:block;background:#eef3f0;"
                )
                _reel_s = (
                    "display:flex;overflow-x:auto;"
                    "scroll-snap-type:x mandatory;"
                    "-webkit-overflow-scrolling:touch;"
                    "scrollbar-width:none;height:200px;"
                    "border-radius:14px 14px 0 0;"
                    "position:relative;"
                )
                photo_imgs = "".join(
                    f'<img src="{p}" alt="" loading="lazy" style="{_img_s}">'
                    for p in photo_urls
                )
                n_photos = len(photo_urls)
                _badge_s = (
                    "position:absolute;bottom:8px;right:8px;"
                    "background:rgba(0,0,0,0.62);color:rgba(255,255,255,0.82);"
                    "font-size:9.5px;font-family:monospace;"
                    "padding:2px 8px;border-radius:100px;pointer-events:none;"
                )
                count_badge = (
                    f'<div style="{_badge_s}">{n_photos} photos</div>'
                    if n_photos > 1 else ""
                )

                card_html = f"""{link_open}
<div class="listing-card">
<div style="{_reel_s}">{photo_imgs}{count_badge}</div>
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
{link_close}"""
                col.markdown(card_html, unsafe_allow_html=True)

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin-top:14px">'
            f'<span style="font-size:10.5px;color:rgba(17,40,30,0.25);'
            f'font-family:Space Mono,monospace">'
            f'{len(listings_to_show)} listings · ZIP {listing_zip or zip_code} · '
            f'{"For Sale" if is_sale_tab else "Rental"} · via</span>'
            f'<img src="{logo_url("rentcast.io", 24)}" width="14" height="14"'
            f'     style="border-radius:3px;opacity:.5;object-fit:contain"'
            f'     onerror="this.style.display=\'none\'">'
            f'<span style="font-size:10.5px;color:rgba(17,40,30,0.25);'
            f'font-family:Space Mono,monospace">'
            f'RentCast{"" if rc_key_listings else " (demo)"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
_data_sources = [
    ("rentcast.io",           "RentCast"),
    ("zillow.com",            "Zillow"),
    ("fred.stlouisfed.org",   "FRED"),
    ("attomdata.com",         "ATTOM"),
    ("census.gov",            "Census"),
    ("google.com",            "Google Maps"),
]
_logo_chips = "".join(
    f"""<a href="https://{domain}" target="_blank" rel="noopener"
          style="display:inline-flex;align-items:center;gap:5px;
                 padding:4px 9px 4px 6px;border-radius:100px;
                 background:rgba(17,40,30,0.04);
                 border:1px solid rgba(12,40,28,0.10);
                 text-decoration:none;transition:border-color .15s">
         <img src="{logo_url(domain, 20)}" width="16" height="16"
              style="border-radius:3px;object-fit:contain;opacity:.75"
              onerror="this.style.display='none'">
         <span style="font-family:'Space Mono',monospace;font-size:9.5px;
               color:rgba(17,40,30,0.3)">{label}</span>
       </a>"""
    for domain, label in _data_sources
)
st.markdown(f"""
<div style="margin-top:48px;padding:18px 36px;border-top:1px solid rgba(12,40,28,0.08);
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
    <span style="font-family:'Space Mono',monospace;font-size:10px;color:rgba(17,40,30,0.25);
          text-transform:uppercase;letter-spacing:0.1em">
        DealSight · Not financial advice
    </span>
    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
        <span style="font-family:'Space Mono',monospace;font-size:9px;
              color:rgba(17,40,30,0.18);margin-right:2px">Powered by</span>
        {_logo_chips}
    </div>
</div>
""", unsafe_allow_html=True)
