import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import create_app

app = create_app()

@pytest.fixture
def client():
    return TestClient(app)

class TestSynthesizeStream:
    def test_synthesize_stream_not_ready(self, client):
        with patch("app.api.endpoints.speech.is_ready", return_value=False):
            response = client.post("/api/synthesize/stream", data={"text": "Hello world"})
            assert response.status_code == 503

    def test_synthesize_stream_invalid_format(self, client):
        with patch("app.api.endpoints.speech.is_ready", return_value=True):
            response = client.post("/api/synthesize/stream", data={"text": "Hello world", "output_format": "invalid"})
            assert response.status_code == 400

    def test_synthesize_stream_success(self, client):
        async def mock_generate():
            yield b"chunk1"
            yield b"chunk2"

        with patch("app.api.endpoints.speech.is_ready", return_value=True), \
             patch("app.core.tts.generate_speech_stream", return_value=mock_generate()), \
             patch("app.api.endpoints.speech.get_voice_library") as mock_lib, \
             patch("app.api.endpoints.speech.Config.TTS_ENGINE", "kyutai"):
            
            response = client.post("/api/synthesize/stream", data={"text": "Hello world"})
            assert response.status_code == 200
            assert response.content == b"chunk1chunk2"

    def test_synthesize_stream_voice_not_found(self, client):
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_voice_path.return_value = None

        with patch("app.api.endpoints.speech.is_ready", return_value=True), \
             patch("app.api.endpoints.speech.get_voice_library", return_value=mock_voice_lib), \
             patch("app.api.endpoints.speech.Config.TTS_ENGINE", "chatterbox"):
            response = client.post("/api/synthesize/stream", data={"text": "Hello world", "voice": "unknown"})
            assert response.status_code == 404

    def test_synthesize_stream_with_voice(self, client):
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_voice_path.return_value = "/path/to/voice.wav"

        async def mock_generate():
            yield b"chunk1"

        with patch("app.api.endpoints.speech.is_ready", return_value=True), \
             patch("app.core.tts.generate_speech_stream", return_value=mock_generate()), \
             patch("app.api.endpoints.speech.get_voice_library", return_value=mock_voice_lib), \
             patch("app.api.endpoints.speech.Config.TTS_ENGINE", "chatterbox"):
            response = client.post("/api/synthesize/stream", data={"text": "Hello world", "voice": "known_voice"})
            assert response.status_code == 200

    def test_synthesize_stream_with_file(self, client):
        async def mock_generate():
            yield b"chunk1"

        with patch("app.api.endpoints.speech.is_ready", return_value=True), \
             patch("app.core.tts.generate_speech_stream", return_value=mock_generate()):
            response = client.post(
                "/api/synthesize/stream",
                data={"text": "Hello world"},
                files={"reference_audio": ("test.wav", b"audio_data", "audio/wav")}
            )
            assert response.status_code == 200

class TestGenerateSpeechStream:
    @pytest.mark.asyncio
    async def test_generate_speech_stream_model_not_initialized(self):
        from app.core.tts import generate_speech_stream
        with patch("app.core.tts._model", None):
            generator = generate_speech_stream("Hello world")
            with pytest.raises(RuntimeError):
                await generator.__anext__()

    @pytest.mark.asyncio
    async def test_generate_speech_stream_success(self):
        from app.core.tts import generate_speech_stream
        mock_model = MagicMock()
        mock_model.sample_rate = 24000
        mock_model.get_state_for_audio_prompt = MagicMock(return_value="mock_state")
        import torch
        mock_model.generate_audio = MagicMock(return_value=torch.randn(1, 24000))

        import asyncio
        read_event = asyncio.Event()

        async def mock_read(*args, **kwargs):
            await read_event.wait()
            if not getattr(mock_read, "called", False):
                mock_read.called = True
                return b"audio_chunk"
            return b""
            
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout.read = mock_read
        
        # We need a way to set the event once write is called
        async def mock_write(*args, **kwargs):
            read_event.set()
        mock_process.stdin.write = AsyncMock(side_effect=mock_write)
        
        # Also set the event if error occurs so it doesn't hang
        async def fallback():
            await asyncio.sleep(2)
            read_event.set()
        asyncio.create_task(fallback())
        
        with patch("app.core.tts._model", mock_model), \
             patch("app.core.tts.Config.TTS_ENGINE", "kyutai"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            generator = generate_speech_stream("Hello world.")
            chunks = []
            async for chunk in generator:
                chunks.append(chunk)
                
            import asyncio
            await asyncio.sleep(0.1)
    
            assert chunks == [b"audio_chunk"]
            mock_process.stdin.write.assert_called()
            mock_process.stdin.close.assert_called()
