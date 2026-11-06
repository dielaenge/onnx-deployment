# Pulls a pre-built image from Docker Hub that contains the FFMPEG static binaries
FROM mwader/static-ffmpeg:6.1 AS ffmpeg_source

# Use the official Docker image for Python 3.11
FROM python:3.11-slim

# get pinned uv version
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

# set WORKDIR, everything from here, happens in /app
WORKDIR /app

# copyy FFMPEG from the source image
COPY --from=ffmpeg_source /ffmpeg /usr/bin/
COPY --from=ffmpeg_source /ffprobe /usr/bin/

# APT // install archive tooling // clear state information and package metadata
# from yum to apt-get = switched from an Amazon Linux distribution to a Debian/Red Hat 
RUN apt-get update && apt-get install -y \
    tar xz-utils gzip unzip libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# dependencies are synced with uv.lock, separate dependency and code layer and keep dependencies in cache when only app is edited
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project

# copy code
COPY app/ app/

# set env variables
ENV UV_COMPILE_BYTECODE=1 \
    # Enable copy mode to support bind mount caching
    UV_LINK_MODE=copy \
    PORT=8080 \
    NUMBA_CACHE_DIR=/tmp \
    JOBLIB_TEMP_FOLDER=/tmp \
    # replaces manual venv activation
    PATH="/app/.venv/bin:$PATH" 

# Start the application
# look for the app object in app/main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]