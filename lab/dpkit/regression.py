"""Hồi quy dự báo: trend + mùa vụ + Tết + khuyến mãi + giá. Dùng statsmodels OLS để có p-value, R²."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def design_matrix(periods, calendar: pd.DataFrame, promo_depth=None, price_index=None,
                  post_promo=True, month_dummies: bool = True, trend: bool = True) -> pd.DataFrame:
    per = pd.PeriodIndex(periods, freq="M")
    cal = calendar.set_index("month")
    X = pd.DataFrame(index=[str(p) for p in per])
    if trend:
        X["t"] = np.arange(1, len(per) + 1)
    if month_dummies:
        for k in range(2, 13):
            X[f"thang_{k}"] = (per.month == k).astype(int)
    X["tet_pre"] = cal.loc[X.index, "tet_pre_share"].values
    X["tet_post"] = cal.loc[X.index, "tet_post_share"].values
    if promo_depth is not None:
        d = np.asarray(promo_depth, dtype=float)
        X["promo_depth"] = d
        if post_promo:
            X["post_promo"] = np.r_[0, (d[:-1] > 0).astype(int)]
    if price_index is not None:
        X["price_index"] = np.asarray(price_index, dtype=float)
    return X


def fit_ols(y, X: pd.DataFrame):
    y = np.asarray(y, dtype=float)
    ok = ~np.isnan(y)
    model = sm.OLS(y[ok], sm.add_constant(X[ok], has_constant="add")).fit()
    return model


def coef_table(model) -> pd.DataFrame:
    t = pd.DataFrame({"he_so": model.params, "sai_so_chuan": model.bse, "t": model.tvalues, "p_value": model.pvalues})
    t["giu_bien?"] = np.where(t.p_value < 0.05, "Giữ (p<0,05)", "Cân nhắc bỏ")
    return t


def baseline_uplift(model, X: pd.DataFrame, promo_cols=("promo_depth", "post_promo")) -> pd.DataFrame:
    """Tách dự báo thành baseline (tắt khuyến mãi) và uplift."""
    Xc = sm.add_constant(X, has_constant="add")
    full = model.predict(Xc)
    Xb = Xc.copy()
    for c in promo_cols:
        if c in Xb:
            Xb[c] = 0
    base = model.predict(Xb)
    return pd.DataFrame({"fitted": full, "baseline": base, "uplift": full - base}, index=X.index)


def adjusted_r2(r2: float, n: int, k: int) -> float:
    return 1 - (1 - r2) * (n - 1) / (n - k - 1)
