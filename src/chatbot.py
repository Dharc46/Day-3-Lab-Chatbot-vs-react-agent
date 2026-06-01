from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class SimpleChatbot:
    """Chatbot đơn giản KHÔNG có tools — baseline để so sánh."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def chat(self, user_input: str) -> str:
        logger.log_event("CHATBOT_START", {"input": user_input})
        system_prompt = (
            "Bạn là trợ lý mua sắm tại cửa hàng thực phẩm Việt Nam. "
            "Giúp khách hàng tìm công thức nấu ăn, kiểm tra nguyên liệu, "
            "tính giá tiền, và gợi ý thay thế khi cần."
        )
        try:
            result = self.llm.generate(user_input, system_prompt=system_prompt)
            logger.log_event("CHATBOT_END", {
                "tokens": result.get("usage", {}),
                "latency_ms": result.get("latency_ms", 0),
            })
            return result["content"]
        except Exception as e:
            logger.log_event("CHATBOT_ERROR", {"error": str(e)})
            return f"Lỗi: {str(e)}"