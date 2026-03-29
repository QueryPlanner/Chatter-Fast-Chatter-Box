"""
Voice library management for TTS.

Provides a simple voice library that:
- Scans the voices/ directory for .wav files
- Maintains metadata in voices.json
- Supports aliases (e.g., "dan" -> "dan_prompt_1")
- Allows voice upload and deletion
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Default voices directory
DEFAULT_VOICES_DIR = Path(__file__).parent.parent.parent / "voices"

# Supported audio formats
SUPPORTED_FORMATS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


class VoiceLibrary:
    """Manages a library of voice samples for TTS."""

    def __init__(self, voices_dir: Optional[Path] = None):
        self.voices_dir = Path(voices_dir) if voices_dir else DEFAULT_VOICES_DIR
        self.metadata_file = self.voices_dir / "voices.json"
        self._ensure_directory()
        self._metadata = self._load_metadata()

    def _ensure_directory(self) -> None:
        """Ensure the voices directory exists."""
        self.voices_dir.mkdir(parents=True, exist_ok=True)

    def _load_metadata(self) -> Dict[str, Any]:
        """Load voice metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Default metadata structure
        return {
            "voices": {},
            "aliases": {},
            "default_voice": "dan",
            "version": "1.0",
        }

    def _save_metadata(self) -> None:
        """Save voice metadata to JSON file."""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)

    def scan_voices(self) -> List[str]:
        """
        Scan the voices directory for audio files.

        Returns:
            List of voice names found
        """
        found_voices = []

        for file_path in self.voices_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
                voice_name = file_path.stem
                found_voices.append(voice_name)

                # Add to metadata if not already present
                if voice_name not in self._metadata["voices"]:
                    self._metadata["voices"][voice_name] = {
                        "name": voice_name,
                        "filename": file_path.name,
                        "path": str(file_path),
                        "file_size": file_path.stat().st_size,
                        "created": datetime.now().isoformat(),
                    }

        # Remove voices that no longer exist
        to_remove = [
            name for name in self._metadata["voices"]
            if name not in found_voices
        ]
        for name in to_remove:
            del self._metadata["voices"][name]

        if found_voices:
            self._save_metadata()

        return found_voices

    def get_voice_path(self, name: str) -> Optional[str]:
        """
        Get the file path for a voice by name or alias.

        Args:
            name: Voice name or alias

        Returns:
            Path to the voice file, or None if not found
        """
        # Check if it's an alias first
        if name in self._metadata.get("aliases", {}):
            actual_name = self._metadata["aliases"][name]
            return self.get_voice_path(actual_name)

        # Check direct name lookup
        if name in self._metadata["voices"]:
            voice_path = Path(self._metadata["voices"][name]["path"])
            if voice_path.exists():
                return str(voice_path)

        return None

    def get_default_voice(self) -> str:
        """Get the default voice name."""
        return self._metadata.get("default_voice", "dan")

    def set_default_voice(self, name: str) -> bool:
        """
        Set the default voice.

        Args:
            name: Voice name or alias

        Returns:
            True if successful, False if voice not found
        """
        if self.get_voice_path(name) is None:
            return False

        # Resolve alias to actual name
        if name in self._metadata.get("aliases", {}):
            name = self._metadata["aliases"][name]

        self._metadata["default_voice"] = name
        self._save_metadata()
        return True

    def add_alias(self, alias: str, voice_name: str) -> bool:
        """
        Add an alias for a voice.

        Args:
            alias: The alias to add
            voice_name: The actual voice name

        Returns:
            True if successful, False if voice not found
        """
        if voice_name not in self._metadata["voices"]:
            return False

        if "aliases" not in self._metadata:
            self._metadata["aliases"] = {}

        self._metadata["aliases"][alias] = voice_name
        self._save_metadata()
        return True

    def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all voices in the library.

        Returns:
            List of voice metadata dictionaries
        """
        voices = []

        for name, metadata in self._metadata["voices"].items():
            voice_path = Path(metadata["path"])
            if voice_path.exists():
                voices.append({
                    **metadata,
                    "exists": True,
                })

        return voices

    def get_voice_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a voice.

        Args:
            name: Voice name or alias

        Returns:
            Voice metadata dictionary, or None if not found
        """
        # Resolve alias
        if name in self._metadata.get("aliases", {}):
            name = self._metadata["aliases"][name]

        if name not in self._metadata["voices"]:
            return None

        metadata = self._metadata["voices"][name]
        voice_path = Path(metadata["path"])

        if not voice_path.exists():
            return None

        return {
            **metadata,
            "exists": True,
        }

    def add_voice(
        self,
        voice_name: str,
        file_content: bytes,
        original_filename: str,
    ) -> Dict[str, Any]:
        """
        Add a new voice to the library.

        Args:
            voice_name: Name for the voice
            file_content: Audio file content
            original_filename: Original filename (for extension)

        Returns:
            Voice metadata

        Raises:
            ValueError: If name is invalid or format unsupported
            FileExistsError: If voice name already exists
        """
        # Validate name
        if not voice_name or not voice_name.strip():
            raise ValueError("Voice name cannot be empty")

        voice_name = voice_name.strip()

        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in voice_name for char in invalid_chars):
            raise ValueError(f"Voice name contains invalid characters: {invalid_chars}")

        # Check file extension
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {file_ext}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        # Check if already exists
        if voice_name in self._metadata["voices"]:
            raise FileExistsError(f"Voice '{voice_name}' already exists")

        # Save the file
        voice_filename = f"{voice_name}{file_ext}"
        voice_path = self.voices_dir / voice_filename

        with open(voice_path, "wb") as f:
            f.write(file_content)

        # Create metadata
        metadata = {
            "name": voice_name,
            "filename": voice_filename,
            "path": str(voice_path),
            "file_size": len(file_content),
            "created": datetime.now().isoformat(),
        }

        self._metadata["voices"][voice_name] = metadata
        self._save_metadata()

        return metadata

    def delete_voice(self, name: str) -> bool:
        """
        Delete a voice from the library.

        Args:
            name: Voice name

        Returns:
            True if deleted, False if not found
        """
        # Resolve alias
        if name in self._metadata.get("aliases", {}):
            name = self._metadata["aliases"][name]

        if name not in self._metadata["voices"]:
            return False

        metadata = self._metadata["voices"][name]
        voice_path = Path(metadata["path"])

        # Remove file
        if voice_path.exists():
            voice_path.unlink()

        # Remove from metadata
        del self._metadata["voices"][name]

        # Remove any aliases pointing to this voice
        aliases_to_remove = [
            alias for alias, target in self._metadata.get("aliases", {}).items()
            if target == name
        ]
        for alias in aliases_to_remove:
            del self._metadata["aliases"][alias]

        # Update default if needed
        if self._metadata.get("default_voice") == name:
            self._metadata["default_voice"] = None

        self._save_metadata()
        return True


# Global instance
_voice_library: Optional[VoiceLibrary] = None


def get_voice_library() -> VoiceLibrary:
    """Get the global voice library instance."""
    global _voice_library
    if _voice_library is None:
        _voice_library = VoiceLibrary()
        _voice_library.scan_voices()
    return _voice_library
