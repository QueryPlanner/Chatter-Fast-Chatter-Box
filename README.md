# Fast-Chatterbox

FastAPI server for Chatterbox TTS with voice cloning support.

## Features

- **Text-to-Speech Synthesis**: Generate speech from text using ChatterboxTurboTTS
- **Voice Cloning**: Clone voices from reference audio samples (>5s recommended)
- **Voice Library**: Manage multiple voice profiles with aliases
- **Long Text Support**: Automatic sentence-based chunking for long text inputs
- **Multiple Formats**: Output as MP3 (default) or WAV
- **Docker Ready**: Easy deployment with Docker and docker-compose

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fast-chatterbox.git
cd fast-chatterbox

# Start with docker-compose
docker-compose up -d

# Or build and run manually
docker build -t fast-chatterbox .
docker run -p 8000:8000 fast-chatterbox
```

The API will be available at http://localhost:8000

### Option 2: Local Development

**Prerequisites:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (for MP3 conversion: `brew install ffmpeg` on macOS)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fast-chatterbox.git
cd fast-chatterbox

# Install dependencies
uv sync

# Run the server
uv run uvicorn app.main:app --reload
```

> First startup downloads model weights automatically through
> `ChatterboxTurboTTS.from_pretrained(...)`. This can take a few minutes
> depending on your connection.

> Internet is required for the first model download. After that, model files
> are reused from your local cache.

---

## API Documentation

Once running, access the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Endpoints

### POST /synthesize

Generate speech from text.

**Parameters (form-data):**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | Yes | - | Text to synthesize (max 10,000 chars) |
| `voice` | string | No | dan | Voice name or alias from library |
| `output_format` | string | No | mp3 | Output format: `mp3` or `wav` |
| `max_chunk_chars` | int | No | 320 | Max characters per chunk (50-1000) |
| `chunk_gap_ms` | int | No | 120 | Gap between chunks in milliseconds |
| `reference_audio` | file | No | - | Upload custom reference audio for cloning |

**Examples:**

```bash
# Basic synthesis (uses default voice "dan")
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello, how are you today?" \
  --output speech.mp3

# Use a specific voice from the library
curl -X POST http://localhost:8000/synthesize \
  -F "text=Welcome to our podcast!" \
  -F "voice=huberman" \
  --output speech.mp3

# Upload custom reference audio for voice cloning
curl -X POST http://localhost:8000/synthesize \
  -F "text=This will sound like the uploaded voice" \
  -F "reference_audio=@my_voice_sample.wav" \
  --output speech.mp3

# Get WAV output instead of MP3
curl -X POST http://localhost:8000/synthesize \
  -F "text=High quality audio output" \
  -F "output_format=wav" \
  --output speech.wav

# Long text with custom chunking
curl -X POST http://localhost:8000/synthesize \
  -F "text=This is a very long text that will be automatically chunked..." \
  -F "max_chunk_chars=200" \
  -F "chunk_gap_ms=150" \
  --output speech.mp3
```

**Response:**
- `Content-Type`: `audio/mpeg` (MP3) or `audio/wav` (WAV)
- `Content-Disposition`: `attachment; filename="speech.mp3"`

---

### GET /voices

List all available voices in the library.

```bash
curl http://localhost:8000/voices
```

**Response:**
```json
{
  "voices": [
    {
      "name": "dan_prompt_1",
      "filename": "dan_prompt_1.wav",
      "file_size": 3840078,
      "created": "2025-03-29T12:00:00",
      "exists": true
    }
  ],
  "count": 6,
  "default_voice": "dan_prompt_1"
}
```

---

### GET /voices/{voice_name}

Get information about a specific voice.

```bash
curl http://localhost:8000/voices/dan
```

**Response:**
```json
{
  "name": "dan_prompt_1",
  "filename": "dan_prompt_1.wav",
  "file_size": 3840078,
  "created": "2025-03-29T12:00:00",
  "exists": true
}
```

---

### POST /voices

Upload a new voice to the library.

```bash
curl -X POST http://localhost:8000/voices \
  -F "voice_name=my_custom_voice" \
  -F "voice_file=@voice_sample.wav"
```

**Response:**
```json
{
  "message": "Voice uploaded successfully",
  "voice": {
    "name": "my_custom_voice",
    "filename": "my_custom_voice.wav",
    "file_size": 5000000
  }
}
```

---

### DELETE /voices/{voice_name}

Delete a voice from the library.

```bash
curl -X DELETE http://localhost:8000/voices/my_custom_voice
```

---

### POST /voices/default

Set the default voice for synthesis.

```bash
curl -X POST http://localhost:8000/voices/default \
  -F "voice_name=huberman"
```

---

### GET /voices/{voice_name}/download

Download a voice file.

```bash
curl http://localhost:8000/voices/dan/download --output dan_voice.wav
```

---

### GET /health

Check server health and model status.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "mps",
  "default_voice": "dan_prompt_1",
  "error": null
}
```

---

### GET /ping

Simple connectivity check.

```bash
curl http://localhost:8000/ping
```

**Response:**
```json
{
  "status": "ok",
  "message": "Server is running"
}
```

---

## Available Voices

The server comes with pre-configured voices:

| Name | Alias | File | Description |
|------|-------|------|-------------|
| `dan_prompt_1` | `dan` | dan_prompt_1.wav | Default voice - clear, professional |
| `donald_prompt` | `donald` | donald_prompt.wav | Donald voice variant 1 |
| `donald_prompt_2` | - | donald_prompt_2.wav | Donald voice variant 2 |
| `donald_prompt_3` | - | donald_prompt_3.wav | Donald voice variant 3 |
| `huberman_prompt` | `huberman` | huberman_prompt.wav | Huberman-style voice |
| `snoop_dogg_prompt` | `snoop` | snoop_dogg_prompt.wav | Snoop Dogg-style voice |

Use either the full name or the alias in API calls.

---

## Configuration

Create a `.env` file (copy from `.env.example`):

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# TTS Configuration
MAX_CHUNK_CHARS=320      # Characters per chunk for long text
CHUNK_GAP_MS=120         # Silence between chunks (milliseconds)

# Device: auto, cuda, mps, or cpu
DEVICE=auto

# Default voice (name or alias)
DEFAULT_VOICE=dan

# Output format: mp3 or wav
DEFAULT_OUTPUT_FORMAT=mp3
```

### Device Selection

- `auto` - Automatically select best available (cuda > mps > cpu)
- `cuda` - Force NVIDIA GPU
- `mps` - Force Apple Silicon GPU
- `cpu` - Force CPU (slowest but most compatible)

---

## Docker Deployment

### Basic Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### GPU Support (NVIDIA)

For CUDA support, modify `docker-compose.yml`:

```yaml
services:
  fast-chatterbox:
    build: .
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Then run:
```bash
docker-compose up -d
```

### Persistent Volumes

The default configuration mounts local directories:
- `./voices` - Voice library (persist your custom voices)
- `./outputs` - Generated audio files

---

## CLI Usage

The original `generate_turbo.py` script is available for command-line usage:

```bash
# Basic usage with default voice
uv run python generate_turbo.py --text "Hello world"

# With specific reference audio
uv run python generate_turbo.py \
  --ref voices/dan_prompt_1.wav \
  --text "Custom voice synthesis"

# Save to specific file
uv run python generate_turbo.py \
  --text "Hello world" \
  --out outputs/my_speech.wav

# Long text with chunking options
uv run python generate_turbo.py \
  --text-file long_text.txt \
  --max-chunk-chars 280 \
  --chunk-gap-ms 150
```

---

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run with hot reload
uv run uvicorn app.main:app --reload

# Run on specific port
uv run uvicorn app.main:app --port 8080
```

---

## Troubleshooting

### Model Loading Issues

If the model fails to load:
1. Check available memory (model requires ~4GB RAM)
2. Try forcing CPU mode: `DEVICE=cpu` in `.env`
3. Check logs: `docker-compose logs -f`
4. Verify startup sequence:
   - `GET /ping` should return immediately
   - `GET /health` should move from `initializing` to `healthy`
5. Warm up the model manually to confirm download/auth works:
   ```bash
   uv run python generate_turbo.py --text "test"
   ```

### Startup Import Errors

If startup fails before `/health` is available (for example
`ModuleNotFoundError`), the model initialization step never runs. Fix import
errors first, then restart the server so the model can download/load.

### First-Run Download Notes

- First run may be slow while model artifacts are downloaded.
- If your network is restricted, run once on an unrestricted connection.
- Re-running after a completed download should be much faster because cached
  artifacts are reused.

### MP3 Conversion Fails

Ensure ffmpeg is installed:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Docker (already included in image)
# No action needed
```

### Voice Not Found

Check available voices:
```bash
curl http://localhost:8000/voices
```

Make sure you're using the correct name or alias.

---

## License

MIT
