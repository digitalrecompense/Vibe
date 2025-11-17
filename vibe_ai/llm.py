from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from llama_cpp import Llama

from vibe_ai.config import LLMConfig, PromptConfig


class LocalLlama:
    """Small wrapper around llama.cpp's Python bindings for chat-style prompts."""

    def __init__(self, config: LLMConfig | None = None, prompt_config: PromptConfig | None = None):
        self.config = config or LLMConfig()
        self.prompt_config = prompt_config or PromptConfig()
        model_path = Path(self.config.model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file '{model_path}' missing. Download a GGUF quantized model and update LLM_MODEL_PATH."
            )

        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=self.config.context_window,
            n_threads=self.config.threads,
            n_gpu_layers=self.config.gpu_layers,
            use_mmap=True,
            verbose=False,
        )

    def build_prompt(self, history: Iterable[Tuple[str, str]], message: str) -> str:
        chat_parts: List[str] = [f"<s>[SYSTEM] {self.prompt_config.system_prompt}\n"]
        for user_msg, model_reply in history:
            chat_parts.append(f"[INST] {user_msg} [/INST] {model_reply}\n")
        chat_parts.append(f"[INST] {message} [/INST]")
        return "".join(chat_parts)

    def generate(self, history: Iterable[Tuple[str, str]], message: str) -> str:
        prompt = self.build_prompt(history, message)
        completion = self._llm(
            prompt,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_tokens=self.config.context_window // 2,
            stop=["</s>", "[INST]"],
        )
        return completion["choices"][0]["text"].strip()
