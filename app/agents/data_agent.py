"""数据分析 Agent：pandas 读取 CSV，matplotlib 生成图表，返回结构化分析结果。

数据源（seed 脚本生成）：
  - data/orders.csv   电商订单（品类 / 金额 / 状态 / 地区 / 渠道 / 时间）
  - data/devices.csv  物联网设备故障日志（设备类型 / 故障码 / 地区 / 时间）

分析类型由问题关键词决定：
  - 故障/设备相关 → 分析设备故障报表
  - 其余（销量/销售额/订单）→ 分析销售报表
  - 含“趋势/月度/时间” → 生成时间趋势折线图
  - 含“品类/类别” 或默认 → 生成品类柱状图
"""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import pandas as pd  # noqa: E402

from app.agents import AgentResult
from app.config import settings

# 常见中文字体，逐个探测可用项，避免中文显示为方框
_CN_FONTS = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]


def _setup_cn_font() -> None:
    for name in _CN_FONTS:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            plt.rcParams["font.sans-serif"] = [name]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


def _load_orders() -> pd.DataFrame:
    path = Path(settings.orders_csv)
    if not path.exists():
        raise FileNotFoundError(f"缺少数据文件: {path}，请先运行 python scripts/seed_data.py")
    df = pd.read_csv(path)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["revenue"] = df["price"] * df["quantity"]
    return df


def _load_devices() -> pd.DataFrame:
    path = Path(settings.devices_csv)
    if not path.exists():
        raise FileNotFoundError(f"缺少数据文件: {path}，请先运行 python scripts/seed_data.py")
    df = pd.read_csv(path)
    df["report_date"] = pd.to_datetime(df["report_date"])
    return df


def _save_chart(fig, name: str) -> str:
    settings.charts_dir.mkdir(parents=True, exist_ok=True)
    path = settings.charts_dir / name
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return f"/charts/{name}"


def _analyze_orders(question: str) -> AgentResult:
    df = _load_orders()
    total_revenue = df["revenue"].sum()
    order_count = len(df)
    avg_price = df["revenue"].mean()

    # 状态分布
    status_counts = df["status"].value_counts().to_dict()

    # 品类维度
    by_cat = df.groupby("category")["revenue"].sum().sort_values(ascending=False)
    top_cat = by_cat.index[0]
    top_cat_rev = by_cat.iloc[0]
    cat_share = top_cat_rev / total_revenue * 100

    # 月度趋势
    monthly = df.groupby(df["order_date"].dt.to_period("M"))["revenue"].sum()

    want_trend = any(k in question for k in ["趋势", "月度", "每月", "时间", "月份"])
    want_cat = any(k in question for k in ["品类", "类别", "类目"])

    if want_trend:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.plot([str(m) for m in monthly.index], monthly.values, marker="o", color="#4c8bf5")
        ax.set_title("月度销售额趋势")
        ax.set_xlabel("月份")
        ax.set_ylabel("销售额（元）")
        ax.grid(alpha=0.3)
        url = _save_chart(fig, "analysis_sales_trend.png")
    else:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.bar([c for c in by_cat.index], by_cat.values, color="#4c8bf5")
        ax.set_title("各品类销售额")
        ax.set_xlabel("品类")
        ax.set_ylabel("销售额（元）")
        for i, v in enumerate(by_cat.values):
            ax.text(i, v, f"{v/10000:.1f}万", ha="center", va="bottom", fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        url = _save_chart(fig, "analysis_sales_category.png")

    lines = [
        "📊 销售数据分析结果",
        f"- 订单总数：{order_count} 笔",
        f"- 总销售额：{total_revenue:,.0f} 元",
        f"- 客单价（均单额）：{avg_price:,.0f} 元",
        f"- 销售额最高的品类：**{top_cat}**（{top_cat_rev:,.0f} 元，占比 {cat_share:.1f}%）",
        f"- 订单状态分布：{'，'.join(f'{k} {v}笔' for k, v in status_counts.items())}",
        "",
        f"图表已生成：`{url}`",
    ]
    return AgentResult(text="\n".join(lines), type="chart", chart_url=url)


def _analyze_devices(question: str) -> AgentResult:
    df = _load_devices()
    total = len(df)
    fault_counts = df["fault_code"].value_counts().to_dict()
    device_counts = df["device_type"].value_counts().to_dict()
    monthly = df.groupby(df["report_date"].dt.to_period("M"))["device_id"].count()

    top_fault = df["fault_code"].value_counts().idxmax()
    top_fault_n = df["fault_code"].value_counts().max()
    top_fault_desc = df.loc[df["fault_code"] == top_fault, "fault_desc"].iloc[0]

    want_trend = any(k in question for k in ["趋势", "月度", "每月", "时间", "月份"])

    if want_trend:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.plot([str(m) for m in monthly.index], monthly.values, marker="o", color="#f5724c")
        ax.set_title("设备故障数量月度趋势")
        ax.set_xlabel("月份")
        ax.set_ylabel("故障数量（次）")
        ax.grid(alpha=0.3)
        url = _save_chart(fig, "analysis_fault_trend.png")
    else:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.pie(list(fault_counts.values()), labels=list(fault_counts.keys()), autopct="%1.1f%%",
               colors=["#4c8bf5", "#f5724c", "#6bc27c", "#f5c24c", "#9b6be0"])
        ax.set_title("故障码分布")
        url = _save_chart(fig, "analysis_fault_pie.png")

    lines = [
        "🔧 设备故障分析结果",
        f"- 故障记录总数：{total} 次",
        f"- 故障设备类型分布：{'，'.join(f'{k} {v}台' for k, v in device_counts.items())}",
        f"- 最高发故障码：**{top_fault}**（{top_fault_n} 次）",
        f"- 故障说明：{top_fault_desc}",
        "",
        f"图表已生成：`{url}`",
    ]
    return AgentResult(text="\n".join(lines), type="chart", chart_url=url)


class DataAgent:
    def handle(self, question: str) -> AgentResult:
        _setup_cn_font()
        if any(k in question for k in ["故障", "设备"]):
            return _analyze_devices(question)
        return _analyze_orders(question)


_data_agent: DataAgent | None = None


def get_data_agent() -> DataAgent:
    global _data_agent
    if _data_agent is None:
        _data_agent = DataAgent()
    return _data_agent
