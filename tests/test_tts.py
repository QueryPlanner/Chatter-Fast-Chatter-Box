"""
Tests for app/core/tts.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import torch

from app.core.tts import (
    generate_single_chunk,
    generate_speech,
    get_device,
    get_initialization_error,
    get_model,
    get_sample_rate,
    initialize_model,
    is_ready,
    resolve_device,
)


class TestResolveDevice:
    """Tests for resolve_device function."""

    def test_explicit_cuda(self):
        """Test explicit CUDA device selection."""
        with patch("torch.cuda.is_available", return_value=False):
            result = resolve_device("cuda")
            assert result == "cuda"

    def test_explicit_cpu(self):
        """Test explicit CPU device selection."""
        result = resolve_device("cpu")
        assert result == "cpu"

    def test_explicit_mps(self):
        """Test explicit MPS device selection."""
        result = resolve_device("mps")
        assert result == "mps"

    def test_auto_cuda_available(self):
        """Test auto selection with CUDA available."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch.object(torch.backends, "mps", create=True) as mock_mps:
                mock_mps.is_available = MagicMock(return_value=False)
                result = resolve_device("auto")
                assert result == "cuda"

    def test_auto_mps_available(self):
        """Test auto selection with MPS available."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch.object(torch.backends, "mps", create=True) as mock_mps:
                mock_mps.is_available = MagicMock(return_value=True)
                result = resolve_device("auto")
                assert result == "mps"

    def test_auto_cpu_fallback(self):
        """Test auto selection fallback to CPU."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch.object(torch.backends, "mps", create=True) as mock_mps:
                mock_mps.is_available = MagicMock(return_value=False)
                result = resolve_device("auto")
                assert result == "cpu"

    def test_case_insensitive(self):
        """Test device names are case insensitive."""
        assert resolve_device("CUDA") == "cuda"
        assert resolve_device("Cpu") == "cpu"
        assert resolve_device("MPS") == "mps"


class TestInitializeModel:
    """Tests for initialize_model function."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful model initialization."""
        mock_model = MagicMock()
        mock_model.sr = 24000

        with patch("app.core.tts.ChatterboxTurboTTS") as mock_cls:
            mock_cls.from_pretrained = MagicMock(return_value=mock_model)
            with patch("torch.cuda.is_available", return_value=False):
                with patch.object(torch.backends, "mps", create=True) as mock_mps:
                    mock_mps.is_available = MagicMock(return_value=False)

                    result = await initialize_model("cpu")

                    assert result == mock_model
                    assert is_ready()

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test model initialization failure."""
        with patch("app.core.tts.ChatterboxTurboTTS") as mock_cls:
            mock_cls.from_pretrained = MagicMock(side_effect=RuntimeError("Load failed"))

            with pytest.raises(RuntimeError, match="Load failed"):
                await initialize_model("cpu")

            assert get_initialization_error() is not None


class TestGetModel:
    """Tests for get_model function."""

    def test_get_model_before_init(self):
        """Test getting model before initialization."""
        with patch("app.core.tts._model", None):
            result = get_model()
            assert result is None

    def test_get_model_after_init(self):
        """Test getting model after initialization."""
        mock_model = MagicMock()
        with patch("app.core.tts._model", mock_model):
            result = get_model()
            assert result == mock_model


class TestGetDevice:
    """Tests for get_device function."""

    def test_get_device_before_init(self):
        """Test getting device before initialization."""
        with patch("app.core.tts._device", None):
            result = get_device()
            assert result is None

    def test_get_device_after_init(self):
        """Test getting device after initialization."""
        with patch("app.core.tts._device", "cuda"):
            result = get_device()
            assert result == "cuda"


class TestGetInitializationError:
    """Tests for get_initialization_error function."""

    def test_no_error(self):
        """Test no error after successful init."""
        with patch("app.core.tts._initialization_error", None):
            result = get_initialization_error()
            assert result is None

    def test_has_error(self):
        """Test error is returned."""
        with patch("app.core.tts._initialization_error", "Failed to load"):
            result = get_initialization_error()
            assert result == "Failed to load"


class TestIsReady:
    """Tests for is_ready function."""

    def test_not_ready(self):
        """Test is_ready returns False when model not loaded."""
        with patch("app.core.tts._model", None):
            assert is_ready() is False

    def test_ready(self):
        """Test is_ready returns True when model is loaded."""
        mock_model = MagicMock()
        with patch("app.core.tts._model", mock_model):
            assert is_ready() is True


class TestGetSampleRate:
    """Tests for get_sample_rate function."""

    def test_model_not_initialized(self):
        """Test error when model not initialized."""
        with patch("app.core.tts._model", None):
            with pytest.raises(RuntimeError, match="Model not initialized"):
                get_sample_rate()

    def test_returns_sample_rate(self):
        """Test returns model sample rate."""
        mock_model = MagicMock()
        mock_model.sr = 24000
        with patch("app.core.tts._model", mock_model):
            assert get_sample_rate() == 24000


class TestGenerateSingleChunk:
    """Tests for generate_single_chunk function."""

    def test_model_not_initialized(self):
        """Test error when model not initialized."""
        with patch("app.core.tts._model", None):
            with pytest.raises(RuntimeError, match="Model not initialized"):
                generate_single_chunk("test", "/tmp/out.wav")

    def test_generates_and_writes_wav(self, tmp_path):
        """Test that single chunk generates audio and writes to disk."""
        mock_model = MagicMock()
        mock_model.sr = 24000
        mock_model.generate = MagicMock(return_value=torch.randn(1, 24000))

        output_path = str(tmp_path / "chunk.wav")

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.ta") as mock_ta:
                generate_single_chunk("Hello world.", output_path)

                mock_model.generate.assert_called_once_with("Hello world.")
                mock_ta.save.assert_called_once()
                call_args = mock_ta.save.call_args
                assert call_args[0][0] == output_path
                assert call_args[0][2] == 24000

    def test_generates_with_reference_audio(self, tmp_path):
        """Test generation with reference audio path."""
        mock_model = MagicMock()
        mock_model.sr = 24000
        mock_model.generate = MagicMock(return_value=torch.randn(1, 24000))

        output_path = str(tmp_path / "chunk.wav")

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.ta"):
                generate_single_chunk(
                    "Hello world.",
                    output_path,
                    reference_audio_path="/path/to/voice.wav",
                )

                call_kwargs = mock_model.generate.call_args[1]
                assert call_kwargs["audio_prompt_path"] == "/path/to/voice.wav"


class TestGenerateSpeech:
    """Tests for generate_speech function."""

    def test_model_not_initialized(self):
        """Test error when model not initialized."""
        with patch("app.core.tts._model", None):
            with pytest.raises(RuntimeError, match="Model not initialized"):
                generate_speech("test text")

    def test_generate_without_reference(self):
        """Test generation without reference audio."""
        mock_model = MagicMock()
        mock_model.sr = 24000

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.split_text_into_chunks") as mock_split:
                with patch("app.core.tts.generate_single_chunk") as mock_gen_chunk:
                    with patch("app.core.tts.stitch_chunk_files") as mock_stitch:
                        mock_split.return_value = ["chunk1"]

                        # Mock stitch to create the output file
                        def fake_stitch(**kwargs):
                            with open(kwargs["output_path"], "wb") as f:
                                f.write(b"audio_data")

                        mock_stitch.side_effect = fake_stitch

                        result = generate_speech("test text")

                        assert result == (b"audio_data", "audio/mpeg")
                        mock_gen_chunk.assert_called_once()

    def test_generate_with_reference(self):
        """Test generation with reference audio."""
        mock_model = MagicMock()
        mock_model.sr = 24000

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.split_text_into_chunks") as mock_split:
                with patch("app.core.tts.generate_single_chunk") as mock_gen_chunk:
                    with patch("app.core.tts.stitch_chunk_files") as mock_stitch:
                        mock_split.return_value = ["chunk1"]

                        def fake_stitch(**kwargs):
                            with open(kwargs["output_path"], "wb") as f:
                                f.write(b"audio_data")

                        mock_stitch.side_effect = fake_stitch

                        generate_speech("test text", reference_audio_path="/path/to/voice.wav")

                        call_kwargs = mock_gen_chunk.call_args[1]
                        assert call_kwargs["reference_audio_path"] == "/path/to/voice.wav"

    def test_generate_multiple_chunks(self):
        """Test generation with multiple chunks."""
        mock_model = MagicMock()
        mock_model.sr = 24000

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.split_text_into_chunks") as mock_split:
                with patch("app.core.tts.generate_single_chunk") as mock_gen_chunk:
                    with patch("app.core.tts.stitch_chunk_files") as mock_stitch:
                        mock_split.return_value = ["chunk1", "chunk2", "chunk3"]

                        def fake_stitch(**kwargs):
                            with open(kwargs["output_path"], "wb") as f:
                                f.write(b"audio_data")

                        mock_stitch.side_effect = fake_stitch

                        generate_speech("test text", reference_audio_path="/voice.wav")

                        assert mock_gen_chunk.call_count == 3

    def test_generate_wav_output(self):
        """Test generation with WAV output format."""
        mock_model = MagicMock()
        mock_model.sr = 24000

        with patch("app.core.tts._model", mock_model):
            with patch("app.core.tts.split_text_into_chunks") as mock_split:
                with patch("app.core.tts.generate_single_chunk"):
                    with patch("app.core.tts.stitch_chunk_files") as mock_stitch:
                        mock_split.return_value = ["chunk1"]

                        def fake_stitch(**kwargs):
                            with open(kwargs["output_path"], "wb") as f:
                                f.write(b"wav_data")

                        mock_stitch.side_effect = fake_stitch

                        result = generate_speech("test text", output_format="wav")

                        assert result == (b"wav_data", "audio/wav")
                        call_kwargs = mock_stitch.call_args[1]
                        assert call_kwargs["output_format"] == "wav"


class TestApplyCpuThreadingBudget:
    """Cover PyTorch thread-setter edge cases on CPU init."""

    def test_handles_set_interop_and_intraop_errors(self):
        from app.core.tts import _apply_cpu_threading_budget

        with patch("app.core.tts.torch.set_num_interop_threads", side_effect=RuntimeError("already set")):
            with patch("app.core.tts.torch.set_num_threads", side_effect=ValueError("bad")):
                with patch("app.core.tts.logger") as mock_log:
                    _apply_cpu_threading_budget()
        mock_log.debug.assert_called()
        mock_log.warning.assert_called()
