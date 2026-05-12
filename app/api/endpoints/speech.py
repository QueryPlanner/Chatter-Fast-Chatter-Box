"""
Text-to-speech synthesis endpoint.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.config import Config
from app.core.tts import generate_speech, is_ready
from app.core.voices import get_voice_library

router = APIRouter(tags=["speech"])


KYUTAI_VOICES = {
    'cosette', 'marius', 'javert', 'alba', 'jean', 'anna', 'vera', 'fantine', 
    'charles', 'paul', 'eponine', 'azelma', 'george', 'mary', 'jane', 'michael', 
    'eve', 'bill_boerst', 'peter_yearsley', 'stuart_bell', 'caro_davy', 'giovanni', 
    'lola', 'juergen', 'rafael', 'estelle'
}

async def resolve_reference_audio(voice: str | None, reference_audio: UploadFile | None) -> str | None:
    """Helper to resolve the reference audio path based on user input and configuration."""
    if reference_audio is not None and reference_audio.filename:
        content = await reference_audio.read()
        suffix = Path(reference_audio.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            return tmp.name

    if Config.TTS_ENGINE.lower() == "kyutai" and voice in KYUTAI_VOICES:
        return voice

    if Config.TTS_ENGINE.lower() == "kyutai" and not voice:
        return "alba"

    if voice:
        voice_lib = get_voice_library()
        voice_path = voice_lib.get_voice_path(voice)
        if voice_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "message": f"Voice '{voice}' not found in voice library",
                        "type": "voice_not_found",
                    }
                },
            )
        return voice_path

    voice_lib = get_voice_library()
    default_voice = voice_lib.get_default_voice()
    
    reference_audio_path = None
    if default_voice:
        reference_audio_path = voice_lib.get_voice_path(default_voice)
    
    if Config.TTS_ENGINE.lower() == "kyutai":
        return "alba"

    return reference_audio_path


@router.post(
    "/synthesize",
    responses={
        200: {
            "description": "Generated audio",
            "content": {
                "audio/mpeg": {"schema": {"type": "string", "format": "binary"}},
                "audio/wav": {"schema": {"type": "string", "format": "binary"}},
            },
        },
    },
    summary="Synthesize speech",
    description="Generate speech from text using Chatterbox TTS or Kyutai Pocket TTS",
)
async def synthesize(
    text: str = Form(..., description="Text to synthesize", min_length=1, max_length=10000),
    voice: str = Form(None, description="Voice name or alias"),
    output_format: str = Form("mp3", description="Output format: mp3 or wav"),
    max_sentences_per_chunk: int = Form(
        Config.MAX_SENTENCES_PER_CHUNK, description="Max sentences per chunk"
    ),
    max_chunk_chars: int = Form(Config.MAX_CHUNK_CHARS, description="Max characters per chunk"),
    chunk_gap_ms: int = Form(Config.CHUNK_GAP_MS, description="Gap between chunks in ms"),
    reference_audio: UploadFile = File(
        None, description="Optional reference audio for voice cloning"
    ),
) -> Response:
    """
    Generate speech from text.

    You can either:
    - Use a voice from the library (voice parameter)
    - Upload a reference audio file for voice cloning (reference_audio parameter)
    - Use the default voice (neither parameter)

    The output is MP3 by default, but WAV is available.
    """
    # Check if model is ready
    if not is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "message": "Model is still initializing. Please try again in a moment.",
                    "type": "model_not_ready",
                }
            },
        )

    # Validate output format
    output_format = output_format.lower()
    if output_format not in ("mp3", "wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": "output_format must be 'mp3' or 'wav'",
                    "type": "invalid_format",
                }
            },
        )

    # Determine reference audio path
    reference_audio_path = await resolve_reference_audio(voice, reference_audio)

    try:
        # Generate speech
        audio_bytes, content_type = generate_speech(
            text=text,
            reference_audio_path=reference_audio_path,
            max_sentences_per_chunk=max_sentences_per_chunk,
            max_chunk_chars=max_chunk_chars,
            chunk_gap_ms=chunk_gap_ms,
            output_format=output_format,
        )

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{output_format}"',
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "message": f"Failed to generate speech: {str(e)}",
                    "type": "generation_error",
                }
            },
        ) from e

    finally:
        # Clean up temp file if created
        if (
            reference_audio is not None
            and reference_audio_path
            and reference_audio_path.startswith("/tmp")
        ):
            Path(reference_audio_path).unlink(missing_ok=True)


@router.post(
    "/synthesize/stream",
    responses={
        200: {
            "description": "Streamed audio",
            "content": {
                "audio/mpeg": {"schema": {"type": "string", "format": "binary"}},
                "audio/wav": {"schema": {"type": "string", "format": "binary"}},
            },
        },
    },
    summary="Stream synthesized speech",
    description="Stream generated speech from text chunk by chunk",
)
async def synthesize_stream(
    text: str = Form(..., description="Text to synthesize", min_length=1, max_length=10000),
    voice: str = Form(None, description="Voice name or alias"),
    output_format: str = Form("mp3", description="Output format: mp3 or wav"),
    max_sentences_per_chunk: int = Form(
        Config.MAX_SENTENCES_PER_CHUNK, description="Max sentences per chunk"
    ),
    max_chunk_chars: int = Form(Config.MAX_CHUNK_CHARS, description="Max characters per chunk"),
    chunk_gap_ms: int = Form(Config.CHUNK_GAP_MS, description="Gap between chunks in ms"),
    reference_audio: UploadFile = File(
        None, description="Optional reference audio for voice cloning"
    ),
):
    """
    Stream generated speech from text chunk by chunk.
    """
    from fastapi.responses import StreamingResponse
    from app.core.tts import generate_speech_stream
    
    if not is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "message": "Model is still initializing. Please try again in a moment.",
                    "type": "model_not_ready",
                }
            },
        )

    output_format = output_format.lower()
    if output_format not in ("mp3", "wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"message": "output_format must be 'mp3' or 'wav'", "type": "invalid_format"}}
        )

    reference_audio_path = await resolve_reference_audio(voice, reference_audio)

    async def cleanup_generator():
        try:
            async for chunk in generate_speech_stream(
                text=text,
                reference_audio_path=reference_audio_path,
                max_sentences_per_chunk=max_sentences_per_chunk,
                max_chunk_chars=max_chunk_chars,
                chunk_gap_ms=chunk_gap_ms,
                output_format=output_format,
            ):
                yield chunk
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error streaming speech: {e}")
        finally:
            if reference_audio is not None and reference_audio_path and reference_audio_path.startswith("/tmp"):
                Path(reference_audio_path).unlink(missing_ok=True)

    content_type = "audio/wav" if output_format == "wav" else "audio/mpeg"

    return StreamingResponse(
        cleanup_generator(),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="speech.{output_format}"'}
    )
