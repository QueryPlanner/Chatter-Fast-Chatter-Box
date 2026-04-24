"""
Tests for app/core/voices.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.voices import SUPPORTED_FORMATS, VoiceLibrary


class TestVoiceLibrary:
    """Tests for VoiceLibrary class."""

    def test_init_creates_directory(self, temp_voices_dir: Path):
        """Test that initialization creates the voices directory."""
        new_dir = temp_voices_dir / "new_voices"
        new_dir.mkdir(parents=True, exist_ok=True)

        lib = VoiceLibrary(voices_dir=new_dir)
        assert lib.voices_dir == new_dir

    def test_load_metadata_creates_default(self, temp_voices_dir: Path):
        """Test that loading metadata creates default structure."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        assert "voices" in lib._metadata
        assert "aliases" in lib._metadata
        assert "version" in lib._metadata

    def test_scan_voices_finds_files(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test that scan_voices finds audio files."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        voices = lib.scan_voices()

        assert "test_voice" in voices

    def test_scan_voices_already_in_metadata(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test that scan_voices handles voices already in metadata."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        voices = lib.scan_voices()

        assert "test_voice" in voices

    def test_scan_voices_ignores_unsupported_formats(self, temp_voices_dir: Path):
        """Test that scan_voices ignores unsupported formats."""
        unsupported_file = temp_voices_dir / "unsupported.txt"
        unsupported_file.write_text("not audio")

        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        voices = lib.scan_voices()

        assert "unsupported" not in voices

    def test_get_voice_path_existing(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting path for existing voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        path = lib.get_voice_path("test_voice")
        assert path is not None
        assert "test_voice" in path

    def test_get_voice_path_nonexistent(self, temp_voices_dir: Path):
        """Test getting path for non-existent voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        path = lib.get_voice_path("nonexistent")
        assert path is None

    def test_get_voice_path_via_alias(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting voice path via alias."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.add_alias("my_alias", "test_voice")

        path = lib.get_voice_path("my_alias")
        assert path is not None

    def test_get_default_voice(self, temp_voices_dir: Path):
        """Test getting default voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        default = lib.get_default_voice()
        assert default == "dan"

    def test_get_default_voice_returns_set_value(
        self, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test getting default voice after it's set."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.set_default_voice("test_voice")

        default = lib.get_default_voice()
        assert default == "test_voice"

    def test_set_default_voice(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test setting default voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        result = lib.set_default_voice("test_voice")
        assert result is True
        assert lib.get_default_voice() == "test_voice"

    def test_set_default_voice_nonexistent(self, temp_voices_dir: Path):
        """Test setting default voice to non-existent voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        result = lib.set_default_voice("nonexistent")
        assert result is False

    def test_add_alias(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test adding an alias."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        result = lib.add_alias("my_alias", "test_voice")
        assert result is True
        assert lib._metadata["aliases"]["my_alias"] == "test_voice"

    def test_add_alias_nonexistent_voice(self, temp_voices_dir: Path):
        """Test adding alias for non-existent voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        result = lib.add_alias("alias", "nonexistent")
        assert result is False

    def test_list_voices(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test listing voices."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        voices = lib.list_voices()
        assert len(voices) == 1
        assert voices[0]["name"] == "test_voice"

    def test_list_voices_empty(self, temp_voices_dir: Path):
        """Test listing voices when empty."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        voices = lib.list_voices()
        assert len(voices) == 0

    def test_get_voice_info(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting voice info."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        info = lib.get_voice_info("test_voice")
        assert info is not None
        assert info["name"] == "test_voice"
        assert info["exists"] is True

    def test_get_voice_info_nonexistent(self, temp_voices_dir: Path):
        """Test getting info for non-existent voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        info = lib.get_voice_info("nonexistent")
        assert info is None

    def test_add_voice(self, temp_voices_dir: Path):
        """Test adding a new voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        metadata = lib.add_voice(
            voice_name="new_voice",
            file_content=b"audio_content",
            original_filename="new_voice.wav",
        )

        assert metadata["name"] == "new_voice"
        assert "new_voice" in lib._metadata["voices"]

    def test_add_voice_empty_name(self, temp_voices_dir: Path):
        """Test adding voice with empty name."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        with pytest.raises(ValueError, match="Voice name cannot be empty"):
            lib.add_voice("", b"content", "file.wav")

    def test_add_voice_invalid_characters(self, temp_voices_dir: Path):
        """Test adding voice with invalid characters."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        with pytest.raises(ValueError, match="invalid characters"):
            lib.add_voice("voice/name", b"content", "file.wav")

    def test_add_voice_unsupported_format(self, temp_voices_dir: Path):
        """Test adding voice with unsupported format."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        with pytest.raises(ValueError, match="Unsupported format"):
            lib.add_voice("voice", b"content", "file.txt")

    def test_add_voice_already_exists(self, temp_voices_dir: Path):
        """Test adding voice that already exists."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.add_voice("existing", b"content", "existing.wav")

        with pytest.raises(FileExistsError, match="already exists"):
            lib.add_voice("existing", b"new_content", "existing.wav")

    def test_delete_voice(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test deleting a voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        result = lib.delete_voice("test_voice")
        assert result is True
        assert "test_voice" not in lib._metadata["voices"]

    def test_delete_voice_nonexistent(self, temp_voices_dir: Path):
        """Test deleting non-existent voice."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        result = lib.delete_voice("nonexistent")
        assert result is False

    def test_delete_voice_removes_aliases(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test that deleting voice removes associated aliases."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.add_alias("my_alias", "test_voice")

        lib.delete_voice("test_voice")

        assert "my_alias" not in lib._metadata["aliases"]

    def test_load_metadata_corrupted_json(self, temp_voices_dir: Path):
        """Test loading metadata with corrupted JSON."""
        metadata_file = temp_voices_dir / "voices.json"
        metadata_file.write_text("{ invalid json }")

        lib = VoiceLibrary(voices_dir=temp_voices_dir)

        assert "voices" in lib._metadata
        assert lib._metadata["voices"] == {}

    def test_scan_voices_removes_deleted_files(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test that scan removes voices whose files were deleted."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        assert "test_voice" in lib._metadata["voices"]

        sample_voice_file.unlink()
        lib.scan_voices()

        assert "test_voice" not in lib._metadata["voices"]

    def test_get_voice_path_file_deleted(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting path when file was deleted."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        sample_voice_file.unlink()

        path = lib.get_voice_path("test_voice")
        assert path is None

    def test_set_default_voice_via_alias(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test setting default voice using an alias."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.add_alias("my_alias", "test_voice")

        result = lib.set_default_voice("my_alias")

        assert result is True
        assert lib.get_default_voice() == "test_voice"

    def test_add_alias_creates_aliases_dict(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test adding alias when aliases dict doesn't exist."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        del lib._metadata["aliases"]

        result = lib.add_alias("my_alias", "test_voice")

        assert result is True
        assert "aliases" in lib._metadata
        assert lib._metadata["aliases"]["my_alias"] == "test_voice"

    def test_list_voices_excludes_missing_files(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test listing voices excludes files that don't exist."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        lib._metadata["voices"]["missing"] = {
            "name": "missing",
            "filename": "missing.wav",
            "path": str(temp_voices_dir / "missing.wav"),
            "file_size": 100,
        }
        lib._save_metadata()

        voices = lib.list_voices()
        voice_names = [v["name"] for v in voices]

        assert "test_voice" in voice_names
        assert "missing" not in voice_names

    def test_get_voice_info_via_alias(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting voice info via alias."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.add_alias("my_alias", "test_voice")

        info = lib.get_voice_info("my_alias")

        assert info is not None
        assert info["name"] == "test_voice"

    def test_get_voice_info_file_deleted(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test getting voice info when file was deleted."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        sample_voice_file.unlink()

        info = lib.get_voice_info("test_voice")
        assert info is None

    def test_delete_voice_by_alias(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test deleting voice by alias."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.add_alias("my_alias", "test_voice")

        result = lib.delete_voice("my_alias")

        assert result is True
        assert "test_voice" not in lib._metadata["voices"]

    def test_delete_voice_file_missing(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test deleting voice when file is already deleted."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()

        sample_voice_file.unlink()

        result = lib.delete_voice("test_voice")

        assert result is True
        assert "test_voice" not in lib._metadata["voices"]

    def test_delete_voice_updates_default(self, temp_voices_dir: Path, sample_voice_file: Path):
        """Test that deleting default voice clears default."""
        lib = VoiceLibrary(voices_dir=temp_voices_dir)
        lib.scan_voices()
        lib.set_default_voice("test_voice")

        lib.delete_voice("test_voice")

        assert lib._metadata.get("default_voice") is None


class TestSupportedFormats:
    """Tests for SUPPORTED_FORMATS constant."""

    def test_supported_formats_includes_common(self):
        """Test that common formats are supported."""
        assert ".wav" in SUPPORTED_FORMATS
        assert ".mp3" in SUPPORTED_FORMATS
        assert ".flac" in SUPPORTED_FORMATS
        assert ".m4a" in SUPPORTED_FORMATS
        assert ".ogg" in SUPPORTED_FORMATS
