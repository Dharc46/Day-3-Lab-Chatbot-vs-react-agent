"""
ReAct Agent V2 — Grocery Shopping Assistant.
Changes from v1:
  - System prompt in English (better instruction following for small models)
  - Added few-shot example
  - Added tool priority rules
  - Added "dish name only" rule for search_recipe
  - Improved parse error recovery
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
        return f"""You are a smart grocery shopping assistant at a Vietnamese food store.
Your job: help customers find recipes, check ingredient availability, calculate prices, and suggest substitutes.

TOOLS:
{tool_desc}

RESPONSE FORMAT (follow exactly):
Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)
Observation: <result from tool — do NOT write this yourself, wait for the system>
... (repeat Thought/Action/Observation as needed) ...
Final Answer: <your complete response to the customer in Vietnamese>

RULES:
1. Call only ONE tool per turn.
2. WAIT for the Observation before your next Thought.
3. When you have enough information, write Final Answer.
4. If an ingredient is out of stock (HẾT HÀNG), you MUST call suggest_substitute for it.
5. For search_recipe, pass ONLY the dish name (e.g. "bún bò Huế"), do NOT add extra words.
6. Do NOT call the same tool with the same argument twice.
7. Always respond to the customer in Vietnamese.

TOOL PRIORITY ORDER:
1. search_recipe → find what ingredients are needed
2. check_inventory → check key ingredients (especially meat, seafood)
3. suggest_substitute → for any out-of-stock items
4. calculate_price → calculate total cost last

EXAMPLE:
User: Tôi muốn nấu gà kho gừng, tính giá giúp tôi.
Thought: The customer wants to cook Gà Kho Gừng. First I need to find the recipe.
Action: search_recipe(gà kho gừng)
Observation: {{"name": "Gà Kho Gừng", "servings": 3, "ingredients": [{{"item": "đùi gà", "quantity": "500g"}}, ...], "time": "45 phút"}}
Thought: I have the recipe with 7 ingredients. Now I'll calculate the total price.
Action: calculate_price(đùi gà, gừng, nước mắm, đường, tỏi, tiêu, hành tím)
Observation: CHI TIẾT: ... TỔNG ƯỚC TÍNH: 185,000đ
Thought: I have all the information needed to answer.
Final Answer: Món Gà Kho Gừng cho 3 người cần 7 nguyên liệu, tổng chi phí ước tính khoảng 185,000đ. Các nguyên liệu gồm: đùi gà (500g), gừng (1 củ to), nước mắm, đường, tỏi, tiêu, hành tím."""

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
        })

        accumulated = f"User: {user_input}\n"
        steps = 0
        called_tools = []  # Track (tool, args) to prevent duplicate calls

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

            # 2. Check for Final Answer
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

                # V2: prevent duplicate tool calls
                call_key = (tool_name, tool_args)
                if call_key in called_tools:
                    accumulated += (
                        f"{text}\nObservation: You already called {tool_name}(\"{tool_args}\") "
                        f"and it didn't work. Try a different argument or use Final Answer.\n"
                    )
                    logger.log_event("DUPLICATE_CALL", {
                        "step": steps,
                        "tool": tool_name,
                        "args": tool_args,
                    })
                    continue

                called_tools.append(call_key)

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

                accumulated += f"{text}\nObservation: {observation}\n"
            else:
                # Parse failed
                accumulated += (
                    f"{text}\n"
                    f"(You must use the format: Action: tool_name(argument) "
                    f"or Final Answer: your response)\n"
                )
                logger.log_event("PARSE_ERROR", {
                    "step": steps,
                    "raw": text[:300],
                })

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