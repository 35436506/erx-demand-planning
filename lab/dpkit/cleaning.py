"""Làm sạch dữ liệu nhu cầu — nguyên tắc: KHÔNG xóa số gốc, mọi điều chỉnh có lý do và được ghi nhật ký."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass
class Adjustment:
    series: str
    month: str
    original: float
    adjusted: float
    rule: str
    reason: str
    evidence: str = ""


class AdjustmentLog(list):
    def add(self, **kw):
        self.append(Adjustment(**kw))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(a) for a in self])


def iqr_flags(y, k: float = 1.5) -> tuple[np.ndarray, float, float]:
    """Gắn cờ ngoài [Q1 − k·IQR, Q3 + k·IQR] (Excel: QUARTILE.INC)."""
    y = np.asarray(y, dtype=float)
    q1, q3 = np.nanpercentile(y, 25), np.nanpercentile(y, 75)
    lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
    return (y < lo) | (y > hi), lo, hi


def zscore_flags(y, z: float = 3.0) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    return np.abs((y - np.nanmean(y)) / np.nanstd(y, ddof=1)) > z


def robust_flags(y, months, idx=None, k: float = 3.5) -> np.ndarray:
    """Cờ dựa trên phần dư sau khi khử mùa vụ, đo bằng MAD — ít bị chính outlier làm lệch."""
    y = np.asarray(y, dtype=float)
    if idx is not None:
        s = np.array([idx[m] for m in months])
        y = y / s
    med = np.nanmedian(y)
    mad = np.nanmedian(np.abs(y - med)) * 1.4826
    return np.abs(y - med) > k * mad if mad else np.zeros(len(y), bool)


def correct_stockout_gt(shipments: float, stockout_days: int, days_in_month: int) -> float:
    """Kênh GT (không ghi đơn bị từ chối): nhu cầu ≈ xuất kho × số ngày / số ngày có hàng."""
    if stockout_days <= 0:
        return shipments
    return shipments * days_in_month / (days_in_month - stockout_days)


def interpolate_gap(y) -> np.ndarray:
    """Nội suy tuyến tính các ô trống bên trong chuỗi."""
    return pd.Series(np.asarray(y, dtype=float)).interpolate(limit_area="inside").to_numpy()


def clean_series(df_hist: pd.DataFrame, sku: str, channel: str, master: pd.DataFrame,
                 sellout: pd.DataFrame | None = None, log: AdjustmentLog | None = None) -> pd.DataFrame:
    """Quy trình làm sạch chuẩn của khóa học cho MỘT hàng kế hoạch × kênh. Trả về bảng 3 lớp:
    recorded (số ghi nhận) → demand (nhu cầu ước tính) với cột flag/rule."""
    log = log if log is not None else AdjustmentLog()
    m = master.set_index("sku")
    items = [s for s in m.index if m.loc[s, "planning_item"] == sku] or [sku]
    x = df_hist[(df_hist.sku.isin(items)) & (df_hist.channel == channel)]
    g = x.groupby("month").agg(orders=("orders", lambda s: s.sum(min_count=1)),
                               shipments=("shipments", lambda s: s.sum(min_count=1)),
                               returns=("returns", "sum"), stockout_days=("stockout_days", "max"),
                               n_codes=("sku", "nunique"))
    g = g.reindex(sorted(df_hist.month.unique()))
    g["recorded"] = g.shipments
    g["demand"] = g.shipments.astype(float)
    g["rule"] = ""
    key = f"{sku}|{channel}"
    upc = float(m.loc[items[-1], "units_per_carton"])
    # 1. Đổi mã: đã cộng các mã cùng planning_item
    for mo, r in g[g.n_codes > 1].iterrows():
        g.loc[mo, "rule"] += "Nối mã cũ–mới; "
        log.add(series=key, month=mo, original=np.nan, adjusted=r.shipments, rule="Nối mã",
                reason="Cộng mã cũ và mã mới cùng hàng kế hoạch", evidence="sku_master.planning_item")
    # 2. Lỗi đơn vị: giá trị ≈ units_per_carton lần mức trung vị
    vals = g.demand.to_numpy(dtype=float)
    for i, (mo, r) in enumerate(g.iterrows()):
        nb = np.r_[vals[max(0, i - 3):i], vals[i + 1:i + 4]]
        nb = nb[~np.isnan(nb)]
        if not (r.demand > 0) or len(nb) == 0:
            continue
        med = np.median(nb)
        same_month = [vals[j] for j in (i - 12, i + 12) if 0 <= j < len(vals) and not np.isnan(vals[j])]
        seasonal_peak = any(abs(v / r.demand - 1) < 0.6 for v in same_month)
        if upc > 1 and med > 0 and r.demand > 8 * med and abs(r.demand / upc / med - 1) < 0.5 and not seasonal_peak:
            new = r.demand / upc
            log.add(series=key, month=mo, original=r.demand, adjusted=new, rule="Sửa đơn vị",
                    reason=f"Số ghi theo đơn vị lẻ, chia {upc:.0f}", evidence="units_per_carton")
            g.loc[mo, ["demand", "rule"]] = [new, g.loc[mo, "rule"] + "Sửa đơn vị; "]
    # 3. Có sell-out (DMS) cho kênh GT → dùng sell-out làm nhu cầu: đã gồm cả tác động đẩy hàng cuối kỳ
    #    và hết hàng phía công ty (NPP vẫn bán từ tồn của họ). Ưu tiên nguồn gần người mua nhất.
    has_so = False
    if sellout is not None and channel == "GT":
        so = sellout[(sellout.sku == sku) & (sellout.channel == channel)].set_index("month").sellout_dms
        if len(so):
            has_so = True
            for mo in g.index.intersection(so.index):
                if abs(g.loc[mo, "demand"] - so[mo]) / so[mo] > 0.02:
                    why = "Hết hàng phía công ty; NPP vẫn bán từ tồn" if g.loc[mo, "stockout_days"] > 0 else \
                        "Xuất kho lệch bán ra (đẩy hàng/xả hàng NPP)"
                    log.add(series=key, month=mo, original=g.loc[mo, "demand"], adjusted=so[mo], rule="Dùng sell-out",
                            reason=why, evidence="sellout_dms")
                    g.loc[mo, ["demand", "rule"]] = [so[mo], g.loc[mo, "rule"] + "Sell-out; "]
    # 4. Hết hàng (khi không có sell-out): MT dùng PO của chuỗi; GT quy đổi theo số ngày có hàng
    if not has_so:
        for mo, r in g[g.stockout_days > 0].iterrows():
            dim = pd.Period(mo, "M").days_in_month
            use_po = channel == "MT" and r.orders > r.shipments
            new = r.orders if use_po else correct_stockout_gt(r.demand, int(r.stockout_days), dim)
            how = "Dùng PO của chuỗi (MT)" if use_po else f"Quy đổi theo {int(r.stockout_days)} ngày hết hàng"
            log.add(series=key, month=mo, original=r.demand, adjusted=new, rule="Phục hồi hết hàng", reason=how,
                    evidence="stockout_days")
            g.loc[mo, ["demand", "rule"]] = [new, g.loc[mo, "rule"] + "Hết hàng; "]
    # 5. Ô trống bên trong chuỗi: nội suy
    inner = g.demand.isna() & g.demand.ffill().notna() & g.demand.bfill().notna()
    filled = interpolate_gap(g.demand)
    for mo in g.index[inner]:
        v = filled[list(g.index).index(mo)]
        log.add(series=key, month=mo, original=np.nan, adjusted=v, rule="Nội suy", reason="Thiếu dữ liệu",
                evidence="Ô trống trong ERP")
        g.loc[mo, ["demand", "rule"]] = [v, g.loc[mo, "rule"] + "Nội suy; "]
    g["rule"] = g.rule.str.rstrip("; ")
    return g[["recorded", "orders", "returns", "stockout_days", "demand", "rule"]]
