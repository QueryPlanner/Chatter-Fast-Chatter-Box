"""
Text-to-speech synthesis endpoint.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.tts import generate_speech, is_ready
from app.core.voices import get_voice_library

router = APIRouter(tags=["speech"])


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
    description="Generate speech from text using Chatterbox TTS",
)
async def synthesize(
    text: str = Form(..., description="Text to synthesize", min_length=1, max_length=10000),
    voice: str = Form(None, description="Voice name or alias"),
    output_format: str = Form("mp3", description="Output format: mp3 or wav"),
    max_sentences_per_chunk: int = Form(5, description="Max sentences per chunk"),
    max_chunk_chars: int = Form(320, description="Max characters per chunk"),
    chunk_gap_ms: int = Form(120, description="Gap between chunks in ms"),
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
    reference_audio_path = None

    if reference_audio is not None and reference_audio.filename:
        # User uploaded a reference audio file
        # Save to temp file
        content = await reference_audio.read()
        suffix = Path(reference_audio.filename).suffix or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            reference_audio_path = tmp.name

    elif voice:
        # User specified a voice from the library
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

        reference_audio_path = voice_path

    else:
        # Use default voice
        voice_lib = get_voice_library()
        default_voice = voice_lib.get_default_voice()

        if default_voice:
            reference_audio_path = voice_lib.get_voice_path(default_voice)

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
