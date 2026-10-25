"""Thước đo sai số dự báo. Quy ước e = actual − forecast.

| Thước đo | Trả lời câu hỏi                                  | Excel tương đương |
|----------|--------------------------------------------------|-------------------|
| ME/Bias  | Dự báo có lệch về một phía không?                | =AVERAGE(e)       |
| MAE      | Sai trung bình bao nhiêu đơn vị?                 | =AVERAGE(ABS(e))  |
| RMSE     | Phạt nặng sai số lớn (dùng cho Safety Stock)     | =SQRT(SUMSQ(e)/n) |
| MAPE     | Sai trung bình bao nhiêu % (thiên lệch ở mã nhỏ) | =AVERAGE(ABS(e)/A)|
| WMAPE    | % sai số có trọng số sản lượng (= WAPE)          | =SUM(ABS(e))/SUM(A)|
| MASE     | Tốt hơn Naive bao nhiêu? (<1 là tốt hơn)         | MAE / MAE_naive   |
"""
from __future__ import annotations

import numpy as np


def _clean(a, f):
    a = np.asarray(a, dtype=float)
    f = np.asarray(f, dtype=float)
    m = ~(np.isnan(a) | np.isnan(f))
    return a[m], f[m]


def errors(actual, forecast) -> np.ndarray:
    a, f = _clean(actual, forecast)
    return a - f


def me(actual, forecast) -> float:
    return float(np.mean(errors(actual, forecast)))


def bias_pct(actual, forecast) -> float:
    """Bias % = Σ(F − A) / ΣA. Dương = dự báo CAO (over-forecast) — cách ngành hay báo cáo."""
    a, f = _clean(actual, forecast)
    return float((f - a).sum() / a.sum()) if a.sum() else np.nan


def mae(actual, forecast) -> float:
    return float(np.mean(np.abs(errors(actual, forecast))))


def mse(actual, forecast) -> float:
    return float(np.mean(errors(actual, forecast) ** 2))


def rmse(actual, forecast) -> float:
    return float(np.sqrt(mse(actual, forecast)))


def mape(actual, forecast) -> float:
    """MAPE (%); bỏ qua kỳ actual = 0 (không định nghĩa). Báo cáo số kỳ bị bỏ để minh bạch."""
    a, f = _clean(actual, forecast)
    m = a != 0
    if not m.any():
        return np.nan
    return float(np.mean(np.abs(a[m] - f[m]) / np.abs(a[m])) * 100)


def wmape(actual, forecast) -> float:
    """WMAPE = WAPE = Σ|e| / Σ|A| (%)."""
    a, f = _clean(actual, forecast)
    return float(np.abs(a - f).sum() / np.abs(a).sum() * 100) if np.abs(a).sum() else np.nan


def accuracy(actual, forecast) -> float:
    """Forecast Accuracy = max(0, 1 − WMAPE) — cách nhiều công ty báo cáo."""
    w = wmape(actual, forecast)
    return float(max(0.0, 100 - w))


def mase(actual, forecast, insample, m: int = 1) -> float:
    """MASE: MAE ngoài mẫu chia MAE của Naive (mùa vụ m) trong mẫu train."""
    ins = np.asarray(insample, dtype=float)
    ins = ins[~np.isnan(ins)]
    if len(ins) <= m:
        return np.nan
    scale = np.mean(np.abs(ins[m:] - ins[:-m]))
    return float(mae(actual, forecast) / scale) if scale else np.nan


def tracking_signal(actual, forecast) -> np.ndarray:
    """TS_t = Σe / MAD (lũy kế). |TS| > 4 là cảnh báo lệch có hệ thống."""
    e = errors(actual, forecast)
    cum = np.cumsum(e)
    mad = np.array([np.mean(np.abs(e[: i + 1])) for i in range(len(e))])
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(mad > 0, cum / mad, 0.0)


def summary(actual, forecast, insample=None, m: int = 1) -> dict:
    out = {"ME": me(actual, forecast), "Bias%": bias_pct(actual, forecast) * 100, "MAE": mae(actual, forecast),
           "RMSE": rmse(actual, forecast), "MAPE%": mape(actual, forecast), "WMAPE%": wmape(actual, forecast)}
    if insample is not None:
        out["MASE"] = mase(actual, forecast, insample, m)
    return out


def fva(actual, versions: dict[str, np.ndarray], naive=None) -> list[dict]:
    """Forecast Value Added: so WMAPE từng bước với bước trước (và với Naive)."""
    rows = []
    prev_name, prev_w = None, None
    steps = ({"Naive": naive} if naive is not None else {}) | versions
    for name, f in steps.items():
        w = wmape(actual, f)
        rows.append({"step": name, "WMAPE%": w, "Bias%": bias_pct(actual, f) * 100,
                     "FVA_vs_prev_pp": (prev_w - w) if prev_w is not None else np.nan,
                     "vs": prev_name})
        prev_name, prev_w = name, w
    return rows
