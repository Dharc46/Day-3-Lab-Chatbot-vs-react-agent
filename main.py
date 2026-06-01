"""
Entry point — chạy 1 câu demo so sánh chatbot vs agent.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.tools.grocery_tools import TOOL_REGISTRY


def get_llm():
    """Khởi tạo LLM provider dựa trên .env config."""
    provider = os.getenv("DEFAULT_PROVIDER", "local")

    if provider == "local":
        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path and not os.path.isdir(os.path.join(cuda_path, "bin")):
            os.environ.pop("CUDA_PATH", None)
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/qwen2.5-3b-instruct-q4_k_m.gguf")
        print(f"🔧 Provider: local ({os.path.basename(model_path)})")
        return LocalProvider(model_path=model_path)

    elif provider == "google":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key.startswith("AIza"):
            raise ValueError(
                "GEMINI_API_KEY phải bắt đầu bằng 'AIza' (tạo tại https://aistudio.google.com/apikey)."
            )
        model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash-lite")
        print(f"🔧 Provider: google ({model})")
        return GeminiProvider(model_name=model, api_key=api_key)

    else:
        from src.core.openai_provider import OpenAIProvider
        print("🔧 Provider: openai")
        return OpenAIProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )


def main():
    from src.agent.agent import ReActAgent
    from src.chatbot import SimpleChatbot

    llm = get_llm()
    agent = ReActAgent(llm=llm, tools=TOOL_REGISTRY, max_steps=7)
    chatbot = SimpleChatbot(llm=llm)

    query = "Tôi muốn nấu bún bò Huế, kiểm tra nguyên liệu và tính giá giúp tôi"

    print(f"\n📝 Query: {query}")
    print("=" * 60)
    print("💬 CHATBOT:")
    print(chatbot.chat(query))
    print()
    print("=" * 60)
    print("🤖 AGENT:")
    print(agent.run(query))


if __name__ == "__main__":
    main()
