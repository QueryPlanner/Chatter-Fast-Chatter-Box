# Fast-Chatterbox

FastAPI server for Chatterbox TTS with voice cloning support.

## Features

- **Text-to-Speech Synthesis**: Generate speech from text using ChatterboxTurboTTS
- **Voice Cloning**: Clone voices from reference audio samples
- **Voice Library**: Manage multiple voice profiles
- **Long Text Support**: Automatic chunking for long text inputs
- **Multiple Formats**: Output as MP3 (default) or WAV

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (for MP3 conversion)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd chatterbox-tts

# Install dependencies
uv sync

# Run the server
uv run uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Speech Synthesis

```bash
# Basic synthesis (uses default voice)
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello, how are you today?" \
  --output speech.mp3

# With specific voice
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello world" \
  -F "voice=dan" \
  --output speech.mp3

# With custom reference audio
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello world" \
  -F "reference_audio=@my_voice.wav" \
  --output speech.mp3

# WAV output
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello world" \
  -F "output_format=wav" \
  --output speech.wav
```

### Voice Management

```bash
# List voices
curl http://localhost:8000/voices

# Get voice info
curl http://localhost:8000/voices/dan

# Upload new voice
curl -X POST http://localhost:8000/voices \
  -F "voice_name=my_voice" \
  -F "voice_file=@voice_sample.wav"

# Set default voice
curl -X POST http://localhost:8000/voices/default \
  -F "voice_name=dan"
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Configuration

Create a `.env` file (copy from `.env.example`):

```env
# Server
HOST=0.0.0.0
PORT=8000

# TTS
MAX_CHUNK_CHARS=320
CHUNK_GAP_MS=120

# Device: auto, cuda, mps, or cpu
DEVICE=auto

# Default voice
DEFAULT_VOICE=dan

# Output format: mp3 or wav
DEFAULT_OUTPUT_FORMAT=mp3
```

## Available Voices

The server comes with pre-configured voices:

| Name | Alias | Description |
|------|-------|-------------|
| dan_prompt_1 | dan | Default voice |
| donald_prompt | donald | Donald voice variant 1 |
| donald_prompt_2 | - | Donald voice variant 2 |
| donald_prompt_3 | - | Donald voice variant 3 |
| huberman_prompt | huberman | Huberman-style voice |
| snoop_dogg_prompt | snoop | Snoop Dogg-style voice |

## CLI Usage

The original `generate_turbo.py` script is still available for CLI usage:

```bash
# Basic usage
uv run python generate_turbo.py --text "Hello world"

# With reference audio
uv run python generate_turbo.py --ref voices/dan_prompt_1.wav --text "Custom voice"
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run with hot reload
uv run uvicorn app.main:app --reload
```

## License

MIT
