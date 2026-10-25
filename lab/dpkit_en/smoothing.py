"""Họ san bằng mũ (Exponential Smoothing) — viết tay để khớp TỪNG Ô với file Excel.

Khởi tạo (giống Excel bài tập):
  SES : L_1 = y_1
  Holt: L_1 = y_1 ; T_1 = (y_4 − y_1)/3
  Holt-Winters: năm đầu (m kỳ) dùng để khởi tạo — L = trung bình năm 1,
                T = (TB năm 2 − TB năm 1)/m, chỉ số mùa vụ = y / L (nhân) hoặc y − L (cộng).
Tham số tối ưu = cực tiểu SSE 1-step forecast (tương đương Solver trong Excel).
Ràng buộc β ≤ 0,5 (thực hành phổ biến, tránh xu hướng chạy theo nhiễu).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize


def _check(y):
    y = np.asarray(y, dtype=float)
    if np.isnan(y).any():
        raise ValueError("The series still has blank cells (NaN) — clean the data before smoothing (Session 2).")
    return y


@dataclass
class ESResult:
    method: str
    params: dict
    fitted: np.ndarray            # 1-step forecast trong mẫu (NaN ở kỳ khởi tạo)
    forecast: np.ndarray          # forecasts h bước ngoài mẫu
    level: np.ndarray
    trend: np.ndarray | None = None
    season: np.ndarray | None = None
    sse: float = np.nan
    extra: dict = field(default_factory=dict)


# ------------------------------------------------------------------ SES

def ses_filter(y, alpha: float):
    y = _check(y)
    n = len(y)
    L = np.zeros(n)
    f = np.full(n, np.nan)
    L[0] = y[0]
    for t in range(1, n):
        f[t] = L[t - 1]
        L[t] = alpha * y[t] + (1 - alpha) * L[t - 1]
    return f, L


def ses(y, h: int = 12, alpha: float | None = None) -> ESResult:
    y = _check(y)

    def sse(a):
        f, _ = ses_filter(y, float(a[0]))
        return np.nansum((y - f) ** 2)

    if alpha is None:
        grid = np.linspace(0.01, 0.99, 50)
        a0 = grid[np.argmin([sse([g]) for g in grid])]
        alpha = float(minimize(sse, [a0], bounds=[(0.0, 1.0)], method="L-BFGS-B").x[0])
    f, L = ses_filter(y, alpha)
    return ESResult("SES", {"alpha": alpha}, f, np.repeat(L[-1], h), L, sse=float(np.nansum((y - f) ** 2)))


# ------------------------------------------------------------------ Holt (có thể tắt dần)

def holt_filter(y, alpha: float, beta: float, phi: float = 1.0):
    y = _check(y)
    n = len(y)
    L = np.zeros(n)
    T = np.zeros(n)
    f = np.full(n, np.nan)
    k = min(3, n - 1)
    L[0] = y[0]
    T[0] = (y[k] - y[0]) / k
    for t in range(1, n):
        f[t] = L[t - 1] + phi * T[t - 1]
        L[t] = alpha * y[t] + (1 - alpha) * (L[t - 1] + phi * T[t - 1])
        T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * phi * T[t - 1]
    return f, L, T


def holt(y, h: int = 12, alpha=None, beta=None, damped: bool = False, phi: float | None = None) -> ESResult:
    y = _check(y)

    def unpack(p):
        a, b = p[0], p[1]
        ph = p[2] if damped and phi is None else (phi if phi is not None else 1.0)
        return a, b, ph

    def sse(p):
        f, _, _ = holt_filter(y, *unpack(p))
        return np.nansum((y - f) ** 2)

    if alpha is None or beta is None:
        bounds = [(0, 1), (0, 0.5)] + ([(0.8, 0.98)] if damped and phi is None else [])
        best = None
        for a0 in (0.2, 0.5, 0.8):
            for b0 in (0.05, 0.2):
                x0 = [a0, b0] + ([0.9] if damped and phi is None else [])
                r = minimize(sse, x0, bounds=bounds, method="L-BFGS-B")
                if best is None or r.fun < best.fun:
                    best = r
        alpha, beta, ph = unpack(best.x)
    else:
        ph = phi if phi is not None else (0.9 if damped else 1.0)
    f, L, T = holt_filter(y, alpha, beta, ph)
    steps = np.array([sum(ph ** j for j in range(1, i + 1)) for i in range(1, h + 1)])
    fc = L[-1] + steps * T[-1]
    name = "Holt (damped)" if damped else "Holt"
    return ESResult(name, {"alpha": alpha, "beta": beta, "phi": ph}, f, fc, L, T,
                    sse=float(np.nansum((y - f) ** 2)))


# ------------------------------------------------------------------ Holt-Winters

def hw_filter(y, alpha, beta, gamma, m=12, seasonal="mul"):
    y = _check(y)
    n = len(y)
    if n < 2 * m:
        raise ValueError(f"Holt-Winters needs at least {2*m} periods of data (2 seasons).")
    L = np.full(n, np.nan)
    T = np.full(n, np.nan)
    S = np.full(n, np.nan)
    f = np.full(n, np.nan)
    l0 = y[:m].mean()
    b0 = (y[m:2 * m].mean() - y[:m].mean()) / m
    if seasonal == "mul":
        S[:m] = y[:m] / l0
    else:
        S[:m] = y[:m] - l0
    L[m - 1], T[m - 1] = l0, b0
    for t in range(m, n):
        base = L[t - 1] + T[t - 1]
        if seasonal == "mul":
            f[t] = base * S[t - m]
            L[t] = alpha * (y[t] / S[t - m]) + (1 - alpha) * base
            T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * T[t - 1]
            S[t] = gamma * (y[t] / L[t]) + (1 - gamma) * S[t - m]
        else:
            f[t] = base + S[t - m]
            L[t] = alpha * (y[t] - S[t - m]) + (1 - alpha) * base
            T[t] = beta * (L[t] - L[t - 1]) + (1 - beta) * T[t - 1]
            S[t] = gamma * (y[t] - L[t]) + (1 - gamma) * S[t - m]
    return f, L, T, S


def holt_winters(y, h: int = 12, m: int = 12, seasonal: str = "mul", alpha=None, beta=None, gamma=None) -> ESResult:
    y = _check(y)

    def sse(p):
        f, *_ = hw_filter(y, p[0], p[1], p[2], m, seasonal)
        return np.nansum((y - f) ** 2)

    if alpha is None or beta is None or gamma is None:
        best = None
        for a0 in (0.1, 0.3, 0.6):
            for g0 in (0.05, 0.3):
                r = minimize(sse, [a0, 0.05, g0], bounds=[(0, 1), (0, 0.5), (0, 1)], method="L-BFGS-B")
                if best is None or r.fun < best.fun:
                    best = r
        alpha, beta, gamma = (float(v) for v in best.x)
    f, L, T, S = hw_filter(y, alpha, beta, gamma, m, seasonal)
    n = len(y)
    fc = []
    for i in range(1, h + 1):
        s = S[n - m + ((i - 1) % m)]
        base = L[-1] + i * T[-1]
        fc.append(base * s if seasonal == "mul" else base + s)
    name = ("Multiplicative" if seasonal == "mul" else "Additive") + " Holt-Winters"
    return ESResult(name, {"alpha": alpha, "beta": beta, "gamma": gamma, "m": m}, f, np.array(fc), L, T, S,
                    sse=float(np.nansum((y - f) ** 2)))
