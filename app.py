"""
Gradio Frontend — Lab 3: Chatbot vs ReAct Agent
3 tab: Agent chat, Chatbot chat, So Sánh side-by-side (TEAM_GUIDE_FINAL)
"""

import os
import sys
import time

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.grocery_tools import TOOL_REGISTRY


# ==============================================================
# PROVIDER (khớp tests/run_tests.py trong TEAM_GUIDE)
# ==============================================================

def get_llm(provider_override: str | None = None):
    """Khởi tạo LLM provider từ .env hoặc override (openai | google | local)."""
    provider = (provider_override or os.getenv("DEFAULT_PROVIDER", "openai")).lower()

    if provider == "google":
        from src.core.gemini_provider import GeminiProvider

        print("🔧 Using Gemini API")
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    if provider == "local":
        from src.core.local_provider import LocalProvider

        model_path = os.getenv(
            "LOCAL_MODEL_PATH",
            "./models/Phi-3-mini-4k-instruct-q4.gguf",
        )
        print(f"🔧 Loading local model: {os.path.basename(model_path)}...")
        return LocalProvider(model_path=model_path)

    from src.core.openai_provider import OpenAIProvider

    print("🔧 Using OpenAI API")
    return OpenAIProvider(
        model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


print("=" * 50)
print("🍜 Trợ Lý Đi Chợ Thông Minh — Starting...")
print("=" * 50)

llm = get_llm()

from src.agent.agent import ReActAgent
from src.chatbot import SimpleChatbot

agent = ReActAgent(llm=llm, tools=TOOL_REGISTRY, max_steps=7)
chatbot_inst = SimpleChatbot(llm=llm)

_provider = os.getenv("DEFAULT_PROVIDER", "openai")
print(f"✅ Ready! Provider={_provider}, model={llm.model_name}")


# ==============================================================
# HANDLERS
# ==============================================================

def agent_chat(message, history):
    """Handler tab Agent."""
    try:
        return agent.run(message)
    except Exception as e:
        return f"❌ Agent error: {str(e)}"


def chatbot_chat(message, history):
    """Handler tab Chatbot."""
    try:
        return chatbot_inst.chat(message)
    except Exception as e:
        return f"❌ Chatbot error: {str(e)}"


def compare(question):
    """Chạy cùng câu hỏi trên chatbot và agent — side-by-side."""
    if not question or not question.strip():
        return "Vui lòng nhập câu hỏi.", "Vui lòng nhập câu hỏi."

    t0 = time.time()
    try:
        cb_ans = chatbot_inst.chat(question)
    except Exception as e:
        cb_ans = f"❌ Error: {e}"
    cb_time = time.time() - t0

    t0 = time.time()
    try:
        ag_ans = agent.run(question)
    except Exception as e:
        ag_ans = f"❌ Error: {e}"
    ag_time = time.time() - t0

    return (
        f"⏱️ {cb_time:.1f}s\n\n{cb_ans}",
        f"⏱️ {ag_time:.1f}s\n\n{ag_ans}",
    )


# ==============================================================
# UI
# ==============================================================

# Ví dụ chung cho tab Agent / Chatbot
CHAT_EXAMPLES = [
    "Phở bò cần gì?",
    "Tôi muốn nấu phở bò cho 4 người, tính giá giúp tôi",
    "Nấu bún bò Huế cần gì? Nguyên liệu nào hết thì gợi ý thay thế",
    "Tôi có 200,000đ, muốn nấu cơm tấm cho 2 người, đủ không?",
]

# Live Demo (+5 bonus) — tab So Sánh (TEAM_GUIDE Phase 4)
COMPARE_EXAMPLES = [
    ["Phở bò cần gì?"],
    ["Bún bò Huế, hết thì thay, tính giá"],
]

with gr.Blocks(
    title="🍜 Trợ Lý Đi Chợ Thông Minh",
    theme=gr.themes.Soft(),
) as demo:

    gr.Markdown("# 🍜 Trợ Lý Đi Chợ Thông Minh")
    gr.Markdown(
        "So sánh **Chatbot** (không tools) vs **ReAct Agent** "
        "(có tools: công thức, kho, giá, thay thế)."
    )
    gr.Markdown(
        f"*Provider: `{_provider}` · Model: `{llm.model_name}` · "
        f"Logs: `logs/` (grep `LLM_METRIC`)*"
    )

    with gr.Tabs():

        # ─── Tab 1: Agent chat ───
        with gr.TabItem("🤖 Agent"):
            gr.Markdown(
                "*ReAct Agent — tra công thức, kiểm kho, tính giá, gợi ý thay thế "
                "(dữ liệu mock cửa hàng).*"
            )
            gr.ChatInterface(
                fn=agent_chat,
                examples=CHAT_EXAMPLES,
                type="messages",
            )

        # ─── Tab 2: Chatbot chat ───
        with gr.TabItem("💬 Chatbot"):
            gr.Markdown(
                "*Chatbot baseline — chỉ LLM, **không** gọi tools / database cửa hàng.*"
            )
            gr.ChatInterface(
                fn=chatbot_chat,
                examples=CHAT_EXAMPLES,
                type="messages",
            )

        # ─── Tab 3: So sánh side-by-side ───
        with gr.TabItem("📊 So Sánh"):
            gr.Markdown(
                "### Live demo (gợi ý cho instructor)\n"
                "1. **\"Phở bò cần gì?\"** → cả hai thường trả lời được.\n"
                "2. **\"Bún bò Huế, hết thì thay, tính giá\"** → Agent dùng tools, "
                "thường chính xác hơn Chatbot."
            )

            with gr.Row():
                compare_input = gr.Textbox(
                    label="Câu hỏi",
                    placeholder="Vd: Bún bò Huế, hết thì thay, tính giá",
                    scale=4,
                )
                compare_btn = gr.Button("🔍 So sánh", variant="primary", scale=1)

            with gr.Row():
                chatbot_out = gr.Textbox(
                    label="💬 Chatbot (không tools)",
                    lines=15,
                )
                agent_out = gr.Textbox(
                    label="🤖 Agent (có tools)",
                    lines=15,
                )

            compare_btn.click(
                compare,
                inputs=compare_input,
                outputs=[chatbot_out, agent_out],
            )
            compare_input.submit(
                compare,
                inputs=compare_input,
                outputs=[chatbot_out, agent_out],
            )

            gr.Examples(
                examples=COMPARE_EXAMPLES,
                inputs=compare_input,
                label="Ví dụ demo",
            )

    gr.Markdown("---")
    gr.Markdown(
        "*Lab 3 — Chatbot vs ReAct Agent — Agentic AI Course — VinUni*"
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
    )
    # share=True nếu cần link public cho instructor
