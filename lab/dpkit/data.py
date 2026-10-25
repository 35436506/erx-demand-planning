"""Đọc bộ dữ liệu case MBF và dựng chuỗi thời gian theo hàng kế hoạch × kênh."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TABLES = ["sku_master", "sales_history", "sellout_dms", "promo_calendar", "prices", "calendar",
          "inventory_snapshot", "in_month_tracking", "capacity", "forecast_history", "data_dictionary",
          "demand_clean", "adjustment_log_reference"]


def default_data_dir() -> Path:
    here = Path(__file__).resolve()
    for cand in [here.parent / "data", here.parents[1] / "data", here.parents[2] / "06_Data" / "csv",
                 here.parents[1] / "06_Data" / "csv"]:
        if (cand / "sales_history.csv").exists():
            return cand
    raise FileNotFoundError("Không tìm thấy thư mục dữ liệu (cần sales_history.csv)")


def load(data_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Đọc toàn bộ bảng CSV thành dict {tên bảng: DataFrame}."""
    d = Path(data_dir) if data_dir else default_data_dir()
    out = {}
    for t in TABLES:
        p = d / f"{t}.csv"
        if p.exists():
            out[t] = pd.read_csv(p, encoding="utf-8-sig")
    return out


def planning_item(sku: str, master: pd.DataFrame | None = None) -> str:
    if master is not None and "planning_item" in master:
        m = master.set_index("sku")["planning_item"].to_dict()
        return m.get(sku, sku)
    return "S06" if sku == "S06N" else sku


def series(df: pd.DataFrame, item: str, channel: str | None = None, col: str = "shipments",
           master: pd.DataFrame | None = None, start: str | None = None, end: str | None = None) -> pd.Series:
    """Chuỗi tháng của một hàng kế hoạch (đã nối mã cũ–mới). channel=None -> cộng hai kênh.
    Giữ NaN nếu tháng bị thiếu dữ liệu (không tự điền 0)."""
    x = df.copy()
    x["item"] = x["sku"].map(lambda s: planning_item(s, master))
    x = x[x["item"] == item]
    if channel:
        x = x[x["channel"] == channel]
    s = x.groupby("month")[col].sum(min_count=1)
    s.index = pd.PeriodIndex(s.index, freq="M")
    full = pd.period_range(start or s.index.min(), end or s.index.max(), freq="M")
    s = s.reindex(full)
    s.name = f"{item}|{channel or 'ALL'}|{col}"
    return s


def all_series(df: pd.DataFrame, col: str = "shipments", master: pd.DataFrame | None = None) -> dict[str, pd.Series]:
    x = df.copy()
    x["item"] = x["sku"].map(lambda s: planning_item(s, master))
    out = {}
    for (item, ch), _ in x.groupby(["item", "channel"]):
        out[f"{item}|{ch}"] = series(df, item, ch, col, master)
    return out


def to_array(s: pd.Series) -> np.ndarray:
    return np.asarray(s, dtype=float)
