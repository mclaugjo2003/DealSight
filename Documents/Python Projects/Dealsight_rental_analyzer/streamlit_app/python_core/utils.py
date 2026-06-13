"""
Shared UI helpers: formatters, KPI card renderer, Plotly theme.
Imported by app.py; no imports from the rest of python_core.
"""

import plotly.graph_objects as go
from typing import Optional

# ─────────────────────────────────────────────
# Color palette
# ─────────────────────────────────────────────
GOLD   = "#d4a843"
GREEN  = "#34d399"
RED    = "#f87171"
BLUE   = "#4f72ff"
PURPLE = "#8b5cf6"

GRADE_COLORS: dict[str, tuple[str, str, str]] = {
    "A": ("#34d399", "rgba(52,211,153,0.1)",  "rgba(52,211,153,0.3)"),
    "B": ("#a3e635", "rgba(163,230,53,0.1)",  "rgba(163,230,53,0.3)"),
    "C": ("#fbbf24", "rgba(251,191,36,0.1)",  "rgba(251,191,36,0.3)"),
    "F": ("#f87171", "rgba(248,113,113,0.1)", "rgba(248,113,113,0.3)"),
}
_GOLD_FALLBACK = (GOLD, "rgba(212,168,67,0.1)", "rgba(212,168,67,0.3)")


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


# ─────────────────────────────────────────────
# Simple KPI card (no grade badge — used in tabs)
# ─────────────────────────────────────────────
def simple_kpi(col, label: str, val: str, color: str = GOLD,
               font_size: str = "1.5rem") -> None:
    col.markdown(f"""
    <div style="background:#0b0b1e;border:1px solid rgba(255,255,255,0.07);
         border-radius:12px;padding:20px 16px;text-align:center;
         position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;
             background:linear-gradient(90deg,transparent,{color}55,transparent)"></div>
        <div style="font-size:9px;font-family:'Space Mono',monospace;
             color:rgba(205,200,230,0.35);text-transform:uppercase;
             letter-spacing:0.12em;margin-bottom:10px">{label}</div>
        <div style="font-family:'Space Mono',monospace;font-size:{font_size};
             font-weight:400;color:{color};text-shadow:0 0 18px {color}44">{val}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Plotly dark theme
# ─────────────────────────────────────────────
def apply_theme(fig: go.Figure, height: int = 380, **kwargs) -> go.Figure:
    axis_defaults = dict(
        gridcolor="rgba(255,255,255,0.04)",
        linecolor="rgba(255,255,255,0.08)",
        zeroline=False,
    )
    layout: dict = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "#0b0b1e",
        "font":          dict(family="Space Mono, monospace",
                              color="rgba(205,200,230,0.5)", size=11),
        "legend":        dict(orientation="h", y=1.08, font=dict(size=10)),
        "margin":        dict(t=40, b=40, l=12, r=12),
        "height":        height,
        "xaxis":         axis_defaults,
        "yaxis":         axis_defaults,
    }
    layout.update(kwargs)
    fig.update_layout(**layout)
    return fig
