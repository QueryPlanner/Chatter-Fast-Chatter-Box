FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    ffmpeg \
    git \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .python-version uv.lock ./
COPY app/ ./app/
COPY voices/ ./voices/
COPY outputs/ ./outputs/
COPY generate_turbo.py ./

# Create .env from example if not exists
COPY .env.example ./

# Reproducible install; fails if lock is missing or out of date
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8000

# Run the server
# Use the venv directly so `uv run` does not re-sync and alter packages at startup
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
