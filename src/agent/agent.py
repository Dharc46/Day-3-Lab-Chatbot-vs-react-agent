"""
ReAct Agent — Final Version.
Design: short prompt + smart code handling edge cases.
Instead of bloating the prompt with rules, we handle:
  - Input validation in run() 
  - "Not found" detection in code (force Final Answer)
  - Chinese detection as post-processing
  - Duplicate calls in code
"""

import re
from typing import List, Dict, Any
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """ReAct Agent: Thought -> Action -> Observation loop."""

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 7):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps

    def get_system_prompt(self) -> str:
        tool_desc = "\n".join(
            f"- {t['name']}: {t['description']}" for t in self.tools
        )
        return f"""CRITICAL: Final Answer MUST be in Vietnamese. NEVER Chinese.

You are a grocery shopping assistant at a Vietnamese food store.
Help customers find recipes, check ingredients, calculate prices, suggest substitutes.

TOOLS:
{tool_desc}

FORMAT:
Thought: <reasoning>
Action: tool_name(<argument>)
Observation: <wait for system>
... repeat ...
Final Answer: <response in Vietnamese>

RULES:
1. One tool per turn. Wait for Observation.
2. search_recipe: pass ONLY dish name (e.g. "bún bò Huế").
3. If ingredient is HẾT HÀNG, call suggest_substitute.
4. Unrelated questions: decline politely in Final Answer, no tools.

PRIORITY: search_recipe → check_inventory → suggest_substitute → calculate_price

EXAMPLE:
User: Nấu gà kho gừng, tính giá giúp tôi.
Thought: Need recipe first.
Action: search_recipe(gà kho gừng)
Observation: {{"name": "Gà Kho Gừng", "servings": 3, "ingredients": [...]}}
Thought: Got recipe. Calculate price.
Action: calculate_price(đùi gà, gừng, nước mắm, đường, tỏi, tiêu, hành tím)
Observation: TỔNG ƯỚC TÍNH: 185,000đ
Thought: Done.
Final Answer: Món Gà Kho Gừng cho 3 người, tổng khoảng 185,000đ."""

    # ==============================================================
    # PRE-PROCESSING — validate input before calling LLM
    # ==============================================================
    def _validate_input(self, user_input: str) -> str | None:
        """Return error message if input is invalid, None if OK."""
        text = user_input.strip()
        if not text:
            return "Vui lòng nhập câu hỏi."
        if re.search(r'-\d{3,}', text):
            return "Xin lỗi, số tiền không hợp lệ. Vui lòng nhập số dương."
        if len(text) < 3:
            return "Vui lòng nhập câu hỏi rõ hơn."
        return None

    # ==============================================================
    # POST-PROCESSING — fix output issues
    # ==============================================================
    def _has_chinese(self, text: str) -> bool:
        """Detect Chinese characters in text."""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _count_not_found(self, text: str) -> int:
        """Count how many 'not found' results appeared."""
        return text.lower().count("không tìm thấy")

    # ==============================================================
    # MAIN REACT LOOP
    # ==============================================================
    def run(self, user_input: str) -> str:
        # Pre-validate
        error = self._validate_input(user_input)
        if error:
            return error

        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
        })

        accumulated = f"User: {user_input}\n"
        steps = 0
        called_tools = []
        not_found_count = 0

        while steps < self.max_steps:
            steps += 1

            # 1. Call LLM
            try:
                result = self.llm.generate(
                    prompt=accumulated,
                    system_prompt=self.get_system_prompt(),
                )
            except Exception as e:
                logger.log_event("LLM_ERROR", {"step": steps, "error": str(e)})
                return f"Lỗi khi gọi LLM: {str(e)}"

            text = result["content"]

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

            # 2. Check Final Answer
            if "Final Answer:" in text:
                final = text.split("Final Answer:")[-1].strip()

                # Post-process: Chinese detection → retry once
                if self._has_chinese(final) and steps < self.max_steps:
                    accumulated += f"{text}\n(Viết lại Final Answer bằng tiếng Việt. Không dùng tiếng Trung.)\n"
                    logger.log_event("CHINESE_DETECTED", {"step": steps})
                    continue

                logger.log_event("AGENT_END", {"steps": steps, "status": "success"})
                return final

            # 3. Parse Action
            match = re.search(r"Action:\s*(\w+)\((.+?)\)", text)
            if match:
                tool_name = match.group(1)
                tool_args = match.group(2).strip().strip("\"'")

                # Duplicate check
                call_key = (tool_name, tool_args)
                if call_key in called_tools:
                    accumulated += (
                        f"{text}\nObservation: Already called {tool_name}(\"{tool_args}\"). "
                        f"Use Final Answer now.\n"
                    )
                    logger.log_event("DUPLICATE_CALL", {
                        "step": steps, "tool": tool_name, "args": tool_args,
                    })
                    continue

                called_tools.append(call_key)
                logger.log_event("TOOL_CALL", {
                    "step": steps, "tool": tool_name, "args": tool_args,
                })

                # Execute
                observation = self._execute_tool(tool_name, tool_args)
                logger.log_event("TOOL_RESULT", {
                    "step": steps, "tool": tool_name, "result": observation[:300],
                })

                # Track "not found" — if too many, force stop
                if "không tìm thấy" in observation.lower():
                    not_found_count += 1
                if not_found_count >= 2:
                    accumulated += f"{text}\nObservation: {observation}\n"
                    accumulated += (
                        "(Đã tìm nhiều lần không có kết quả. "
                        "Hãy viết Final Answer gợi ý các món có sẵn cho khách.)\n"
                    )
                    logger.log_event("FORCE_STOP", {"step": steps, "reason": "too_many_not_found"})
                    continue

                accumulated += f"{text}\nObservation: {observation}\n"
            else:
                # No valid Action found
                accumulated += (
                    f"{text}\n(Use format: Action: tool_name(arg) or Final Answer: ...)\n"
                )
                logger.log_event("PARSE_ERROR", {"step": steps, "raw": text[:300]})

        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return "Xin lỗi, không hoàn thành được yêu cầu trong giới hạn bước cho phép."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                try:
                    return tool["function"](args)
                except Exception as e:
                    return f"Error calling {tool_name}: {str(e)}"
        available = ", ".join(t["name"] for t in self.tools)
        return f"Tool '{tool_name}' does not exist. Available: {available}"