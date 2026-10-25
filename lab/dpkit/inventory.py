"""Từ sai số dự báo đến tồn kho, cảnh báo sớm và giá trị tài chính."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def z_value(service_level: float) -> float:
    """Excel: =NORM.S.INV(service_level)."""
    return float(norm.ppf(service_level))


def safety_stock(sigma_error: float, lead_time_periods: float, service_level: float = 0.95,
                 review_period: float = 0.0) -> float:
    """SS = z × σ_e × √(L + R). σ_e là độ lệch chuẩn (≈ RMSE) sai số dự báo NGOÀI MẪU mỗi kỳ."""
    return z_value(service_level) * sigma_error * np.sqrt(lead_time_periods + review_period)


def safety_stock_lt_var(mean_demand: float, sigma_error: float, lt_mean: float, lt_sd: float,
                        service_level: float = 0.95) -> float:
    """Mở rộng: lead time biến động. SS = z × √(L·σ_e² + D²·σ_L²)."""
    return z_value(service_level) * np.sqrt(lt_mean * sigma_error ** 2 + mean_demand ** 2 * lt_sd ** 2)


def reorder_point(mean_demand_per_period: float, lead_time_periods: float, ss: float) -> float:
    return mean_demand_per_period * lead_time_periods + ss


def service_tradeoff(sigma_error: float, lead_time_periods: float, unit_cost: float, holding_rate_yr: float,
                     levels=(0.80, 0.85, 0.90, 0.95, 0.97, 0.98, 0.99, 0.995)) -> pd.DataFrame:
    rows = []
    for sl in levels:
        ss = safety_stock(sigma_error, lead_time_periods, sl)
        rows.append({"service_level": sl, "z": z_value(sl), "safety_stock": ss,
                     "von_ton_kho_trieu": ss * unit_cost / 1000,
                     "chi_phi_giu_nam_trieu": ss * unit_cost * holding_rate_yr / 1000})
    return pd.DataFrame(rows)


def run_rate_alert(actual_to_date: float, days_elapsed: int, days_in_month: int, monthly_forecast: float,
                   threshold: float = 0.15) -> dict:
    """Cảnh báo sớm trong tháng: so tốc độ bán thực tế với forecast tháng (đã quy theo số ngày)."""
    expected = monthly_forecast * days_elapsed / days_in_month
    ratio = actual_to_date / expected if expected else np.nan
    projected = actual_to_date / days_elapsed * days_in_month
    flag = "Bình thường"
    if ratio > 1 + threshold:
        flag = "Bán nhanh — nguy cơ đứt hàng"
    elif ratio < 1 - threshold:
        flag = "Bán chậm — nguy cơ tồn/cận date"
    return {"expected_to_date": expected, "run_rate_ratio": ratio, "projected_month": projected, "flag": flag}


def shelf_life_risk(inv: pd.DataFrame, avg_daily_demand: dict[str, float], min_remaining_pct: float = 0.67) -> pd.DataFrame:
    """Lô nào sẽ không bán kịp trước khi xuống dưới ngưỡng hạn dùng khách chấp nhận (FEFO)."""
    rows = []
    for sku, g in inv.sort_values("expiry_date").groupby("sku"):
        d = avg_daily_demand.get(sku, 0)
        cum_days = 0.0
        for r in g.itertuples():
            days_to_sell = r.qty / d if d else np.inf
            cum_days += days_to_sell
            sellable_days = r.remaining_days - (1 - min_remaining_pct) * r.shelf_life_days
            rows.append({"sku": sku, "batch": r.batch, "qty": r.qty, "remaining_days": r.remaining_days,
                         "ngay_ban_het_luy_ke": cum_days, "ngay_con_ban_duoc": sellable_days,
                         "rui_ro": "CẢNH BÁO" if cum_days > sellable_days else "OK"})
    return pd.DataFrame(rows)


def volume_to_value(plan: pd.DataFrame, price: dict[str, float], cost: dict[str, float]) -> pd.DataFrame:
    p = plan.copy()
    p["doanh_thu_trieu"] = p.apply(lambda r: r.qty * price.get(r.sku, 0) / 1000, axis=1)
    p["gia_von_trieu"] = p.apply(lambda r: r.qty * cost.get(r.sku, 0) / 1000, axis=1)
    p["lai_gop_trieu"] = p.doanh_thu_trieu - p.gia_von_trieu
    return p
