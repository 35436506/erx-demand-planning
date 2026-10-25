"""Mùa vụ: chỉ số mùa vụ (ratio-to-moving-average), khử mùa vụ, và hiệu ứng Tết dịch tháng."""
from __future__ import annotations

import numpy as np
import pandas as pd


def centered_ma(y, m: int = 12) -> np.ndarray:
    """Trung bình trượt trung tâm 2×12 (Excel: =(AVERAGE(B2:B13)+AVERAGE(B3:B14))/2)."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    out = np.full(n, np.nan)
    half = m // 2
    for t in range(half, n - half):
        if m % 2 == 0:
            out[t] = (y[t - half:t + half].mean() + y[t - half + 1:t + half + 1].mean()) / 2
        else:
            out[t] = y[t - half:t + half + 1].mean()
    return out


def seasonal_indices(y, months, m: int = 12, model: str = "mul") -> pd.Series:
    """Chỉ số mùa vụ chuẩn hóa theo tháng (1..12). Nhân: TB = 1; cộng: tổng = 0."""
    y = np.asarray(y, dtype=float)
    cma = centered_ma(y, m)
    ratio = y / cma if model == "mul" else y - cma
    df = pd.DataFrame({"month": np.asarray(months), "r": ratio}).dropna()
    raw = df.groupby("month").r.mean().reindex(range(1, m + 1))
    if model == "mul":
        return raw / raw.mean()
    return raw - raw.mean()


def deseasonalize(y, months, idx: pd.Series, model: str = "mul") -> np.ndarray:
    s = np.array([idx[m] for m in months])
    y = np.asarray(y, dtype=float)
    return y / s if model == "mul" else y - s


def seasonal_strength(y, months) -> float:
    """Độ mạnh mùa vụ đơn giản = max/min của chỉ số mùa vụ."""
    idx = seasonal_indices(y, months)
    return float(idx.max() / idx.min())


def tet_regressors(periods, calendar: pd.DataFrame) -> pd.DataFrame:
    cal = calendar.set_index("month")
    keys = [str(p) for p in periods]
    return cal.loc[keys, ["tet_pre_share", "tet_post_share"]].reset_index(drop=True)


def tet_adjusted_indices(y, periods, calendar: pd.DataFrame) -> dict:
    """Tách hiệu ứng Tết khỏi chỉ số tháng 1/2 bằng hồi quy log(y) ~ trend + tháng + tet_pre + tet_post.
    Trả về hệ số Tết (% tăng khi toàn bộ cửa sổ 35 ngày rơi vào tháng) và chỉ số tháng đã khử Tết."""
    y = np.asarray(y, dtype=float)
    per = pd.PeriodIndex(periods, freq="M")
    X = pd.DataFrame({"const": 1.0, "t": np.arange(len(y))})
    for k in range(2, 13):
        X[f"m{k}"] = (per.month == k).astype(float)
    tr = tet_regressors(per, calendar)
    X["tet_pre"] = tr.tet_pre_share.values
    X["tet_post"] = tr.tet_post_share.values
    ok = (y > 0) & ~np.isnan(y)
    beta, *_ = np.linalg.lstsq(X.values[ok], np.log(y[ok]), rcond=None)
    b = dict(zip(X.columns, beta))
    month_idx = np.exp([0.0] + [b[f"m{k}"] for k in range(2, 13)])
    month_idx = month_idx / month_idx.mean()
    return {"tet_uplift_pct": (np.exp(b["tet_pre"]) - 1) * 100, "post_tet_pct": (np.exp(b["tet_post"]) - 1) * 100,
            "trend_pct_month": (np.exp(b["t"]) - 1) * 100,
            "month_index_ex_tet": pd.Series(month_idx, index=range(1, 13)), "coef": b}


def tet_part_ratio(y: pd.Series, calendar: pd.DataFrame, years=(2024, 2025, 2026)) -> pd.DataFrame:
    """'Phần Tết' mỗi năm, tính bằng số tháng-thường: (T12+T1+T2 − 3×mức thường) / mức thường,
    với mức thường = TB tháng 3–9 cùng năm. y có PeriodIndex tháng."""
    rows = []
    for yr in years:
        keys = [pd.Period(k, "M") for k in (f"{yr-1}-12", f"{yr}-01", f"{yr}-02")]
        if not all(k in y.index for k in keys):
            continue
        win = float(sum(y[k] for k in keys))
        normal = float(y.loc[pd.Period(f"{yr}-03", "M"):pd.Period(f"{yr}-09", "M")].mean())
        if normal > 0:
            rows.append({"nam": yr, "T12_T1_T2": win, "muc_thuong": normal, "phan_Tet": (win - 3 * normal) / normal})
    return pd.DataFrame(rows)


def tet_reallocate(normal: float, R: float, calendar: pd.DataFrame, months, post_dip: float = 0.15) -> dict:
    """Dự báo T12–T2 = mức thường × (1 + R × tỷ trọng trước Tết) × (1 − post_dip × tỷ trọng sau Tết)."""
    c = calendar.set_index("month")
    return {m: normal * (1 + R * c.loc[m, "tet_pre_share"]) * (1 - post_dip * c.loc[m, "tet_post_share"]) for m in months}
