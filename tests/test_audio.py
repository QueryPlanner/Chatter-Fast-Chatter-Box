"""
Tests for app/core/audio.py
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
import torch

from app.core.audio import (
    concatenate_with_gap,
    stitch_chunk_files,
    tensor_to_audio_bytes,
    wav_bytes_to_mp3_bytes,
)


class TestConcatenateWithGap:
    """Tests for concatenate_with_gap function."""

    def test_concatenate_single_tensor(self):
        """Test concatenating a single tensor."""
        tensor = torch.randn(1, 1000)
        result = concatenate_with_gap([tensor], sample_rate=24000, gap_ms=100)

        assert torch.equal(result, tensor)

    def test_concatenate_multiple_tensors(self):
        """Test concatenating multiple tensors."""
        tensor1 = torch.randn(1, 1000)
        tensor2 = torch.randn(1, 1000)
        tensor3 = torch.randn(1, 1000)

        result = concatenate_with_gap([tensor1, tensor2, tensor3], sample_rate=24000, gap_ms=100)

        gap_samples = int(24000 * 0.1)
        expected_length = 3000 + 2 * gap_samples
        assert result.shape == (1, expected_length)

    def test_concatenate_with_zero_gap(self):
        """Test concatenating with zero gap."""
        tensor1 = torch.randn(1, 1000)
        tensor2 = torch.randn(1, 1000)

        result = concatenate_with_gap([tensor1, tensor2], sample_rate=24000, gap_ms=0)

        assert result.shape == (1, 2000)

    def test_concatenate_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="No audio tensors to concatenate"):
            concatenate_with_gap([], sample_rate=24000)

    def test_concatenate_preserves_dtype(self):
        """Test that concatenation preserves tensor dtype."""
        tensor1 = torch.randn(1, 1000, dtype=torch.float32)
        tensor2 = torch.randn(1, 1000, dtype=torch.float32)

        result = concatenate_with_gap([tensor1, tensor2], sample_rate=24000)
        assert result.dtype == torch.float32

    def test_concatenate_preserves_device(self):
        """Test that concatenation preserves tensor device."""
        tensor1 = torch.randn(1, 1000)
        tensor2 = torch.randn(1, 1000)

        result = concatenate_with_gap([tensor1, tensor2], sample_rate=24000)
        assert result.device == tensor1.device

    def test_concatenate_silence_between_chunks(self):
        """Test that silence is added between chunks."""
        tensor1 = torch.ones(1, 1000)
        tensor2 = torch.ones(1, 1000)

        result = concatenate_with_gap([tensor1, tensor2], sample_rate=24000, gap_ms=100)

        gap_samples = int(24000 * 0.1)
        silence = result[:, 1000 : 1000 + gap_samples]

        assert torch.allclose(silence, torch.zeros(1, gap_samples), atol=1e-6)


class TestWavBytesToMp3Bytes:
    """Tests for wav_bytes_to_mp3_bytes function."""

    def test_wav_to_mp3_success(self, sample_wav_audio: bytes):
        """Test successful WAV to MP3 conversion."""
        with patch("app.core.audio.PYDUB_AVAILABLE", True):
            with patch("app.core.audio.AudioSegment") as mock_segment:
                mock_audio = MagicMock()
                mock_segment.from_wav.return_value = mock_audio

                mock_buffer = io.BytesIO()
                mock_buffer.write(b"mp3_data")
                mock_buffer.seek(0)

                mock_audio.export = MagicMock(
                    side_effect=lambda buf, **kwargs: (
                        buf.write(b"mp3_data"),
                        buf.seek(0),
                    )[0]
                )

                result = wav_bytes_to_mp3_bytes(sample_wav_audio)
                assert len(result) > 0

    def test_wav_to_mp3_pydub_unavailable(self):
        """Test that missing pydub raises RuntimeError."""
        with patch("app.core.audio.PYDUB_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pydub is required for MP3 conversion"):
                wav_bytes_to_mp3_bytes(b"wav_data")

    def test_wav_to_mp3_custom_bitrate(self, sample_wav_audio: bytes):
        """Test WAV to MP3 conversion with custom bitrate."""
        with patch("app.core.audio.PYDUB_AVAILABLE", True):
            with patch("app.core.audio.AudioSegment") as mock_segment:
                mock_audio = MagicMock()
                mock_segment.from_wav.return_value = mock_audio

                mock_audio.export = MagicMock(
                    side_effect=lambda buf, **kwargs: (
                        buf.write(b"mp3_data"),
                        buf.seek(0),
                    )[0]
                )

                wav_bytes_to_mp3_bytes(sample_wav_audio, bitrate="256k")

                call_kwargs = mock_audio.export.call_args[1]
                assert call_kwargs["bitrate"] == "256k"


class TestTensorToAudioBytes:
    """Tests for tensor_to_audio_bytes function."""

    def test_tensor_to_wav(self):
        """Test converting tensor to WAV bytes."""
        tensor = torch.randn(1, 24000)

        with patch("torchaudio.save") as mock_save:
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")

            audio_bytes, content_type = tensor_to_audio_bytes(tensor, 24000, "wav")

            assert content_type == "audio/wav"
            assert len(audio_bytes) > 0

    def test_tensor_to_mp3(self):
        """Test converting tensor to MP3 bytes."""
        tensor = torch.randn(1, 24000)

        with (
            patch("torchaudio.save") as mock_save,
            patch("app.core.audio.wav_bytes_to_mp3_bytes") as mock_to_mp3,
        ):
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")
            mock_to_mp3.return_value = b"MP3_DATA"

            audio_bytes, content_type = tensor_to_audio_bytes(tensor, 24000, "mp3")

            assert content_type == "audio/mpeg"
            assert audio_bytes == b"MP3_DATA"

    def test_tensor_to_audio_moves_to_cpu(self):
        """Test that tensor is moved to CPU before saving."""
        with patch("torchaudio.save") as mock_save:
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")

            tensor_to_audio_bytes(torch.randn(1, 24000), 24000, "wav")
            mock_save.assert_called_once()

    def test_tensor_to_audio_format_case_insensitive(self):
        """Test that output format is case insensitive."""
        tensor = torch.randn(1, 24000)

        with patch("torchaudio.save") as mock_save:
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")

            _, content_type1 = tensor_to_audio_bytes(tensor, 24000, "WAV")
            assert content_type1 == "audio/wav"

            with patch("app.core.audio.wav_bytes_to_mp3_bytes", return_value=b"MP3"):
                _, content_type2 = tensor_to_audio_bytes(tensor, 24000, "MP3")
                assert content_type2 == "audio/mpeg"

    def test_tensor_to_audio_with_cpu_method(self):
        """Test that tensor with .cpu() method is moved to CPU."""
        mock_tensor = MagicMock()
        mock_tensor.cpu.return_value = torch.randn(1, 24000)
        mock_tensor.has_c.return_value = True

        with patch("torchaudio.save") as mock_save:
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")

            tensor_to_audio_bytes(mock_tensor, 24000, "wav")

            mock_tensor.cpu.assert_called_once()

    def test_tensor_to_audio_without_cpu_method(self):
        """Test that tensor without .cpu() method is used directly."""
        mock_tensor = object()

        with patch("torchaudio.save") as mock_save:
            mock_save.side_effect = lambda buf, *args, **kwargs: buf.write(b"WAV_DATA")

            result = tensor_to_audio_bytes(mock_tensor, 24000, "wav")

            assert result[1] == "audio/wav"


class TestPydubImportError:
    """Tests for pydub ImportError handling."""

    def test_pydub_import_error_handling(self):
        """Test that ImportError for pydub is handled correctly."""
        import importlib
        import sys

        original_pydub = sys.modules.get("pydub")

        try:
            sys.modules["pydub"] = None
            sys.modules["pydub.AudioSegment"] = None

            import app.core.audio as audio_module
            importlib.reload(audio_module)

            from app.core.audio import PYDUB_AVAILABLE

            assert PYDUB_AVAILABLE is False

        finally:
            if original_pydub is not None:
                sys.modules["pydub"] = original_pydub
            elif "pydub" in sys.modules:
                del sys.modules["pydub"]

            importlib.reload(audio_module)


class TestStitchChunkFiles:
    """Tests for stitch_chunk_files function."""

    def _create_chunk_wav(self, path: str, samples: int = 24000, sample_rate: int = 24000) -> None:
        """Helper to create a valid WAV chunk file on disk."""
        import torchaudio as ta

        audio = torch.randn(1, samples)
        ta.save(path, audio, sample_rate, format="wav")

    def test_empty_list_raises(self, tmp_path):
        """Test that empty chunk list raises ValueError."""
        with pytest.raises(ValueError, match="No chunk files to stitch"):
            stitch_chunk_files(
                chunk_paths=[],
                output_path=str(tmp_path / "out.wav"),
                sample_rate=24000,
            )

    def test_single_chunk_wav(self, tmp_path):
        """Test stitching a single chunk to WAV."""
        chunk_path = str(tmp_path / "chunk_0.wav")
        output_path = str(tmp_path / "out.wav")
        self._create_chunk_wav(chunk_path, samples=24000)

        stitch_chunk_files(
            chunk_paths=[chunk_path],
            output_path=output_path,
            sample_rate=24000,
            gap_ms=0,
            output_format="wav",
        )

        import torchaudio as ta
        from pathlib import Path

        assert Path(output_path).exists()
        audio, sr = ta.load(output_path)
        assert sr == 24000
        assert audio.shape[0] == 1
        assert audio.shape[1] == 24000

    def test_multiple_chunks_with_gap(self, tmp_path):
        """Test stitching multiple chunks with silence gaps."""
        chunk_paths = []
        for i in range(3):
            path = str(tmp_path / f"chunk_{i}.wav")
            self._create_chunk_wav(path, samples=1000)
            chunk_paths.append(path)

        output_path = str(tmp_path / "out.wav")

        stitch_chunk_files(
            chunk_paths=chunk_paths,
            output_path=output_path,
            sample_rate=24000,
            gap_ms=100,
            output_format="wav",
        )

        import torchaudio as ta

        audio, sr = ta.load(output_path)
        gap_samples = int(24000 * 0.1)
        expected_length = 3 * 1000 + 2 * gap_samples  # 3 chunks + 2 gaps
        assert audio.shape[1] == expected_length

    def test_mp3_output(self, tmp_path):
        """Test stitching with MP3 output format."""
        chunk_path = str(tmp_path / "chunk_0.wav")
        output_path = str(tmp_path / "out.mp3")
        self._create_chunk_wav(chunk_path, samples=24000)

        with patch("app.core.audio.wav_bytes_to_mp3_bytes") as mock_to_mp3:
            mock_to_mp3.return_value = b"MP3_DATA"

            stitch_chunk_files(
                chunk_paths=[chunk_path],
                output_path=output_path,
                sample_rate=24000,
                output_format="mp3",
            )

            mock_to_mp3.assert_called_once()
            from pathlib import Path

            assert Path(output_path).exists()
            with open(output_path, "rb") as f:
                assert f.read() == b"MP3_DATA"

    def test_batch_processing(self, tmp_path):
        """Test stitching with batch processing for memory efficiency."""
        chunk_paths = []
        for i in range(25):
            path = str(tmp_path / f"chunk_{i}.wav")
            self._create_chunk_wav(path, samples=1000)
            chunk_paths.append(path)

        output_path = str(tmp_path / "out.wav")

        stitch_chunk_files(
            chunk_paths=chunk_paths,
            output_path=output_path,
            sample_rate=24000,
            gap_ms=0,
            output_format="wav",
            batch_size=10,
        )

        import torchaudio as ta

        audio, sr = ta.load(output_path)
        assert sr == 24000
        assert audio.shape[1] == 25 * 1000

    def test_batch_processing_with_gaps(self, tmp_path):
        """Test batch stitching preserves correct gaps between chunks."""
        chunk_paths = []
        for i in range(5):
            path = str(tmp_path / f"chunk_{i}.wav")
            self._create_chunk_wav(path, samples=1000)
            chunk_paths.append(path)

        output_path = str(tmp_path / "out.wav")

        stitch_chunk_files(
            chunk_paths=chunk_paths,
            output_path=output_path,
            sample_rate=24000,
            gap_ms=100,
            output_format="wav",
            batch_size=2,
        )

        import torchaudio as ta

        audio, sr = ta.load(output_path)
        gap_samples = int(24000 * 0.1)
        expected_length = 5 * 1000 + 4 * gap_samples
        assert audio.shape[1] == expected_length
