"""Phân cấp dự báo: CV ở các cấp, top-down theo tỷ trọng lịch sử, bottom-up."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .classify import cv


def cv_by_level(hist: pd.DataFrame, value_col: str = "shipments", master: pd.DataFrame | None = None) -> pd.DataFrame:
    """So CV trung bình ở 4 cấp: SKU×kênh, SKU, nhóm hàng, toàn công ty."""
    h = hist.copy()
    if master is not None:
        h = h.merge(master[["sku", "category", "planning_item"]], on="sku", how="left")
    else:
        h["category"] = "ALL"
        h["planning_item"] = h.sku
    lv = {
        "SKU × kênh": ["planning_item", "channel"],
        "SKU": ["planning_item"],
        "Nhóm hàng": ["category"],
        "Toàn công ty": [],
    }
    rows = []
    for name, keys in lv.items():
        if keys:
            g = h.groupby(keys + ["month"])[value_col].sum().unstack("month")
            cvs = g.apply(lambda r: cv(r.values), axis=1)
            rows.append({"cap": name, "so_chuoi": len(g), "CV_trung_vi": float(cvs.median()),
                         "CV_trung_binh": float(cvs.mean())})
        else:
            s = h.groupby("month")[value_col].sum()
            rows.append({"cap": name, "so_chuoi": 1, "CV_trung_vi": cv(s.values), "CV_trung_binh": cv(s.values)})
    return pd.DataFrame(rows)


def top_down(total_fc: np.ndarray, children_hist: pd.DataFrame, last_n: int = 12) -> pd.DataFrame:
    """Chia dự báo tổng xuống theo tỷ trọng lịch sử last_n kỳ. children_hist: cột = con, hàng = tháng."""
    share = children_hist.tail(last_n).sum() / children_hist.tail(last_n).sum().sum()
    return pd.DataFrame(np.outer(total_fc, share.values), columns=children_hist.columns)


def bottom_up(children_fc: pd.DataFrame) -> np.ndarray:
    return children_fc.sum(axis=1).to_numpy()
