"""
ReAct Agent: Thought → Action → Observation loop.
Trợ lý đi chợ thông minh với 4 tools.
"""

import re
from typing import List, Dict, Any
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """ReAct Agent: Thought → Action → Observation loop."""

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 7):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps

    def get_system_prompt(self) -> str:
        tool_desc = "\n".join(
            f"- {t['name']}: {t['description']}" for t in self.tools
        )
        return f"""Bạn là trợ lý đi chợ thông minh tại cửa hàng thực phẩm Việt Nam.
Nhiệm vụ: giúp khách tìm công thức, kiểm tra nguyên liệu, tính giá, gợi ý thay thế.

CÔNG CỤ:
{tool_desc}

FORMAT BẮT BUỘC:
Thought: <suy nghĩ bước tiếp>
Action: <tool_name>(<tham_số>)
Observation: <kết quả — KHÔNG tự viết, chờ hệ thống>
... (lặp lại nếu cần) ...
Final Answer: <trả lời khách>

QUY TẮC:
1. Mỗi lượt chỉ gọi MỘT tool.
2. PHẢI đợi Observation rồi mới Thought tiếp.
3. Khi đủ thông tin → viết Final Answer.
4. Nếu nguyên liệu hết hàng → BẮT BUỘC gọi suggest_substitute.
5. KHÔNG BAO GIỜ tự bịa Observation.
"""

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
        })

        accumulated = f"User: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            steps += 1

            # 1. Gọi LLM
            try:
                result = self.llm.generate(
                    prompt=accumulated,
                    system_prompt=self.get_system_prompt(),
                )
            except Exception as e:
                logger.log_event("LLM_ERROR", {"step": steps, "error": str(e)})
                return f"Lỗi khi gọi LLM: {str(e)}"

            text = result["content"]

            # Track metrics
            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            logger.log_event("LLM_RESPONSE", {
                "step": steps,
                "response": text[:500],
                "tokens": result.get("usage", {}),
                "latency_ms": result.get("latency_ms", 0),
            })

            # 2. Final Answer?
            if "Final Answer:" in text:
                final = text.split("Final Answer:")[-1].strip()
                logger.log_event("AGENT_END", {
                    "steps": steps,
                    "status": "success",
                })
                return final

            # 3. Parse Action
            match = re.search(r"Action:\s*(\w+)\((.+?)\)", text)
            if match:
                tool_name = match.group(1)
                tool_args = match.group(2).strip().strip("\"'")

                logger.log_event("TOOL_CALL", {
                    "step": steps,
                    "tool": tool_name,
                    "args": tool_args,
                })

                # 4. Execute tool
                observation = self._execute_tool(tool_name, tool_args)

                logger.log_event("TOOL_RESULT", {
                    "step": steps,
                    "tool": tool_name,
                    "result": observation[:300],
                })

                # 5. Append to accumulated prompt
                accumulated += f"{text}\nObservation: {observation}\n"
            else:
                # Parse failed — nudge the LLM
                accumulated += f"{text}\n"
                accumulated += "(Hãy dùng format: Action: tool_name(args) hoặc Final Answer: ...)\n"
                logger.log_event("PARSE_ERROR", {
                    "step": steps,
                    "raw": text[:300],
                })

        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return "Xin lỗi, không hoàn thành được yêu cầu trong giới hạn bước cho phép."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """Tìm và thực thi tool theo tên."""
        for tool in self.tools:
            if tool["name"] == tool_name:
                try:
                    return tool["function"](args)
                except Exception as e:
                    return f"Lỗi khi gọi {tool_name}: {str(e)}"
        available = ", ".join(t["name"] for t in self.tools)
        return f"Tool '{tool_name}' không tồn tại. Có: {available}"
