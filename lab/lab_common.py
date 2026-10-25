"""Dùng chung cho mọi trang của Forecasting Lab: dữ liệu (cache), giao diện, biểu đồ."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dpkit import data as dpdata  # noqa: E402

DATA_DIR = HERE / "data"
INK, MUTED, GRID, BRAND = "#1F2421", "#76777B", "#E6E8E6", "#01AE42"
CAT = ["#008A3A", "#2563C9", "#D9720B", "#8E44AD", "#C2185B"]
TEST_MONTHS = 6

SESSIONS = {
    1: "Dự báo để làm gì & phân cấp",
    2: "Hiểu và làm sạch dữ liệu",
    3: "Dự báo đầu tiên & đo sai số",
    4: "Exponential Smoothing & cuốn chiếu",
    5: "Mùa vụ & hiệu ứng Tết",
    6: "Hồi quy, giá & khuyến mãi",
    7: "Chọn mô hình theo danh mục",
    8: "Demand Review & FVA",
    9: "Tồn kho, cảnh báo sớm & S&OP",
    10: "Capstone workbench",
}


def page(session: int | None, title: str, intro: str = ""):
    st.markdown(
        """<style>
        .block-container{padding-top:1.4rem;max-width:1250px}
        h1,h2,h3{color:#1F2421}
        .erx-tag{display:inline-block;background:#EAF7EF;color:#00703C;border-radius:14px;padding:2px 10px;font-size:0.8rem;font-weight:600}
        .erx-note{background:#F2F7F3;border-left:0;border-radius:8px;padding:10px 14px;color:#1F2421;font-size:0.92rem}
        div[data-testid="stMetricValue"]{color:#1F2421}
        </style>""", unsafe_allow_html=True)
    with st.sidebar:
        logo = HERE / "assets" / "ERX_Logo_color.png"
        if logo.exists():
            st.image(str(logo), width=150)
        st.caption("Demand Planning & Forecasting in Practice · Forecasting Lab")
        st.caption("Dữ liệu: Mekong Bloom Foods (công ty giả định)")
        st.caption("Giảng viên: Thư Nguyễn · thu.minh090997@gmail.com")
    tag = f"Buổi {session} · " if session else ""
    st.markdown(f'<span class="erx-tag">{tag}ERX Forecasting Lab</span>', unsafe_allow_html=True)
    st.title(title)
    if intro:
        st.markdown(f'<div class="erx-note">{intro}</div>', unsafe_allow_html=True)
        st.write("")


@st.cache_data(show_spinner=False)
def load_all() -> dict[str, pd.DataFrame]:
    return dpdata.load(DATA_DIR)


def series_keys(include_discontinued: bool = False) -> list[str]:
    dc = load_all()["demand_clean"]
    keys = (dc["item"] + "|" + dc["channel"]).drop_duplicates().tolist()
    return [k for k in keys if include_discontinued or not k.startswith("N06")]


def label(key: str) -> str:
    m = load_all()["sku_master"].drop_duplicates("planning_item").set_index("planning_item")
    it, ch = key.split("|")
    name = m.loc[it, "name"].replace(" (chai PET – mã cũ)", "") if it in m.index else it
    return f"{it} · {name} · {ch}"


def clean_series(key: str, col: str = "demand") -> pd.Series:
    dc = load_all()["demand_clean"]
    it, ch = key.split("|")
    s = dc[(dc["item"] == it) & (dc["channel"] == ch)].set_index("month")[col].dropna()
    s.index = pd.PeriodIndex(s.index, freq="M")
    return s


def raw_series(key: str, col: str = "shipments") -> pd.Series:
    D = load_all()
    it, ch = key.split("|")
    return dpdata.series(D["sales_history"], it, ch, col, D["sku_master"])


def pick_series(label_txt="Chọn chuỗi SKU × kênh", default="N01|GT", key=None, options=None) -> str:
    opts = options or series_keys()
    idx = opts.index(default) if default in opts else 0
    return st.selectbox(label_txt, opts, index=idx, format_func=label, key=key)


def fig_base(title: str = "", height: int = 380, ytitle: str = "") -> go.Figure:
    f = go.Figure()
    f.update_layout(template="plotly_white", height=height, title=dict(text=title, font=dict(size=15, color=INK)),
                    margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified",
                    legend=dict(orientation="h", y=-0.18, font=dict(color=MUTED)),
                    font=dict(family="Be Vietnam Pro, Arial, sans-serif", color=INK),
                    yaxis=dict(title=ytitle, gridcolor=GRID, zeroline=False), xaxis=dict(gridcolor=GRID))
    return f


def add_line(f, x, y, name, color=INK, dash=None, width=2, mode="lines"):
    xs = list(x)
    if xs and not isinstance(xs[0], (int, float, np.integer, np.floating)):
        xs = [str(v) for v in xs]
    f.add_trace(go.Scatter(x=xs, y=y, name=name, mode=mode,
                           line=dict(color=color, width=width, dash=dash), marker=dict(size=7)))
    return f


def shade_test(f, x_all, n_test=TEST_MONTHS, label_txt="Test"):
    xs = [str(v) for v in x_all]
    f.add_vrect(x0=xs[-n_test], x1=xs[-1], fillcolor="#EAF7EF", opacity=0.7, line_width=0,
                annotation_text=label_txt, annotation_position="top left", annotation_font_color=MUTED)
    return f


def metric_table(rows: list[dict], extra_fmt: dict | None = None) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    fmt = {c: "{:.1f}" for c in df.columns if c.endswith("%")}
    fmt.update({c: "{:,.0f}" for c in ("ME", "MAE", "RMSE") if c in df.columns})
    fmt.update({"MASE": "{:.2f}"} if "MASE" in df.columns else {})
    fmt.update(extra_fmt or {})
    return df.style.format(fmt, na_rep="–")


def note(txt: str):
    st.markdown(f'<div class="erx-note">{txt}</div>', unsafe_allow_html=True)


def months_str(idx) -> list[str]:
    return [str(v) for v in idx]


def fmt_num(x, d=0):
    try:
        return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(x)


def np_float(x):
    return float(np.asarray(x, dtype=float))
