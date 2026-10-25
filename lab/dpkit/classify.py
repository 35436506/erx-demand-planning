"""Phân nhóm danh mục: ABC (giá trị), XYZ (biến động), hình dạng nhu cầu, và ma trận chọn phương pháp."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .intermittent import adi_cv2, sbc_class


def abc(values: pd.Series, a: float = 0.80, b: float = 0.95) -> pd.Series:
    """A = nhóm chiếm 80% giá trị lũy kế đầu tiên, B đến 95%, còn lại C."""
    v = values.sort_values(ascending=False)
    cum = v.cumsum() / v.sum()
    prev = cum.shift(fill_value=0)
    cls = np.where(prev < a, "A", np.where(prev < b, "B", "C"))
    return pd.Series(cls, index=v.index).reindex(values.index)


def cv(y) -> float:
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    return float(y.std(ddof=1) / y.mean()) if y.mean() else np.nan


def xyz(cv_value: float, x: float = 0.15, y: float = 0.35) -> str:
    """X: CV ≤ 0,15 ; Y: ≤ 0,35 ; Z: > 0,35 (dữ liệu THÁNG, cấp SKU — ngưỡng tùy ngành và cấp dữ liệu;
    dữ liệu tuần thường dùng 0,5/1,0). Nên tính CV trên chuỗi ĐÃ khử mùa vụ & khuyến mãi."""
    if np.isnan(cv_value):
        return "Z"
    return "X" if cv_value <= x else ("Y" if cv_value <= y else "Z")


def slope_pct(y) -> float:
    """Độ dốc xu hướng tuyến tính, % mức trung bình mỗi tháng (Excel: =SLOPE(y,t)/AVERAGE(y))."""
    y = np.asarray(y, dtype=float)
    t = np.arange(len(y))
    ok = ~np.isnan(y)
    if ok.sum() < 3:
        return np.nan
    b = np.polyfit(t[ok], y[ok], 1)[0]
    return float(b / np.nanmean(y) * 100)


METHOD_MATRIX = {
    "AX": "Thống kê tự động (ETS/Holt-Winters), rà soát theo ngoại lệ",
    "AY": "Thống kê + rà soát hằng tháng với Sales/Marketing",
    "AZ": "Rà soát kỹ: hồi quy khuyến mãi/sự kiện + phán đoán có kiểm chứng (FVA)",
    "BX": "Thống kê tự động",
    "BY": "Thống kê tự động, rà soát theo ngoại lệ",
    "BZ": "Phương pháp đơn giản bền vững (SES/MA) + tồn kho an toàn cao hơn",
    "CX": "Tự động, chu kỳ rà soát thưa",
    "CY": "Phương pháp đơn giản (MA/SES)",
    "CZ": "Croston/SBA hoặc sản xuất theo đơn (MTO); không đầu tư thời gian dự báo chi tiết",
}


def deseasonalized_cv(s: pd.Series, last_n: int = 12) -> float:
    """CV sau khi chia cho chỉ số mùa vụ (tính trên toàn bộ lịch sử) — tránh xếp nhầm hàng mùa vụ vào nhóm Z."""
    from .seasonal import seasonal_indices
    y = s.dropna()
    if len(y) < 30 or (y <= 0).mean() > 0.3:
        return cv(y.iloc[-last_n:].to_numpy(dtype=float))
    idx = seasonal_indices(y.values, y.index.month)
    ds = y.values / np.array([idx[m] for m in y.index.month])
    return cv(ds[-last_n:])


def item_portfolio(series: dict[str, pd.Series], value_per_unit: dict[str, float], last_n: int = 12) -> pd.DataFrame:
    """Phân nhóm ở cấp SKU (cộng hai kênh) — cấp quyết định phân bổ thời gian của planner."""
    items = sorted({k.split("|")[0] for k in series})
    agg = {}
    for it in items:
        parts = [v for k, v in series.items() if k.split("|")[0] == it]
        agg[f"{it}|ALL"] = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    df = portfolio_table(agg, value_per_unit, last_n)
    df["CV_khu_mua_vu"] = [deseasonalized_cv(agg[k], last_n) for k in df.series]
    df["XYZ_khu_mua_vu"] = df.CV_khu_mua_vu.map(xyz)
    df["segment_adj"] = df.ABC + df.XYZ_khu_mua_vu
    return df


def portfolio_table(series: dict[str, pd.Series], value_per_unit: dict[str, float], last_n: int = 12) -> pd.DataFrame:
    rows = []
    for key, s in series.items():
        item = key.split("|")[0]
        y = s.iloc[-last_n:].to_numpy(dtype=float)
        adi, cv2 = adi_cv2(y)
        rows.append({"series": key, "item": item, "channel": key.split("|")[1],
                     "volume_12m": np.nansum(y), "value_12m_trieu": np.nansum(y) * value_per_unit.get(item, 0) / 1000,
                     "CV": cv(y), "pct_zero": float(np.mean(y[~np.isnan(y)] == 0) * 100), "ADI": adi, "CV2": cv2,
                     "SBC": sbc_class(adi, cv2), "slope_pct_month": slope_pct(y)})
    df = pd.DataFrame(rows)
    df["ABC"] = abc(df.set_index("series")["value_12m_trieu"]).values
    df["XYZ"] = df.CV.map(xyz)
    df["segment"] = df.ABC + df.XYZ
    df["method"] = df.segment.map(METHOD_MATRIX)
    df.loc[df.SBC.str.startswith(("Intermittent", "Lumpy")), "method"] = "Croston / SBA / TSB (nhu cầu rời rạc)"
    return df.sort_values("value_12m_trieu", ascending=False).reset_index(drop=True)
