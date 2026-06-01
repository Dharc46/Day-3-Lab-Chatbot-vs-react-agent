"""
Chạy 10 test cases trên chatbot + agent, lưu kết quả.
Tự chạy provider switching nếu có key provider thứ 2.
"""

import sys
import os
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.tools.grocery_tools import TOOL_REGISTRY
from src.agent.agent import ReActAgent
from src.chatbot import SimpleChatbot
from tests.test_scenarios import TEST_CASES


def get_llm(provider_override=None):
    """Khởi tạo LLM provider."""
    provider = provider_override or os.getenv("DEFAULT_PROVIDER", "local")

    if provider == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/qwen2.5-3b-instruct-q4_k_m.gguf")
        return LocalProvider(model_path=model_path)

    elif provider == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    else:
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )


def run_suite(llm, label="default", test_cases=None):
    """Chạy 1 bộ test với 1 provider, trả về list kết quả."""
    cases = test_cases or TEST_CASES
    agent = ReActAgent(llm=llm, tools=TOOL_REGISTRY, max_steps=7)
    cb = SimpleChatbot(llm=llm)
    results = []

    for tc in cases:
        print(f"\n{'=' * 60}")
        print(f"[{label}] TEST {tc['id']} [{tc['type']}]: {tc['input'][:50]}...")

        # Chatbot
        t0 = time.time()
        try:
            cb_ans = cb.chat(tc["input"])
        except Exception as e:
            cb_ans = f"ERROR: {e}"
        cb_ms = int((time.time() - t0) * 1000)

        # Agent
        t0 = time.time()
        try:
            ag_ans = agent.run(tc["input"])
        except Exception as e:
            ag_ans = f"ERROR: {e}"
        ag_ms = int((time.time() - t0) * 1000)

        results.append({
            "id": tc["id"],
            "type": tc["type"],
            "provider": label,
            "input": tc["input"],
            "expected": tc["expected"],
            "chatbot_answer": cb_ans[:300],
            "chatbot_time_ms": cb_ms,
            "agent_answer": ag_ans[:300],
            "agent_time_ms": ag_ms,
        })

        print(f"  💬 Chatbot ({cb_ms}ms): {cb_ans[:80]}...")
        print(f"  🤖 Agent   ({ag_ms}ms): {ag_ans[:80]}...")

    return results


def print_summary(results, label):
    """In tổng hợp kết quả."""
    print(f"\n{'=' * 60}")
    print(f"📊 TỔNG HỢP ({label}) — {len(results)} test cases:")
    avg_cb = sum(r["chatbot_time_ms"] for r in results) / len(results)
    avg_ag = sum(r["agent_time_ms"] for r in results) / len(results)
    print(f"  Chatbot avg latency: {avg_cb:.0f}ms")
    print(f"  Agent   avg latency: {avg_ag:.0f}ms")

    # Count agent errors
    errors = sum(1 for r in results if "ERROR" in r["agent_answer"] or "Xin lỗi" in r["agent_answer"])
    success = len(results) - errors
    print(f"  Agent success rate: {success}/{len(results)} ({100*success/len(results):.0f}%)")


def run_all():
    """Chạy full test suite + provider switching nếu có."""
    # Primary provider
    provider1 = os.getenv("DEFAULT_PROVIDER", "local")
    print(f"🔧 Primary provider: {provider1}")
    llm1 = get_llm(provider1)
    results = run_suite(llm1, label=provider1)
    print_summary(results, provider1)

    # Provider switching (nếu có key thứ 2)
    provider2 = None
    if provider1 == "local":
        # Thử google trước, rồi openai
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if gemini_key and "your_" not in gemini_key:
            provider2 = "google"
        elif openai_key and "your_" not in openai_key:
            provider2 = "openai"
    elif provider1 == "openai":
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key and "your_" not in gemini_key:
            provider2 = "google"
    elif provider1 == "google":
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and "your_" not in openai_key:
            provider2 = "openai"

    if provider2:
        print(f"\n{'=' * 60}")
        print(f"🔄 PROVIDER SWITCHING: chạy thêm 3 test cases với {provider2}")
        llm2 = get_llm(provider2)
        mini_cases = [tc for tc in TEST_CASES if tc["id"] in ("S1", "M2", "E1")]
        results_p2 = run_suite(llm2, label=provider2, test_cases=mini_cases)
        results.extend(results_p2)
        print_summary(results_p2, provider2)
    else:
        print(f"\n⚠️  Không có key provider thứ 2 — bỏ qua provider switching.")

    # Lưu kết quả
    os.makedirs("tests", exist_ok=True)
    output_path = "tests/results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved → {output_path}")


if __name__ == "__main__":
    run_all()
