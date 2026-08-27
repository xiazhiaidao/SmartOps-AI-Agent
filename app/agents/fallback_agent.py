"""兜底 Agent：闲聊 / 寒暄，识别到“转人工/投诉”等强情绪词时转人工客服。"""
from app.agents import AgentResult
from app.llm import create_llm

_FALLBACK_PROMPT = """你是 SmartOps 智能客服系统（面向电商与物联网设备售后）的接待助手。

请用友好、简洁的中文回应用户。注意：
- 这是闲聊场景，无需调用任何工具。
- 如果用户表达强烈不满、要求投诉或坚持要人工客服，请明确给出转人工提示。
- 不要编造系统功能，也不要提及内部实现。"""

_HANDOFF_KEYWORDS = ["转人工", "人工客服", "投诉", "退款", "赔偿", "要说法", "找领导"]


class FallbackAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = create_llm(temperature=0.6)
        return self._llm

    def handle(self, question: str) -> AgentResult:
        # 强情绪 / 转人工意图 → 直接转人工，不调用 LLM，保证即时响应
        if any(k in question for k in _HANDOFF_KEYWORDS):
            return AgentResult(
                text="收到，正在为您转接人工客服。\n"
                     "温馨提示：人工客服工作时间为 9:00-21:00，当前您的工单已加急，预计 5 分钟内响应。",
                type="handoff",
            )
        try:
            resp = self.llm.invoke(
                [
                    {"role": "system", "content": _FALLBACK_PROMPT},
                    {"role": "user", "content": question},
                ]
            )
            return AgentResult(text=resp.content, type="text")
        except Exception:
            return AgentResult(
                text="您好，我是 SmartOps 智能客服，很高兴为您服务。\n"
                     "您可以咨询产品使用、售后政策、订单或设备状态，也可以让我帮您分析数据。",
                type="text",
            )


_fallback_agent: FallbackAgent | None = None


def get_fallback_agent() -> FallbackAgent:
    global _fallback_agent
    if _fallback_agent is None:
        _fallback_agent = FallbackAgent()
    return _fallback_agent
