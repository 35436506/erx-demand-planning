"""Đánh giá ngoài mẫu: train/test, dự báo cuốn chiếu (rolling origin) và độ chính xác theo độ trễ (lag)."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from . import baseline, metrics, smoothing

ForecastFn = Callable[[np.ndarray, int], np.ndarray]


def method_library(m: int = 12) -> dict[str, ForecastFn]:
    return {
        "Naive": lambda y, h: baseline.naive(y, h),
        "Seasonal Naive": lambda y, h: baseline.seasonal_naive(y, h, m),
        "MA(3)": lambda y, h: baseline.moving_average(y, h, 3),
        "SES": lambda y, h: smoothing.ses(y, h).forecast,
        "Holt": lambda y, h: smoothing.holt(y, h).forecast,
        "Holt tắt dần": lambda y, h: smoothing.holt(y, h, damped=True).forecast,
        "Holt-Winters nhân": lambda y, h: smoothing.holt_winters(y, h, m, "mul").forecast,
        "Holt-Winters cộng": lambda y, h: smoothing.holt_winters(y, h, m, "add").forecast,
    }


def train_test(y, n_test: int, methods: dict[str, ForecastFn] | None = None, m: int = 12) -> pd.DataFrame:
    """Cắt dữ liệu TRƯỚC, fit trên train, chấm trên test. Trả về bảng sai số mỗi phương pháp."""
    y = np.asarray(y, dtype=float)
    tr, te = y[:-n_test], y[-n_test:]
    methods = methods or method_library(m)
    rows, fcs = [], {}
    for name, fn in methods.items():
        try:
            f = fn(tr, n_test)
        except ValueError:
            continue
        fcs[name] = f
        rows.append({"method": name, **metrics.summary(te, f, tr, m=1)})
    out = pd.DataFrame(rows).sort_values("WMAPE%").reset_index(drop=True)
    out.attrs["forecasts"] = fcs
    return out


def rolling_origin(y, first_origin: int, horizon: int, fn: ForecastFn) -> pd.DataFrame:
    """Dự báo cuốn chiếu: tại mỗi origin chỉ dùng dữ liệu đến origin, dự báo horizon kỳ.
    Trả về bảng dài: origin, target, lag, forecast, actual."""
    y = np.asarray(y, dtype=float)
    rows = []
    for o in range(first_origin, len(y)):
        f = fn(y[:o], horizon)
        for lag in range(1, horizon + 1):
            tgt = o + lag - 1
            if tgt < len(y):
                rows.append({"origin": o, "target": tgt, "lag": lag, "forecast": f[lag - 1], "actual": y[tgt]})
    return pd.DataFrame(rows)


def accuracy_by_lag(ro: pd.DataFrame) -> pd.DataFrame:
    return ro.groupby("lag").apply(lambda d: pd.Series({
        "WMAPE%": metrics.wmape(d.actual, d.forecast), "Bias%": metrics.bias_pct(d.actual, d.forecast) * 100,
        "n": len(d)}), include_groups=False).reset_index()


def best_fit(y, n_test: int = 6, m: int = 12, methods=None) -> tuple[str, pd.DataFrame]:
    """'Best-fit' kiểu phần mềm APS — nhưng chọn bằng sai số NGOÀI MẪU, không phải trong mẫu."""
    tbl = train_test(y, n_test, methods, m)
    return tbl.iloc[0]["method"], tbl
