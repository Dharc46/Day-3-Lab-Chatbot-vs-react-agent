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
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    if provider == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    if provider == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv(
                "LOCAL_MODEL_PATH",
                "./models/qwen2.5-3b-instruct-q4_k_m.gguf",
            ),
        )
    from src.core.openai_provider import OpenAIProvider
    return OpenAIProvider(
        model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

from src.agent.agent import ReActAgent
from src.chatbot import SimpleChatbot

print("=" * 50)
print("🍜 Trợ Lý Đi Chợ Thông Minh — Starting...")
print("=" * 50)

llm = get_llm()
agent = ReActAgent(llm=llm, tools=TOOL_REGISTRY, max_steps=7)
chatbot_inst = SimpleChatbot(llm=llm)
print("✅ Ready!")

# ==============================================================
# HANDLERS
# ==============================================================
def agent_chat(message, history):
    return agent.run(message)

def chatbot_chat(message, history):
    return chatbot_inst.chat(message)

def compare(question):
    if not question or not question.strip():
        return "Vui lòng nhập câu hỏi.", ""

    t0 = time.time()
    cb_ans = chatbot_inst.chat(question)
    cb_time = time.time() - t0

    t0 = time.time()
    ag_ans = agent.run(question)
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
    "Nấu bún bò Huế cần gì? Nguyên liệu hết thì gợi ý thay thế",
    "Tôi có 200,000đ, muốn nấu cơm tấm cho 2 người, đủ không?",
    "Gà kho gừng cần nguyên liệu gì?",
]

with gr.Blocks() as demo:
    gr.Markdown("# 🍜 Trợ Lý Đi Chợ Thông Minh")
    gr.Markdown("So sánh **Chatbot** (không tools) vs **ReAct Agent** (có tools)")

    with gr.Tabs():
        with gr.TabItem("🤖 ReAct Agent"):
            gr.Markdown("*Agent tra công thức, kiểm kho, tính giá, gợi ý thay thế.*")
            gr.ChatInterface(fn=agent_chat, examples=EXAMPLES)

        with gr.TabItem("💬 Chatbot Baseline"):
            gr.Markdown("*Chatbot chỉ dùng kiến thức chung, KHÔNG truy cập database.*")
            gr.ChatInterface(fn=chatbot_chat, examples=EXAMPLES)

        with gr.TabItem("📊 So Sánh"):
            gr.Markdown("### Chạy cùng 1 câu trên cả hai — thấy ngay sự khác biệt")
            with gr.Row():
                compare_input = gr.Textbox(
                    label="Câu hỏi", scale=4,
                    placeholder="Vd: Nấu bún bò Huế, kiểm kho + tính giá",
                )
                compare_btn = gr.Button("🔍 So sánh", variant="primary", scale=1)
            with gr.Row():
                chatbot_out = gr.Textbox(label="💬 Chatbot", lines=12)
                agent_out = gr.Textbox(label="🤖 Agent", lines=12)
            compare_btn.click(
                compare,
                inputs=compare_input,
                outputs=[chatbot_out, agent_out],
            )
            gr.Examples(
                examples=[
                    ["Nấu bún bò Huế, nguyên liệu hết thì thay, tính tổng giá"],
                    ["Sinh viên có 150,000đ, gợi ý món tiết kiệm"],
                ],
                inputs=compare_input,
            )

    gr.Markdown("---\n*Lab 3 — Agentic AI — VinUni*")

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(share=False)