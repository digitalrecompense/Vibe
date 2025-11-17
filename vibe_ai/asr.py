from __future__ import annotations

from typing import Iterable, Optional

from faster_whisper import WhisperModel

from vibe_ai.config import VoiceConfig


class SpeechToText:
    """Wrapper around faster-whisper for low-latency speech recognition."""

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self._model: Optional[WhisperModel] = None

    def _load(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self.config.stt_model, device=self.config.device or "auto")
        return self._model

    def transcribe(self, audio_path: str) -> str:
        model = self._load()
        segments, _ = model.transcribe(audio_path, language="en")
        text_parts: Iterable[str] = (segment.text.strip() for segment in segments)
        return " ".join(text_parts)
