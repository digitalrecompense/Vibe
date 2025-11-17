from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float_from_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class LLMConfig:
    """Configuration for the local LLM backend."""

    model_path: str = os.getenv("LLM_MODEL_PATH", "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
    context_window: int = _int_from_env("LLM_CTX", 4096)
    threads: int = _int_from_env("LLM_THREADS", os.cpu_count() or 4)
    gpu_layers: int = _int_from_env("LLM_GPU_LAYERS", 20)
    temperature: float = _float_from_env("LLM_TEMP", 0.7)
    top_p: float = _float_from_env("LLM_TOP_P", 0.95)


@dataclass
class VoiceConfig:
    """Configuration for speech-to-text and text-to-speech."""

    stt_model: str = os.getenv("STT_MODEL", "medium.en")
    tts_model: str = os.getenv("TTS_MODEL", "tts_models/en/vctk/vits")
    device: Optional[str] = os.getenv("VOICE_DEVICE")


@dataclass
class PromptConfig:
    """Default system prompt for the assistant persona."""

    system_prompt: str = (
        "You are Vibe, a patient AI guide who can teach, explain, and plan with a calm voice. "
        "Be concise, cite steps clearly, and avoid hallucinations by admitting uncertainty." 
        "When summarizing, produce short bullet points."
    )
    starter_messages: List[str] = (
        [
            "Hey there! I'm Vibe. Ask me to explain code, generate plans, or talk through problems.",
            "Voice features are available: you can pass a .wav file to transcribe or synthesize answers to audio.",
        ]
    )
