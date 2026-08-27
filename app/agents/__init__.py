"""多 Agent 子系统：路由 + 知识库 + 数据分析 + 订单查询 + 兜底。"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentResult:
    """Agent 统一返回结构。

    type: text（纯文本回复） | chart（文本+图表） | handoff（转人工）
    """

    text: str
    type: str = "text"
    chart_url: str | None = None
    sources: List[dict] = field(default_factory=list)
