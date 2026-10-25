"""Phương pháp mốc chuẩn (benchmark). Mọi mô hình phức tạp phải thắng được các mốc này."""
from __future__ import annotations

import numpy as np


def naive_fitted(y) -> np.ndarray:
    """Dự báo 1 bước trong mẫu: F_t = y_{t-1}."""
    y = np.asarray(y, dtype=float)
    f = np.full_like(y, np.nan)
    f[1:] = y[:-1]
    return f


def naive(y, h: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    return np.repeat(y[-1], h)


def seasonal_naive_fitted(y, m: int = 12) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    f = np.full_like(y, np.nan)
    f[m:] = y[:-m]
    return f


def seasonal_naive(y, h: int, m: int = 12) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    return np.array([y[len(y) - m + (i % m)] for i in range(h)])


def moving_average_fitted(y, n: int = 3) -> np.ndarray:
    """F_t = trung bình n kỳ trước t (Excel: =AVERAGE(B2:B4) kéo xuống)."""
    y = np.asarray(y, dtype=float)
    f = np.full_like(y, np.nan)
    for t in range(n, len(y)):
        f[t] = np.mean(y[t - n:t])
    return f


def moving_average(y, h: int, n: int = 3) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    return np.repeat(np.mean(y[-n:]), h)


def weighted_ma(y, h: int, weights=(1, 2, 3)) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)
    return np.repeat(np.dot(y[-len(w):], w) / w.sum(), h)


def drift(y, h: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    slope = (y[-1] - y[0]) / (len(y) - 1)
    return y[-1] + slope * np.arange(1, h + 1)
