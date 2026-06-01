"""
Gradio Frontend — 3 tabs: Agent, Chatbot, So Sánh.
Trợ lý đi chợ thông minh.
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
# PROVIDER
# ==============================================================

def get_llm():
    """Khởi tạo LLM provider dựa trên .env config."""
    provider = os.getenv("DEFAULT_PROVIDER", "local")

    if provider == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/qwen2.5-3b-instruct-q4_k_m.gguf")
        print(f"🔧 Loading local model: {os.path.basename(model_path)}...")
        return LocalProvider(model_path=model_path)

    elif provider == "google":
        from src.core.gemini_provider import GeminiProvider
        print("🔧 Using Gemini API")
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    else:
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

print("✅ Ready!")


# ==============================================================
# HANDLERS
# ==============================================================

def agent_chat(message, history):
    """Handler cho tab Agent."""
    try:
        return agent.run(message)
    except Exception as e:
        return f"❌ Agent error: {str(e)}"


def chatbot_chat(message, history):
    """Handler cho tab Chatbot."""
    try:
        return chatbot_inst.chat(message)
    except Exception as e:
        return f"❌ Chatbot error: {str(e)}"


def compare(question):
    """Chạy cùng 1 câu trên cả chatbot và agent, trả kết quả song song."""
    if not question or not question.strip():
        return "Vui lòng nhập câu hỏi.", "Vui lòng nhập câu hỏi."

    # Chatbot
    t0 = time.time()
    try:
        cb_ans = chatbot_inst.chat(question)
    except Exception as e:
        cb_ans = f"❌ Error: {e}"
    cb_time = time.time() - t0

    # Agent
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

EXAMPLES = [
    "Tôi muốn nấu phở bò cho 4 người, tính giá giúp tôi",
    "Nấu bún bò Huế cần gì? Nguyên liệu nào hết thì gợi ý thay thế",
    "Tôi có 200,000đ, muốn nấu cơm tấm cho 2 người, đủ không?",
    "Gà kho gừng cần nguyên liệu gì? Kiểm tra giá giúp tôi",
    "Nấu canh chua cá cần gì? Tính giá giúp tôi",
]

COMPARE_EXAMPLES = [
    ["Nấu bún bò Huế cần gì? Nguyên liệu hết thì thay thế, tính tổng giá"],
    ["Sinh viên có 150,000đ, gợi ý món nấu tiết kiệm"],
    ["Tôi muốn nấu phở bò cho 4 người, kiểm kho và tính giá giúp tôi"],
]

with gr.Blocks(
    title="🍜 Trợ Lý Đi Chợ Thông Minh",
    theme=gr.themes.Soft(),
) as demo:

    gr.Markdown("# 🍜 Trợ Lý Đi Chợ Thông Minh")
    gr.Markdown(
        "So sánh **Chatbot** (không có tools) vs **ReAct Agent** (có tools truy cập database cửa hàng)"
    )

    with gr.Tabs():

        # ─── Tab 1: Agent ───
        with gr.TabItem("🤖 ReAct Agent"):
            gr.Markdown(
                "*Agent có thể: tra công thức, kiểm kho, tính giá, gợi ý thay thế. "
                "Dữ liệu từ database cửa hàng.*"
            )
            gr.ChatInterface(
                fn=agent_chat,
                examples=EXAMPLES,
                type="messages",
            )

        # ─── Tab 2: Chatbot ───
        with gr.TabItem("💬 Chatbot Baseline"):
            gr.Markdown(
                "*Chatbot chỉ dùng kiến thức chung, KHÔNG truy cập database cửa hàng. "
                "Cùng nhiệm vụ như Agent nhưng không có tools.*"
            )
            gr.ChatInterface(
                fn=chatbot_chat,
                examples=EXAMPLES,
                type="messages",
            )

        # ─── Tab 3: So sánh ───
        with gr.TabItem("📊 So Sánh"):
            gr.Markdown("### Chạy cùng 1 câu trên cả hai — thấy ngay sự khác biệt")

            with gr.Row():
                compare_input = gr.Textbox(
                    label="Câu hỏi",
                    placeholder="Vd: Nấu bún bò Huế, kiểm kho và tính giá giúp tôi",
                    scale=4,
                )
                compare_btn = gr.Button("🔍 So sánh", variant="primary", scale=1)

            with gr.Row():
                chatbot_out = gr.Textbox(label="💬 Chatbot (không tools)", lines=15)
                agent_out = gr.Textbox(label="🤖 Agent (có tools)", lines=15)

            compare_btn.click(
                compare,
                inputs=compare_input,
                outputs=[chatbot_out, agent_out],
            )

            gr.Examples(
                examples=COMPARE_EXAMPLES,
                inputs=compare_input,
            )

    gr.Markdown("---")
    gr.Markdown("*Lab 3 — Chatbot vs ReAct Agent — Agentic AI Course — VinUni*")


if __name__ == "__main__":
    demo.launch(share=False)
    # share=True nếu muốn link public cho instructor
