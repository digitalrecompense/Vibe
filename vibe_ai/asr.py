from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

import av
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from vibe_ai.config import VoiceConfig


class SpeechToText:
    """Wrapper around faster-whisper for low-latency speech recognition."""

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self._model: Optional[WhisperModel] = None

    def _normalize_audio(self, audio_path: str) -> Path:
        """Convert input audio to a mono wav the Whisper model can ingest reliably."""

        source = Path(audio_path)
        target = Path(tempfile.gettempdir()) / f"vibe_norm_{uuid4().hex}.wav"

        with av.open(str(source)) as container:
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono",
                rate=self.config.sample_rate,
            )
            samples = []
            for frame in container.decode(audio=0):
                resampled = resampler.resample(frame)
                if not isinstance(resampled, list):
                    resampled = [resampled]
                for chunk in resampled:
                    array = chunk.to_ndarray().squeeze()
                    samples.append(array.astype("float32") / 32768.0)

        if not samples:
            raise ValueError("No audio frames decoded from input stream")

        audio = np.concatenate(samples)
        sf.write(target, audio, self.config.sample_rate)
        return target

    def _load(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self.config.stt_model, device=self.config.device or "auto")
        return self._model

    def transcribe(self, audio_path: str) -> str:
        model = self._load()
        normalized = self._normalize_audio(audio_path)
        try:
            segments, _ = model.transcribe(str(normalized), language="en")
            text_parts: Iterable[str] = (segment.text.strip() for segment in segments)
            return " ".join(text_parts)
        finally:
            normalized.unlink(missing_ok=True)
