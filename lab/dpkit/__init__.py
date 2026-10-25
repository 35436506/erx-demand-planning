"""dpkit — thư viện Demand Planning dùng chung cho khóa ERX "Demand Planning & Forecasting in Practice".

Mỗi hàm tương ứng một công thức đã dạy trên lớp và có phiên bản Excel song song trong file bài tập.
Quy ước toàn khóa: e = actual − forecast  (e > 0 nghĩa là forecast THẤP hơn thực tế).
"""
from . import (baseline, classify, cleaning, data, evaluation, hierarchy, intermittent,  # noqa: F401
               inventory, metrics, promo, regression, seasonal, smoothing)

__version__ = "1.0.0"
