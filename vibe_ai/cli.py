from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

from vibe_ai.asr import SpeechToText
from vibe_ai.config import LLMConfig, PromptConfig, VoiceConfig
from vibe_ai.llm import LocalLlama
from vibe_ai.tts import TextToSpeech


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vibe: local, voice-aware assistant")
    parser.add_argument("message", nargs="*", help="Prompt to send the assistant. If omitted, an interactive loop starts.")
    parser.add_argument("--audio", type=str, help="Optional path to a .wav file to transcribe before chatting.")
    parser.add_argument("--speak", type=str, help="Save the response as audio at the given path.")
    parser.add_argument("--system", type=str, help="Override the default system prompt for this run.")
    return parser.parse_args()


def interactive_loop(assistant: LocalLlama, voice: VoiceConfig) -> None:
    print("\n".join(PromptConfig().starter_messages))
    history: List[Tuple[str, str]] = []

    while True:
        try:
            user_message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return

        if not user_message:
            continue
        if user_message.lower() in {"quit", "exit"}:
            print("Goodbye!")
            return

        reply = assistant.generate(history, user_message)
        history.append((user_message, reply))
        print(f"Vibe: {reply}\n")


def main() -> None:
    args = parse_args()
    prompt_config = PromptConfig()
    if args.system:
        prompt_config.system_prompt = args.system

    llm = LocalLlama(LLMConfig(), prompt_config)
    voice_config = VoiceConfig()

    user_prompt = " ".join(args.message)
    if args.audio:
        transcript = SpeechToText(voice_config).transcribe(args.audio)
        user_prompt = f"{user_prompt}\n\nTranscription of {args.audio}: {transcript}" if user_prompt else transcript
        print(f"Transcribed audio -> {transcript}")

    if not user_prompt:
        interactive_loop(llm, voice_config)
        return

    response = llm.generate([], user_prompt)
    print(f"Vibe: {response}")

    if args.speak:
        path = TextToSpeech(voice_config).synthesize(response, Path(args.speak))
        print(f"Saved audio to {path}")


if __name__ == "__main__":
    main()
