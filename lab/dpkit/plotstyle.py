"""Phong cách biểu đồ thống nhất toàn khóa (màu thương hiệu ERX, palette đã kiểm tra mù màu)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

INK = "#1F2421"        # thực tế (actual) và chữ
MUTED = "#76777B"      # trục, chú thích (xám thương hiệu ERX)
GRID = "#E6E8E6"
BRAND = "#01AE42"      # xanh ERX (nền nhấn, vùng tô)
CAT = ["#008A3A", "#2563C9", "#D9720B", "#8E44AD", "#C2185B"]   # dự báo / chuỗi so sánh (thứ tự cố định)


def _register_fonts():
    """Đăng ký phông Be Vietnam Pro nếu có (thư mục assets/fonts của bộ tài liệu hoặc ~/.fonts)."""
    from pathlib import Path
    here = Path(__file__).resolve()
    cands = [p / "assets" / "fonts" for p in here.parents] + [Path.home() / ".fonts"]
    for d in cands:
        if d.is_dir():
            for f in d.glob("BeVietnamPro-*.ttf"):
                try:
                    font_manager.fontManager.addfont(str(f))
                except Exception:
                    pass


def use():
    # DejaVu Sans: đủ dấu tiếng Việt và ký tự Hy Lạp (α, β, σ…), hiển thị nhất quán trên mọi máy
    fam = "DejaVu Sans"
    plt.rcParams.update({
        "font.family": fam, "font.size": 11.5, "legend.fontsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 13,
        "axes.titlecolor": INK, "legend.frameon": False, "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.facecolor": "white",
        "lines.linewidth": 2.0, "axes.prop_cycle": plt.cycler(color=CAT),
    })
    return plt
