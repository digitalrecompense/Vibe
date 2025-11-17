from __future__ import annotations

import asyncio
import base64
import tempfile
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vibe_ai.asr import SpeechToText
from vibe_ai.config import LLMConfig, PromptConfig, VoiceConfig
from vibe_ai.llm import LocalLlama
from vibe_ai.tts import TextToSpeech

app = FastAPI(title="Vibe UI", version="0.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurn(BaseModel):
    user: str
    assistant: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = Field(default_factory=list)
    speak: bool = False


class ChatResponse(BaseModel):
    reply: str
    audio_base64: str | None = None


class TranscriptionResponse(BaseModel):
    text: str


_llm_instance: LocalLlama | None = None
_voice_config = VoiceConfig()
_stt_instance: SpeechToText | None = None
_tts_instance: TextToSpeech | None = None


def _get_llm() -> LocalLlama:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LocalLlama(LLMConfig(), PromptConfig())
    return _llm_instance


def _get_stt() -> SpeechToText:
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = SpeechToText(_voice_config)
    return _stt_instance


def _get_tts() -> TextToSpeech:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech(_voice_config)
    return _tts_instance


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    index_path = Path("web/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI assets not found. Run from repo root.")
    return index_path.read_text(encoding="utf-8")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    history: List[Tuple[str, str]] = [(turn.user, turn.assistant) for turn in request.history]
    llm = _get_llm()
    reply = await asyncio.to_thread(llm.generate, history, request.message)

    audio_b64: str | None = None
    if request.speak:
        tts = _get_tts()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / f"vibe_reply_{uuid4().hex}.wav"
            await asyncio.to_thread(tts.synthesize, reply, output_path)
            audio_bytes = output_path.read_bytes()
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    return ChatResponse(reply=reply, audio_base64=audio_b64)


@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...)) -> TranscriptionResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file uploaded")

    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        temp_path = Path(tmp.name)

    stt = _get_stt()
    text = await asyncio.to_thread(stt.transcribe, str(temp_path))
    temp_path.unlink(missing_ok=True)
    return TranscriptionResponse(text=text)


app.mount("/static", StaticFiles(directory="web"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
