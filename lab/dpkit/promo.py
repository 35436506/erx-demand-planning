"""Khuyến mãi và sản phẩm mới: uplift, post-dip, ăn lạm, NPD theo mã tương tự."""
from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_excluding_promos(y: pd.Series, promo_months: set, window: int = 3) -> pd.Series:
    """Baseline = trung bình các tháng KHÔNG khuyến mãi và không phải tháng ngay sau khuyến mãi gần nhất."""
    vals = y.copy().astype(float)
    excluded = set(promo_months) | {str(pd.Period(m, "M") + 1) for m in promo_months}
    base = pd.Series(index=y.index, dtype=float)
    for i, mo in enumerate(y.index):
        hist = [vals.iloc[j] for j in range(max(0, i - 12), i) if str(y.index[j]) not in excluded]
        base.iloc[i] = np.mean(hist[-window:]) if len(hist) else np.nan
    return base


def promo_effects(y: pd.Series, base: pd.Series, promo_months: list[str]) -> pd.DataFrame:
    rows = []
    for mo in promo_months:
        if mo not in y.index.astype(str):
            continue
        nxt = str(pd.Period(mo, "M") + 1)
        a = y[y.index.astype(str) == mo].iloc[0]
        b = base[base.index.astype(str) == mo].iloc[0]
        an = y[y.index.astype(str) == nxt].iloc[0] if nxt in y.index.astype(str) else np.nan
        bn = base[base.index.astype(str) == nxt].iloc[0] if nxt in base.index.astype(str) else np.nan
        rows.append({"month": mo, "actual": a, "baseline": b, "uplift": a - b, "uplift_pct": (a / b - 1) * 100,
                     "post_dip": an - bn, "post_dip_pct": (an / bn - 1) * 100 if bn else np.nan,
                     "net_incremental": (a - b) + (an - bn if not np.isnan(an) else 0)})
    return pd.DataFrame(rows)


def promo_pnl(base_units: float, uplift_pct: float, post_dip_pct: float, list_price: float, depth: float,
              unit_cost: float, fixed_cost: float = 0.0) -> dict:
    """So lãi gộp có/không khuyến mãi (đơn vị tiền theo price/cost)."""
    no = base_units * 2 * (list_price - unit_cost)
    promo_units = base_units * (1 + uplift_pct)
    after_units = base_units * (1 + post_dip_pct)
    yes = promo_units * (list_price * (1 - depth) - unit_cost) + after_units * (list_price - unit_cost) - fixed_cost
    return {"lai_khong_KM": no, "lai_co_KM": yes, "chenh_lech": yes - no,
            "uplift_hoa_von_pct": ((base_units * depth * list_price + fixed_cost - base_units * post_dip_pct * (list_price - unit_cost))
                                   / (base_units * (list_price * (1 - depth) - unit_cost))) * 100}


def npd_forecast(pipeline_stores: int, units_per_store: float, repeat_rate_curve: list[float], steady_state: float) -> np.ndarray:
    """Dự báo sản phẩm mới = lấp đầy kênh (tháng đầu) + bán lặp lại theo đường cong tăng dần."""
    pipe = pipeline_stores * units_per_store
    rep = np.array(repeat_rate_curve) * steady_state
    rep[0] += pipe
    return rep


def analog_curve(analog: np.ndarray, scale: float) -> np.ndarray:
    """Mượn hình dạng đường bán của mã tương tự (chuẩn hóa theo tháng ổn định) rồi nhân quy mô."""
    a = np.asarray(analog, dtype=float)
    return a / a[-3:].mean() * scale
