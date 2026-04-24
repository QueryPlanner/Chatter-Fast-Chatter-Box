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

### Option 1: Local development with `uv` (recommended on macOS)

On **macOS**, running the API directly on the host is usually **much faster** than
Docker: PyTorch can use **MPS** (Apple GPU) when `DEVICE=auto`, whereas a
container on Docker Desktop is Linux on a **virtual CPU** with **no Metal/MPS**,
so synthesis is CPU-only and pays VM overhead. Use Docker when you need Linux
deployment parity or server environments; for daily use on a Mac, prefer `uv`.

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), and ffmpeg
(`brew install ffmpeg` on macOS).

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fast-chatterbox.git
cd fast-chatterbox

# Install dependencies
uv sync

# Run the server (MPS on Apple Silicon when DEVICE=auto)
uv run uvicorn app.main:app --reload
# Or: bash scripts/dev.sh  (same, loads .env from repo root)
```

The API will be available at http://localhost:8000. Confirm `GET /health` shows
your device (e.g. `mps` on Apple Silicon when the model is ready).

> First startup downloads model weights through `ChatterboxTurboTTS.from_pretrained(...)`.
> Internet is required once; after that, weights are cached locally.

### Option 2: Docker

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fast-chatterbox.git
cd fast-chatterbox

# Start with docker-compose
docker compose up -d

# Or build and run manually
docker build -t fast-chatterbox .
docker run -p 8000:8000 fast-chatterbox
```

The API will be available at http://localhost:8000.

Verify the server:

```bash
curl http://localhost:8000/ping
curl http://localhost:8000/health
```

### Option 3: macOS LaunchDaemon (MPS, crash restart, auto-start at boot)

For a Mac you use daily, you can run the same stack as Option 1 under a
**system LaunchDaemon**: native `uv` + `uvicorn` (no `--reload`), **MPS** when
`DEVICE=auto`, **restart on crash**, logs under `~/Library/Logs/fast-chatterbox/`,
and **start at login/boot**. `Dockerfile` / `docker-compose.yml` stay as-is for
Linux deploy and CI.

**Day 0 (one-time, from a fresh clone):**

1. `brew install ffmpeg uv` (skip if already installed).
2. `cd /path/to/Chatter-Fast-Chatter-Box && uv sync --frozen` (or `uv sync` if you
   are not using a committed lockfile).
3. Ensure `.env` has `HF_TOKEN` (and any other vars you rely on); copy from
   `.env.example` if needed.
4. Warm the model cache as your user (avoids first-boot download failures in the
   daemon):
   `uv run python generate_turbo.py --text "warmup"`
5. Free port 8000: `docker compose down` if a container is still listening.
6. `bash scripts/install-launchd.sh` (prompts for `sudo` to install the plist).
7. `curl http://localhost:8000/health` — expect `"device": "mps"` on Apple
   Silicon (when Metal is available) and `"model_loaded": true`.

Prod-style process (no reload) is started by
`scripts/start-prod.sh` (`uv run --frozen uvicorn …`). For local iteration with
hot reload, use `bash scripts/dev.sh` (stop the daemon first if port 8000 is
busy — see **Stopping the server** below).

**Day 1 (daily ops):**

- Status: `sudo launchctl print system/com.fastchatterbox.server | head`
- Tail logs:
  `tail -f ~/Library/Logs/fast-chatterbox/stdout.log ~/Library/Logs/fast-chatterbox/stderr.log`
- Force restart:
  `sudo launchctl kickstart -k system/com.fastchatterbox.server`
- Uninstall: `bash scripts/uninstall-launchd.sh` (optional `--purge-logs`)

#### Runtime comparison

| Mode | Typical Mac device | Wins | Trade-offs |
|------|-------------------|------|------------|
| **Docker on Mac** | `cpu` in Linux VM (no Metal/MPS) | Reproducible image, `restart: unless-stopped`, simple `compose up/down` | Slower, VM CPU/RAM overhead, no MPS |
| **LaunchDaemon + `uv` (this option)** | `mps` on Apple Silicon when `DEVICE=auto` | Native speed, crash restart, boot start, persistent stdout/stderr logs | No container isolation; tied to host Python / `uv` / ffmpeg |
| **Docker for deploy only** | N/A locally | Same image as Linux servers / CI | Use Options 1 or 3 for daily Mac TTS |

#### Risks and caveats

- **Full Disk Access**: usually unnecessary for a repo under your home directory;
  if the daemon cannot read `voices/` on first boot, check macOS privacy settings.
- **First-run weights**: warm the cache (Day 0 step 4) so the daemon does not
  depend on Hub access immediately at boot.
- **MPS at boot**: in rare cases Metal may not be ready very early; verify with
  `GET /health` after reboot.
- **Port conflict**: if something else holds `:8000`, launchd may respawn in a
  loop — run `lsof -nP -iTCP:8000 -sTCP:LISTEN` and stop the other process.
- **`uv` location**: the installer records the resolved `uv` path in the plist.
  If you move `uv`, re-run `scripts/install-launchd.sh`.
- **`app/main.py`**: may still default to `reload=True` for `python -m` style
  entrypoints; the daemon bypasses that by invoking `uvicorn` directly.

#### Stopping the server

- **Stop once, keep installed, do not auto-start on next boot** (unload until you
  bootstrap again):

  ```bash
  sudo launchctl bootout system/com.fastchatterbox.server
  ```

  The plist remains in `/Library/LaunchDaemons/`. Bring it back without reboot:

  ```bash
  sudo launchctl bootstrap system /Library/LaunchDaemons/com.fastchatterbox.server.plist
  ```

- **Disable across reboots** (still installed):

  ```bash
  sudo launchctl disable system/com.fastchatterbox.server
  sudo launchctl bootout  system/com.fastchatterbox.server
  ```

  Re-enable:

  ```bash
  sudo launchctl enable    system/com.fastchatterbox.server
  sudo launchctl bootstrap system /Library/LaunchDaemons/com.fastchatterbox.server.plist
  ```

- **Uninstall completely** (stop, remove plist; logs kept unless purged):

  ```bash
  bash scripts/uninstall-launchd.sh
  ```

  Pass `--purge-logs` to also remove `~/Library/Logs/fast-chatterbox/`.

- **Emergency stop** (crash loop or stubborn process; `KeepAlive` respawns
  after `kill -9` unless you disable or bootout first):

  ```bash
  pgrep -fa 'uvicorn app.main:app' ; pgrep -fa 'start-prod.sh'
  sudo launchctl disable system/com.fastchatterbox.server
  sudo kill -9 <pid>
  sudo launchctl enable    system/com.fastchatterbox.server
  sudo launchctl kickstart -k system/com.fastchatterbox.server
  ```

- **Dev server** (`bash scripts/dev.sh`): stop with `Ctrl+C` in that terminal, or
  `pkill -f 'uvicorn app.main:app'` if orphaned (check `pgrep -fa` first if both
  daemon and dev might be running).

- **Docker** (old container on 8000): `docker compose down`

- **Check listeners on 8000:**

  ```bash
  lsof -nP -iTCP:8000 -sTCP:LISTEN
  ```

#### Verify after reboot (optional)

- `curl http://localhost:8000/health` — `device` should be `mps` when Metal is
  available; `model_loaded` should be `true`.
- Crash restart: `kill -9` the `uvicorn` worker PID and confirm launchd respawns
  after the `ThrottleInterval` (10s) in the plist.

---

## Usage in 60 Seconds

1. Start the server (Docker or local development from Quick Start).
2. Confirm readiness:
   - `GET /ping` should return quickly.
   - `GET /health` should report `"status": "healthy"`.
3. Generate your first audio file:

```bash
curl -X POST http://localhost:8000/synthesize \
  -F "text=Hello from Fast-Chatterbox" \
  --output speech.mp3
```

4. Play the output:
   - macOS: `open speech.mp3`
   - Linux: `xdg-open speech.mp3`

If you need a specific voice, list available options with:

```bash
curl http://localhost:8000/voices
```

---

## Just ask Claude Code

Use this prompt with Claude Code when you want it to deploy and run Fast-Chatterbox locally on a MacBook:

```text
You are in the Fast-Chatterbox repository on macOS.

Goal:
- Run Fast-Chatterbox locally and verify it works end-to-end.

Please do the following:
1) Check prerequisites and install missing tools:
   - Homebrew (if needed)
   - uv
   - ffmpeg
2) Install project dependencies with uv.
3) Start the API server locally (uv run uvicorn app.main:app --reload).
4) Verify startup using:
   - GET /ping
   - GET /health
5) Run a synthesis request and save output to speech.mp3.
6) Confirm the output file exists and report exact commands used.
7) If anything fails, diagnose the root cause and fix it before continuing.

Constraints:
- Use safe, non-destructive commands only.
- Explain each step briefly.
- Stop only after the server is running and synthesis succeeds.
```

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
| `max_sentences_per_chunk` | int | No | 3 | Max sentences per audio chunk (1-50) |
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
      "name": "dan_carlin",
      "filename": "dan_carlin.wav",
      "file_size": 3840078,
      "created": "2025-03-29T12:00:00",
      "exists": true
    }
  ],
  "count": 6,
  "default_voice": "dan_carlin"
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
  "name": "dan_carlin",
  "filename": "dan_carlin.wav",
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
  "default_voice": "dan_carlin",
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
| `dan_carlin` | `dan` | dan_carlin.wav | Default voice (Dan Carlin style) |
| `donald_trump` | `donald` | donald_trump.wav | Trump-style voice |
| `donald_trump_2` | `donald_2` | donald_trump_2.wav | Trump-style variant 2 |
| `donald_trump_3` | `donald_3` | donald_trump_3.wav | Trump-style variant 3 |
| `andrew_huberman` | `huberman` | andrew_huberman.wav | Huberman-style voice |
| `snoop_dogg` | `snoop` | snoop_dogg.wav | Snoop Dogg-style voice |

Use either the full name or the alias in API calls.

---

## Configuration

Create a `.env` file (copy from `.env.example`):

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# TTS Configuration
MAX_SENTENCES_PER_CHUNK=3  # Sentences per TTS chunk (1-50)
MAX_CHUNK_CHARS=320      # Characters per chunk for long text
CHUNK_GAP_MS=120         # Silence between chunks (milliseconds)

# Device: auto, cuda, mps, or cpu
DEVICE=auto

# CPU: thread budget for PyTorch / OpenMP (0 = use all logical CPUs, 1–256 to set a cap)
TORCH_NUM_THREADS=0

# Default voice (name or alias)
DEFAULT_VOICE=dan

# Output format: mp3 or wav
DEFAULT_OUTPUT_FORMAT=mp3
```

### Device Selection

- `auto` - Automatically select best available (cuda > mps > cpu)
- `cuda` - Force NVIDIA GPU
- `mps` - Apple Silicon **Metal** (only when running **natively** on macOS, not
  inside Docker on Mac, where the guest is Linux and typically **cpu**)
- `cpu` - Force CPU (slowest but most compatible)

### CPU thread budget (`TORCH_NUM_THREADS`)

On CPU, synthesis speed depends on how many threads OpenMP, MKL, and PyTorch
use. By default, `TORCH_NUM_THREADS=0` picks **all logical CPUs** the process
is allowed to use. Set a positive number (1–256) to cap usage if you are
running other services on the same host.

- **Linux / macOS (native)**: the default is usually optimal; you can still cap
  with `TORCH_NUM_THREADS=4` if needed.
- **Docker Desktop (Mac/Windows)**: the container only sees the CPUs you assign
  to the Docker VM. Increase that under **Settings → Resources** if generation
  is still slow, and keep `TORCH_NUM_THREADS=0` so the app uses all of them.

---

## Docker Deployment

### Basic Deployment

Add a project `.env` (copy from `.env.example`) and set `HF_TOKEN` with a
[Hugging Face read token](https://huggingface.co/settings/tokens) so the
container can authenticate with the Hub (better rate limits and faster
first-time downloads). `docker-compose.yml` passes `HF_TOKEN` into the service
using Compose’s `.env` substitution; the file is not copied into the image.

The image is built with `uv.lock` in the build context and `uv sync --frozen` so
`resemble-perth` resolves exactly as on your machine (see `resemble-perth` from
`tool.uv.sources` in `pyproject.toml`). **Do not** add `uv.lock` to
`.dockerignore` or the container may install the wrong `perth` and fail model
load with `'NoneType' object is not callable`. The first image build is slower
because the Dockerfile installs a compiler toolchain needed for
`praat-parselmouth` (a dependency of Git-based `resemble-perth` on Linux).

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
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
- Named volume `hf-cache` - Caches Hugging Face downloads under `/root/.cache/huggingface` so
  model weights survive `docker compose down` and container rebuilds

---

## CLI Usage

The original `generate_turbo.py` script is available for command-line usage:

```bash
# Basic usage with default voice
uv run python generate_turbo.py --text "Hello world"

# With specific reference audio
uv run python generate_turbo.py \
  --ref voices/dan_carlin.wav \
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
uv sync --group dev

# Run with hot reload
uv run uvicorn app.main:app --reload
# Or: bash scripts/dev.sh

# Run on specific port
uv run uvicorn app.main:app --port 8080
```

---

## Troubleshooting

### Model Loading Issues

If the model fails to load:
1. Check available memory (model requires ~4GB RAM)
2. If you see `'NoneType' object is not callable` right after download: the
   `resemble-perth` (watermark) library must be the version from this repo’s
   `pyproject.toml` / `uv.lock` (GitHub `resemble-ai/Perth`, not a broken PyPI
   install). Re-run `uv sync` and rebuild the Docker image.
3. Try forcing CPU mode: `DEVICE=cpu` in `.env`
4. Check logs: `docker compose logs -f`
5. Verify startup sequence:
   - `GET /ping` should return immediately
   - `GET /health` should move from `initializing` to `healthy`
6. Warm up the model manually to confirm download/auth works:
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
