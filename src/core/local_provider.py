import time
import os
from typing import Dict, Any, Optional, Generator
from llama_cpp import Llama
from src.core.llm_provider import LLMProvider


class LocalProvider(LLMProvider):
    """LLM Provider for local GGUF models via llama-cpp-python."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        super().__init__(model_name=os.path.basename(model_path))
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False,
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=1024,
            stop=["Observation:"],
        )

        latency_ms = int((time.time() - start_time) * 1000)
        content = response["choices"][0]["message"]["content"].strip()
        usage = response["usage"]

        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
            },
            "latency_ms": latency_ms,
            "provider": "local",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=1024,
            stop=["Observation:"],
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                yield delta["content"]