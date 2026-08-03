# Pulls a pre-built image from Docker Hub that contains the FFMPEG static binaries // edited bc johnvansickle source was too unreliable
FROM mwader/static-ffmpeg:6.1 AS ffmpeg_source

# Use the official Docker image for Python 3.11
FROM python:3.11-slim

# set WORKDIR, everything from here, happens in /app
WORKDIR /app

# copyy FFMPEG from the source image
COPY --from=ffmpeg_source /ffmpeg /usr/bin/
COPY --from=ffmpeg_source /ffprobe /usr/bin/

#install tar xz unzip and libsndfile // from yum to apt-get as we switched from an Amazon Linux distribution to a Debian/Red Hat 
RUN apt-get update \
    && apt-get install -y \
    tar \
    xz-utils \
    gzip \
    unzip \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install dependencies
COPY requirements.txt .

#install CPU-only dependencies for torch to save space and time / download from explicit url to avoid dowonloading cuda backend; step separated from dependency installations to prevent conflicts
RUN pip install --upgrade pip \ 
    && pip install --no-cache-dir -r /app/requirements.txt

# copy code
COPY app/ app/

# set env variables
ENV PORT=8080
ENV NUMBA_CACHE_DIR=/tmp
ENV JOBLIB_TEMP_FOLDER=/tmp

# Start the application
# look for the app object in app/main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]