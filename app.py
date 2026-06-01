import os
import sys
import time
import gradio as gr
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.grocery_tools import TOOL_REGISTRY

_IS_LOCAL = os.getenv("DEFAULT_PROVIDER", "openai").lower() == "local"


# ==============================================================
# PROVIDER
# ==============================================================
def get_llm():
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()

    if provider == "google":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key.startswith("AIza"):
            raise ValueError(
                "GEMINI_API_KEY không đúng định dạng. "
                "Key từ Google AI Studio phải bắt đầu bằng 'AIza'. "
                "Tạo key tại: https://aistudio.google.com/apikey"
            )
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-lite")
        print(f"🔧 Using Gemini API ({model})")
        return GeminiProvider(model_name=model, api_key=api_key)

    if provider == "local":
        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path and not os.path.isdir(os.path.join(cuda_path, "bin")):
            os.environ.pop("CUDA_PATH", None)
        from src.core.local_provider import LocalProvider
        model_path = os.getenv(
            "LOCAL_MODEL_PATH",
            "./models/qwen2.5-3b-instruct-q4_k_m.gguf",
        )
        print(f"🔧 Loading local model: {os.path.basename(model_path)}...")
        return LocalProvider(model_path=model_path)

    from src.core.openai_provider import OpenAIProvider
    print("🔧 Using OpenAI API")
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
_agent_max_steps = int(os.getenv("AGENT_MAX_STEPS", "4" if _IS_LOCAL else "7"))
agent = ReActAgent(llm=llm, tools=TOOL_REGISTRY, max_steps=_agent_max_steps)
chatbot_inst = SimpleChatbot(llm=llm)
print("✅ Ready!")


# ==============================================================
# HANDLERS
# ==============================================================
_LOCAL_WAIT_MSG = (
    "⏳ **Model local (CPU)** đang xử lý — thường **1–3 phút** với Agent.\n\n"
    "Vui lòng **không gửi lại** hoặc mở tab khác cùng lúc."
)


def agent_chat(message, history):
    if _IS_LOCAL:
        yield _LOCAL_WAIT_MSG
    try:
        yield agent.run(message)
    except Exception as e:
        yield f"❌ Agent error: {str(e)}"


def chatbot_chat(message, history):
    if _IS_LOCAL:
        yield "⏳ Model local đang trả lời (~30–90 giây). Vui lòng đợi..."
    try:
        yield chatbot_inst.chat(message)
    except Exception as e:
        yield f"❌ Chatbot error: {str(e)}"


def compare(question):
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
EXAMPLES = [
    "Tôi muốn nấu phở bò cho 4 người, tính giá giúp tôi",
    "Nấu bún bò Huế cần gì? Nguyên liệu hết thì gợi ý thay thế",
    "Tôi có 200,000đ, muốn nấu cơm tấm cho 2 người, đủ không?",
    "Gà kho gừng cần nguyên liệu gì?",
]

with gr.Blocks(title="🍜 Trợ Lý Đi Chợ Thông Minh") as demo:
    gr.Markdown("# 🍜 Trợ Lý Đi Chợ Thông Minh")
    gr.Markdown("So sánh **Chatbot** (không tools) vs **ReAct Agent** (có tools)")
    if _IS_LOCAL:
        gr.Markdown(
            "⚠️ **Model local trên CPU** — phản hồi chậm (Agent ~1–3 phút). "
            "Không gửi nhiều câu cùng lúc."
        )

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
    demo.queue(default_concurrency_limit=1).launch(
        share=False,
        theme=gr.themes.Soft(),
    )
