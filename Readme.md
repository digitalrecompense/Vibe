# Vibe: local, voice-aware assistant

This repo packages a practical prototype you can run on Windows 11 with an RTX 3060 Ti and CPU fallback. It blends the local-first ideas used in the RAiTHE projects (small, offline-friendly components you can compose) into a single assistant that can:

- Chat using a quantized GGUF LLM via `llama-cpp-python`.
- Transcribe `.wav` audio with `faster-whisper`.
- Speak responses with Coqui `TTS`.
- Run fully offline after models are downloaded.

## Quick start (Windows 11, Python 3.11.9 recommended)

1. **Clone and open the project**
   ```powershell
   git clone <this repo>
   cd Vibe
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install runtime dependencies** (prebuilt wheels exist for Windows; if `llama-cpp-python` builds from source, install [Visual Studio Build Tools] first):
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Download a quantized model** (fits in 8 GB VRAM/CPU RAM). For example, Mistral Instruct Q4:
   ```powershell
   mkdir models
   curl -L -o models/mistral-7b-instruct-v0.2.Q4_K_M.gguf \
     https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   ```

4. **Run a one-off prompt**
   ```powershell
   python run_assistant.py "Explain how RAiTHE's modularity can guide a new toolchain."
   ```

5. **Interactive chat**
   ```powershell
   python run_assistant.py
   # type messages; use "exit" or Ctrl+C to leave
   ```

6. **Add voice**
   - **Transcribe an input file and answer**
     ```powershell
     python run_assistant.py --audio sample.wav "Summarize the meeting notes."
     ```
   - **Speak the reply to a .wav file**
     ```powershell
     python run_assistant.py "Create a 3-step study plan for linear algebra." --speak output.wav
     ```

7. **Launch the immersive “Nebula” UI**
   ```powershell
   # start the FastAPI server that also serves the animated UI
   python -m uvicorn vibe_ai.server:app --host 0.0.0.0 --port 8000
   # then visit http://localhost:8000 in your browser
   ```
   - The glassy chat surface includes a microphone-reactive cloud (using Web Audio) and a “Speak responses” toggle.
   - Use the 🎙️ button to record a voice question; it will be transcribed locally via `faster-whisper` and injected into the prompt box.
   - Flip **Open mic** on to keep listening continuously. Each phrase is transcribed in the background and auto-sent so you can stay hands-free.

## Configuration knobs

Environment variables let you tune speed/quality for your 3060 Ti:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_MODEL_PATH` | `models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` | GGUF model to load |
| `LLM_CTX` | `4096` | Context window tokens |
| `LLM_THREADS` | CPU threads for llama.cpp |
| `LLM_GPU_LAYERS` | `20` | Layers to offload to GPU (lower for older cards) |
| `LLM_TEMP` | `0.7` | Sampling temperature |
| `LLM_TOP_P` | `0.95` | Top-p nucleus sampling |
| `STT_MODEL` | `medium.en` | faster-whisper size (e.g., `small`, `large-v3`) |
| `TTS_MODEL` | `tts_models/en/vctk/vits` | Coqui TTS voice |
| `VOICE_DEVICE` | auto | Force `cuda` or `cpu` for STT/TTS |
| `AUDIO_SAMPLE_RATE` | `16000` | Sample rate used when normalizing microphone clips |

Adjust `LLM_GPU_LAYERS` upward (e.g., 35) to move more of the model to the 3060 Ti; reduce if you hit VRAM limits.

## How it fits together

- **`vibe_ai/config.py`** – centralizes model paths and prompt defaults, following RAiTHE's config-first style.
- **`vibe_ai/llm.py`** – minimal chat wrapper on `llama-cpp-python` using an instruction-tuned prompt.
- **`vibe_ai/asr.py`** – lazy-loaded `faster-whisper` pipeline for low-latency speech-to-text, with PyAV-normalized audio for reliable Windows decoding.
- **`vibe_ai/tts.py`** – Coqui TTS wrapper for offline speech synthesis.
- **`vibe_ai/cli.py` & `run_assistant.py`** – CLI glue for text-only or voice-enabled sessions.

## Audio pipeline reliability (Windows)

- PyAV is pinned in `requirements.txt` so browser-recorded `.webm` blobs are normalized to 16 kHz mono WAV before reaching `faster-whisper`. Install the latest [FFmpeg builds for Windows](https://www.gyan.dev/ffmpeg/builds/) and ensure `ffmpeg.exe` is on your `PATH` for best results.
- If you prefer a different sample rate, set `AUDIO_SAMPLE_RATE` to match your microphone or interface; the resampler will retarget automatically.

## Extending the prototype

- Swap models by changing `LLM_MODEL_PATH` and `TTS_MODEL`.
- Add retrieval or tool-use by enriching `vibe_ai/llm.py` with your own context strings.
- To expose an API, wrap `LocalLlama.generate` in FastAPI or Flask; the components are decoupled to mirror RAiTHE's modular design ethos.

Enjoy experimenting on your hardware—everything runs locally once the models are downloaded.
