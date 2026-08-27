"""Router Agent：意图识别路由器。

将用户问题分类到四个子 Agent 之一：
  - knowledge : 知识库问答（产品使用 / 故障维修 / 售后政策 / 保修 / 说明书）
  - order     : 订单 / 设备状态查询（查具体编号、物流、设备状态）
  - data      : 数据分析（销量 / 销售额 / 故障率 / 报表 / 趋势）
  - human     : 兜底（闲聊 / 道歉 / 转人工）

策略：先尝试 LLM 分类，若解析失败或超时，回退到关键词规则，保证路由永不中断。
"""
import re

from app.llm import create_llm

VALID_INTENTS = ("knowledge", "order", "data", "human")

_ROUTER_PROMPT = """你是智能客服系统的意图路由器。根据用户的问题，判断应交给哪个子 Agent 处理，只输出一个英文单词，不要输出任何其他内容。

可选类别：
- knowledge：产品如何使用、故障怎么修、售后政策、保修期、说明书等知识类问题
- order：查询某个具体订单或设备的状态、物流、编号
- data：统计、汇总、分析类问题，如销量、销售额、故障率、报表、趋势
- human：打招呼、闲聊、表达不满、明确要求转人工

示例：
- "我的榨汁机坏了怎么办？" → knowledge
- "帮我查一下订单 ORD-2026-00123 到哪了" → order
- "分析一下上个月各品类的销售情况" → data
- "你好呀" → human

问题：{question}
分类结果："""

# 关键词规则兜底（LLM 不可用时的快速降级）
_KEYWORD_RULES = [
    ("data", ["分析", "统计", "汇总", "销量", "销售额", "报表", "故障率", "趋势", "同比", "环比", "占比", "图表", "报告"]),
    ("order", ["订单", "物流", "发货", "到哪了", "快递", "查询", "设备状态", "编号"]),
    ("knowledge", ["怎么用", "怎么操作", "说明书", "保修", "售后", "政策", "坏了", "故障", "维修", "退换", "客服", "怎么办", "无法开机", "报错"]),
    ("human", ["你好", "嗨", "谢谢", "再见", "转人工", "投诉", "无聊"]),
]


def _keyword_classify(question: str) -> str:
    for intent, keywords in _KEYWORD_RULES:
        if any(k in question for k in keywords):
            return intent
    return "human"


class RouterAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = create_llm(temperature=0.0, max_tokens=32)
        return self._llm

    def classify(self, question: str) -> str:
        # 1) 先跑关键词快速通道：命中高置信度词（数据分析意图）直接返回，减少一次 LLM 调用
        if any(k in question for k in ["分析", "统计", "销量", "销售额", "报表", "故障率", "趋势"]):
            return "data"

        # 2) LLM 分类
        try:
            resp = self.llm.invoke(_ROUTER_PROMPT.format(question=question))
            label = (resp.content or "").strip().lower()
            # 只取开头第一个合法单词，容忍模型额外输出
            m = re.search(r"\b(knowledge|order|data|human)\b", label)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 3) 兜底：关键词规则
        return _keyword_classify(question)


_router: RouterAgent | None = None


def get_router() -> RouterAgent:
    global _router
    if _router is None:
        _router = RouterAgent()
    return _router
