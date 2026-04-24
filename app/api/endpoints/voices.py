"""
Voice library endpoints.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.voices import SUPPORTED_FORMATS, get_voice_library
from app.models.responses import VoiceInfo, VoicesResponse

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get(
    "",
    response_model=VoicesResponse,
    summary="List voices",
    description="List all available voices in the library",
)
async def list_voices() -> VoicesResponse:
    """List all voices in the voice library."""
    voice_lib = get_voice_library()
    voices_data = voice_lib.list_voices()

    voices = [
        VoiceInfo(
            name=v["name"],
            filename=v["filename"],
            file_size=v["file_size"],
            created=v.get("created"),
            exists=v.get("exists", True),
        )
        for v in voices_data
    ]

    return VoicesResponse(
        voices=voices,
        count=len(voices),
        default_voice=voice_lib.get_default_voice(),
    )


@router.get(
    "/{voice_name}",
    response_model=VoiceInfo,
    summary="Get voice info",
    description="Get information about a specific voice",
)
async def get_voice_info(voice_name: str) -> VoiceInfo:
    """Get information about a specific voice."""
    voice_lib = get_voice_library()
    info = voice_lib.get_voice_info(voice_name)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Voice '{voice_name}' not found",
                    "type": "voice_not_found",
                }
            },
        )

    return VoiceInfo(
        name=info["name"],
        filename=info["filename"],
        file_size=info["file_size"],
        created=info.get("created"),
        exists=info.get("exists", True),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Upload voice",
    description="Upload a new voice to the library",
)
async def upload_voice(
    voice_name: str = Form(..., description="Name for the voice", min_length=1, max_length=100),
    voice_file: UploadFile = File(..., description="Voice audio file"),
) -> dict:
    """
    Upload a new voice to the library.

    Supported formats: wav, mp3, flac, m4a, ogg
    """
    if voice_file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"message": "Filename is required", "type": "validation_error"}},
        )

    file_ext = "." + voice_file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": f"Unsupported format: {file_ext}. Supported: {', '.join(SUPPORTED_FORMATS)}",
                    "type": "invalid_format",
                }
            },
        )

    # Read file content
    content = await voice_file.read()

    # Add to library
    voice_lib = get_voice_library()
    try:
        metadata = voice_lib.add_voice(voice_name, content, voice_file.filename)
    except FileExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"message": str(e), "type": "voice_exists"}},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"message": str(e), "type": "validation_error"}},
        ) from e

    return {
        "message": "Voice uploaded successfully",
        "voice": {
            "name": metadata["name"],
            "filename": metadata["filename"],
            "file_size": metadata["file_size"],
        },
    }


@router.delete(
    "/{voice_name}",
    summary="Delete voice",
    description="Delete a voice from the library",
)
async def delete_voice(voice_name: str) -> dict:
    """Delete a voice from the library."""
    voice_lib = get_voice_library()
    success = voice_lib.delete_voice(voice_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Voice '{voice_name}' not found",
                    "type": "voice_not_found",
                }
            },
        )

    return {"message": f"Voice '{voice_name}' deleted successfully"}


@router.post(
    "/default",
    summary="Set default voice",
    description="Set the default voice for synthesis",
)
async def set_default_voice(voice_name: str = Form(...)) -> dict:
    """Set the default voice."""
    voice_lib = get_voice_library()
    success = voice_lib.set_default_voice(voice_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Voice '{voice_name}' not found",
                    "type": "voice_not_found",
                }
            },
        )

    return {
        "message": f"Default voice set to '{voice_name}'",
        "default_voice": voice_name,
    }


@router.get(
    "/{voice_name}/download",
    response_class=FileResponse,
    summary="Download voice",
    description="Download a voice file",
)
async def download_voice(voice_name: str) -> FileResponse:
    """Download a voice file."""
    voice_lib = get_voice_library()
    voice_path = voice_lib.get_voice_path(voice_name)

    if voice_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Voice '{voice_name}' not found",
                    "type": "voice_not_found",
                }
            },
        )

    return FileResponse(
        voice_path,
        filename=f"{voice_name}.wav",
        media_type="audio/wav",
    )
