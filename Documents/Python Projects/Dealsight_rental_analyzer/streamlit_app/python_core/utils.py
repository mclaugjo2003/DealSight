"""
Shared UI helpers: formatters, KPI card renderer, Plotly theme.
Imported by app.py; no imports from the rest of python_core.
"""

import plotly.graph_objects as go
from typing import Optional

# ─────────────────────────────────────────────
# Color palette — white · black · green (money)
# ─────────────────────────────────────────────
GOLD   = "#d97706"   # amber — "below target / caution" series & accents
GREEN  = "#16a34a"   # money green — primary / positive
RED    = "#dc2626"   # loss / negative
BLUE   = "#0d9488"   # teal — reference lines, secondary series
PURPLE = "#15803d"   # dark green — tertiary accent

INK    = "#0b1410"   # near-black primary text
INK_SEC = "rgba(17,40,30,0.66)"
INK_MUTED = "rgba(17,40,30,0.42)"
SURFACE = "#ffffff"
SURFACE_2 = "#f4f7f5"

# Deal-grade palette kept legible on white backgrounds
GRADE_COLORS: dict[str, tuple[str, str, str]] = {
    "A": ("#16a34a", "rgba(22,163,74,0.12)",  "rgba(22,163,74,0.30)"),
    "B": ("#65a30d", "rgba(101,163,13,0.12)", "rgba(101,163,13,0.30)"),
    "C": ("#d97706", "rgba(217,119,6,0.12)",  "rgba(217,119,6,0.30)"),
    "F": ("#dc2626", "rgba(220,38,38,0.12)",  "rgba(220,38,38,0.30)"),
}
_GOLD_FALLBACK = (GREEN, "rgba(22,163,74,0.12)", "rgba(22,163,74,0.30)")


# ─────────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────────
def fmt_usd(val: float, sign: bool = False) -> str:
    return f"${val:+,.0f}" if sign else f"${val:,.0f}"


def fmt_pct(val: float, decimals: int = 1) -> str:
    return f"{val:.{decimals}f}%"


def fmt_label(key: str) -> str:
    return key.replace("_", " ").title()


# ─────────────────────────────────────────────
# KPI card HTML (graded — used in main KPI strip)
# ─────────────────────────────────────────────
def kpi_card(label: str, value: str, grade: str, desc: str, sub: str = "") -> str:
    val_color, badge_bg, glow = GRADE_COLORS.get(grade, _GOLD_FALLBACK)
    return f"""
    <div style="background:{SURFACE};padding:24px 20px;position:relative;overflow:hidden;
         border-right:1px solid rgba(12,40,28,0.08);flex:1;transition:background 0.2s;">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
             background:linear-gradient(90deg,transparent,{val_color},transparent)"></div>
        <div style="font-size:9px;font-family:'Space Mono',monospace;
             color:{INK_MUTED};text-transform:uppercase;
             letter-spacing:0.14em;margin-bottom:12px">{label}</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.8rem;
             font-weight:700;line-height:1;margin-bottom:10px;
             color:{val_color}">{value}</div>
        <div style="display:inline-flex;align-items:center;gap:5px;
             font-size:10px;font-family:'Space Mono',monospace;
             padding:3px 9px;border-radius:100px;
             background:{badge_bg};color:{val_color};
             border:1px solid {val_color}55">
            {grade} · {desc[:28]}
        </div>
        {"<div style='font-size:10px;color:" + INK_MUTED + ";font-family:Space Mono,monospace;margin-top:8px'>" + sub + "</div>" if sub else ""}
    </div>"""


# ─────────────────────────────────────────────
# Simple KPI card (no grade badge — used in tabs)
# ─────────────────────────────────────────────
def simple_kpi(col, label: str, val: str, color: str = GREEN,
               font_size: str = "1.5rem") -> None:
    col.markdown(f"""
    <div style="background:{SURFACE};border:1px solid rgba(12,40,28,0.10);
         border-radius:12px;padding:20px 16px;text-align:center;
         position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(12,40,28,0.05);">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
             background:linear-gradient(90deg,transparent,{color},transparent)"></div>
        <div style="font-size:9px;font-family:'Space Mono',monospace;
             color:{INK_MUTED};text-transform:uppercase;
             letter-spacing:0.12em;margin-bottom:10px">{label}</div>
        <div style="font-family:'Space Mono',monospace;font-size:{font_size};
             font-weight:700;color:{color}">{val}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Plotly dark theme
# ─────────────────────────────────────────────
def apply_theme(fig: go.Figure, height: int = 380, **kwargs) -> go.Figure:
    axis_defaults = dict(
        gridcolor="rgba(17,40,30,0.08)",
        linecolor="rgba(17,40,30,0.15)",
        zeroline=False,
    )
    layout: dict = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "#ffffff",
        "font":          dict(family="Space Mono, monospace",
                              color="rgba(17,40,30,0.62)", size=11),
        "legend":        dict(orientation="h", y=1.08, font=dict(size=10)),
        "margin":        dict(t=40, b=40, l=12, r=12),
        "height":        height,
        "xaxis":         axis_defaults,
        "yaxis":         axis_defaults,
    }
    layout.update(kwargs)
    fig.update_layout(**layout)
    return fig
