import os
from dotenv import load_dotenv

from src.agent.agent import GroceryReActAgent


def get_llm():
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()

    if provider == "google":
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=os.getenv("DEFpython main.pyAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    if provider == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(
            model_name=os.getenv("DEFAULT_MODEL", "local-model"),
            api_key=None,
        )

    from src.core.openai_provider import OpenAIProvider

    return OpenAIProvider(
        model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def main():
    load_dotenv()

    llm = get_llm()
    agent = GroceryReActAgent(llm=llm)

    print("Trợ Lý Đi Chợ Thông Minh — ReAct Agent")
    print("Gõ 'exit' để thoát.\n")

    while True:
        user_input = input("Bạn: ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Đã thoát.")
            break

        if not user_input:
            continue

        response = agent.run(user_input)
        print("\nAgent:")
        print(response)
        print("-" * 60)


if __name__ == "__main__":
    main()