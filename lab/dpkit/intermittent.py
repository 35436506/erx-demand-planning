"""Nhu cầu rời rạc: phân loại Syntetos–Boylan (ADI, CV²) và họ Croston (Croston, SBA, TSB)."""
from __future__ import annotations

import numpy as np


def adi_cv2(y) -> tuple[float, float]:
    """ADI = số kỳ / số kỳ có nhu cầu; CV² = (độ lệch chuẩn / trung bình)² của CỠ đơn (chỉ kỳ > 0)."""
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    nz = y[y > 0]
    if len(nz) == 0:
        return np.inf, np.nan
    adi = len(y) / len(nz)
    cv2 = (nz.std(ddof=1) / nz.mean()) ** 2 if len(nz) > 1 else 0.0
    return float(adi), float(cv2)


def sbc_class(adi: float, cv2: float) -> str:
    """Ngưỡng Syntetos–Boylan–Croston: ADI 1,32 ; CV² 0,49."""
    if adi < 1.32:
        return "Smooth (đều)" if cv2 < 0.49 else "Erratic (thất thường)"
    return "Intermittent (rời rạc)" if cv2 < 0.49 else "Lumpy (rời rạc + gộp lô)"


def croston(y, h: int = 12, alpha: float = 0.1, variant: str = "croston") -> dict:
    """variant: 'croston' | 'sba' | 'tsb'. Khởi tạo bằng lần phát sinh đầu tiên.
    Trả về fitted (dự báo 1 bước), forecast, và các thành phần z (cỡ), p (khoảng cách) hoặc r (xác suất)."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    f = np.full(n, np.nan)
    first = int(np.argmax(y > 0)) if (y > 0).any() else None
    if first is None:
        return {"fitted": np.zeros(n), "forecast": np.zeros(h)}
    z = y[first]
    if variant == "tsb":
        r = (y[: first + 1] > 0).mean()
        for t in range(first + 1, n):
            f[t] = r * z
            occ = 1.0 if y[t] > 0 else 0.0
            r = alpha * occ + (1 - alpha) * r
            if y[t] > 0:
                z = alpha * y[t] + (1 - alpha) * z
        return {"fitted": f, "forecast": np.repeat(r * z, h), "z": z, "r": r}
    p = first + 1.0
    q = 1
    adj = (1 - alpha / 2) if variant == "sba" else 1.0
    for t in range(first + 1, n):
        f[t] = adj * z / p
        if y[t] > 0:
            z = alpha * y[t] + (1 - alpha) * z
            p = alpha * q + (1 - alpha) * p
            q = 1
        else:
            q += 1
    return {"fitted": f, "forecast": np.repeat(adj * z / p, h), "z": z, "p": p}
