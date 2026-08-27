"""订单 / 设备状态查询 Agent：在本地 CSV 中按编号精确检索。

在真实生产环境中，这里应替换为调用外部订单系统 / 物联网平台的 HTTP API，
因此该 Agent 也充当“外部 API Agent”的本地可演示实现（预留接口见代码注释）。
"""
import re
from pathlib import Path

import pandas as pd

from app.agents import AgentResult
from app.config import settings

# 订单格式 ORD-2026-00123，设备格式 DEV-1001；先匹配完整长格式，再降级匹配数字
_ID_RE = re.compile(r"(?i)(ORD-\d{4}-\d{3,}|DEV-\d{3,}|\d{4,})")


class LookupAgent:
    def handle(self, question: str) -> AgentResult:
        m = _ID_RE.search(question)
        if not m:
            return AgentResult(
                text="我没有在您的问题中识别到订单或设备编号。\n"
                     "您可以这样问我：\n"
                     "· “查询订单 ORD-2026-00123 的状态”\n"
                     "· “设备 DEV-1001 现在是什么状态？”\n"
                     "· “帮我查一下快递到哪了”",
                type="text",
            )
        token = m.group(1).upper()
        want_device = "设备" in question or token.startswith("DEV")
        try:
            if want_device:
                return self._lookup_device(token)
            return self._lookup_order(token)
        except FileNotFoundError:
            return AgentResult(
                text="订单/设备数据文件缺失，请先运行 `python scripts/seed_data.py` 生成示例数据。",
                type="text",
            )

    # ---------- 订单查询 ----------
    def _lookup_order(self, token: str) -> AgentResult:
        path = Path(settings.orders_csv)
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path)
        df["order_id"] = df["order_id"].str.upper()
        # 兼容用户只报数字尾号
        hit = df[df["order_id"] == token]
        if hit.empty and token.isdigit():
            hit = df[df["order_id"].str.endswith(token)]
        if hit.empty:
            return AgentResult(text=f"很抱歉，没有找到编号为 **{token}** 的订单，请核对后重试。", type="text")
        row = hit.iloc[0]
        lines = [
            f"📦 订单 {row['order_id']} 查询结果",
            f"- 商品：{row['product']}（{row['category']}）",
            f"- 金额：{row['price']:.0f} 元 × {row['quantity']} 件",
            f"- 下单时间：{row['order_date']}",
            f"- 收货地区：{row['region']}",
            f"- 渠道：{row['channel']}",
            f"- 当前状态：**{row['status']}**",
        ]
        return AgentResult(text="\n".join(lines), type="text")

    # ---------- 设备状态查询 ----------
    def _lookup_device(self, token: str) -> AgentResult:
        path = Path(settings.devices_csv)
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path)
        df["device_id"] = df["device_id"].str.upper()
        hit = df[df["device_id"] == token]
        if hit.empty and token.isdigit():
            hit = df[df["device_id"].str.endswith(token)]
        if hit.empty:
            return AgentResult(text=f"很抱歉，没有找到编号为 **{token}** 的设备，请核对后重试。", type="text")
        row = hit.iloc[0]
        status_icon = {"在线": "🟢", "离线": "🔴", "待维修": "🟠", "维修中": "🔧"}.get(row["status"], "⚪")
        lines = [
            f"🔌 设备 {row['device_id']} 状态查询结果",
            f"- 设备类型：{row['device_type']}",
            f"- 当前状态：{status_icon} **{row['status']}**",
            f"- 最近故障码：{row['fault_code']}（{row['fault_desc']}）",
            f"- 所属地区：{row['region']}",
            f"- 故障上报时间：{row['report_date']}",
        ]
        return AgentResult(text="\n".join(lines), type="text")


_lookup_agent: LookupAgent | None = None


def get_lookup_agent() -> LookupAgent:
    global _lookup_agent
    if _lookup_agent is None:
        _lookup_agent = LookupAgent()
    return _lookup_agent
