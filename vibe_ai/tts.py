from __future__ import annotations

from pathlib import Path
from typing import Optional

from TTS.api import TTS

from vibe_ai.config import VoiceConfig


class TextToSpeech:
    """Thin wrapper around Coqui TTS for offline synthesis."""

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self._tts: Optional[TTS] = None

    def _load(self) -> TTS:
        if self._tts is None:
            self._tts = TTS(self.config.tts_model).to(self.config.device or "cpu")
        return self._tts

    def synthesize(self, text: str, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        tts = self._load()
        tts.tts_to_file(text=text, file_path=str(output))
        return output
