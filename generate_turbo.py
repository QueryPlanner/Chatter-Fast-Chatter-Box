#!/usr/bin/env python3
"""
Generate speech with Chatterbox-Turbo.

Without --ref, the pretrained checkpoint's built-in voice (conds.pt) is used.
With --ref, zero-shot cloning applies (>5s WAV recommended).

Official docs: https://github.com/resemble-ai/chatterbox

Examples:
  python generate_turbo.py --text "Hello [chuckle] world."
  python generate_turbo.py --text-file demo_expressive.txt --out outputs/demo.wav
  python generate_turbo.py --text-file long.txt --max-chunk-chars 280
  python generate_turbo.py --no-chunk --text-file long.txt   # single shot (often truncates)
  python generate_turbo.py --ref path/to/voice.wav --text "Custom voice line."
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import torch
import torchaudio as ta
from chatterbox.tts_turbo import ChatterboxTurboTTS

# Turbo often predicts speech EOS early on long inputs, so only part of the text
# becomes audio. Chunking by sentences keeps each generation short enough to finish.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_text_into_tts_chunks(text: str, max_chunk_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return [text]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append(" ".join(current_parts))
        current_parts = []
        current_len = 0

    for part in sentences:
        if len(part) > max_chunk_chars:
            flush()
            for start in range(0, len(part), max_chunk_chars):
                segment = part[start : start + max_chunk_chars].strip()
                if segment:
                    chunks.append(segment)
            continue

        extra = len(part) + (1 if current_parts else 0)
        if current_len + extra > max_chunk_chars:
            flush()
        current_parts.append(part)
        current_len += extra

    flush()
    return chunks


def resolve_device(explicit: str | None) -> str:
    if explicit:
        return explicit
    if torch.cuda.is_available():
        return "cuda"
    mps_available = getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
    if mps_available:
        return "mps"
    return "cpu"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Chatterbox-Turbo TTS (default voice from checkpoint; optional --ref for cloning). "
            "Paralinguistic tags include [laugh], [cough], [chuckle]."
        )
    )
    parser.add_argument(
        "--ref",
        "--audio-prompt",
        dest="audio_prompt_path",
        type=Path,
        default=None,
        help=(
            "Optional reference WAV for voice cloning (>5s required). "
            "Omit to use the model's built-in default speaker."
        ),
    )
    parser.add_argument(
        "--text",
        type=str,
        default=(
            "Hi there, Sarah here from MochaFone calling you back [chuckle], "
            "have you got one minute to chat about the billing issue?"
        ),
        help="Text to synthesize. Ignored if --text-file is set.",
    )
    parser.add_argument(
        "--text-file",
        type=Path,
        default=None,
        help="UTF-8 file with text to synthesize (non-empty lines joined with spaces). Overrides --text.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs") / "turbo-out.wav",
        help="Output WAV path (default: outputs/turbo-out.wav).",
    )
    parser.add_argument(
        "--device",
        choices=("cuda", "mps", "cpu"),
        default=None,
        help="Force device; default: cuda if available, else mps, else cpu.",
    )
    parser.add_argument(
        "--no-chunk",
        action="store_true",
        help="One model.generate() for the whole input (long text often ends up short audio).",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=320,
        metavar="N",
        help="When chunking, max characters per chunk at sentence boundaries. Default: 320.",
    )
    parser.add_argument(
        "--chunk-gap-ms",
        type=int,
        default=120,
        metavar="MS",
        help="Silence inserted between chunks in milliseconds. Default: 120.",
    )
    return parser.parse_args()


def text_from_args(args: argparse.Namespace) -> str:
    if args.text_file is not None:
        path = args.text_file.expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"Text file not found: {path}")
        raw = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in raw.splitlines()]
        joined = " ".join(line for line in lines if line)
        if not joined:
            raise SystemExit(f"Text file is empty or whitespace-only: {path}")
        return joined
    return args.text


def main() -> None:
    args = parse_args()
    text = text_from_args(args)
    ref_path: Path | None = None
    if args.audio_prompt_path is not None:
        ref_path = args.audio_prompt_path.expanduser().resolve()
        if not ref_path.is_file():
            raise SystemExit(f"Reference audio not found: {ref_path}")

    device = resolve_device(args.device)
    out_path = args.out.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading Chatterbox-Turbo on device={device!r} …")
    model = ChatterboxTurboTTS.from_pretrained(device=device)
    if ref_path is None and model.conds is None:
        raise SystemExit(
            "This checkpoint has no built-in voice embeddings (conds.pt). "
            "Pass --ref with a WAV longer than 5 seconds."
        )

    if args.no_chunk:
        chunks = [text]
    else:
        chunks = split_text_into_tts_chunks(text, args.max_chunk_chars)

    gap_samples = max(0, int(model.sr * (args.chunk_gap_ms / 1000.0)))

    print(f"Synthesizing {len(text)} characters in {len(chunks)} chunk(s) …")
    pieces: list[torch.Tensor] = []
    for index, chunk in enumerate(chunks):
        print(f"  Chunk {index + 1}/{len(chunks)} ({len(chunk)} chars) …")
        used_ref_path = str(ref_path) if ref_path is not None and index == 0 else None
        if used_ref_path is not None:
            wav_part = model.generate(chunk, audio_prompt_path=used_ref_path)
        else:
            wav_part = model.generate(chunk)
        pieces.append(wav_part)
        is_last_chunk = index == len(chunks) - 1
        if not is_last_chunk and gap_samples > 0:
            silence = torch.zeros(1, gap_samples, dtype=wav_part.dtype, device=wav_part.device)
            pieces.append(silence)

    wav = torch.cat(pieces, dim=1) if len(pieces) > 1 else pieces[0]

    ta.save(str(out_path), wav, model.sr)
    print(f"Wrote {out_path} (sr={model.sr})")


if __name__ == "__main__":
    main()
