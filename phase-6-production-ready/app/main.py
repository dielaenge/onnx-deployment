from .inference_engine import AcousticModelProcessor
from .audio_utils import MelSpectrogram

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import FileResponse
import uvicorn

import numpy as np

import json
import logging
from pathlib import Path

from contextlib import asynccontextmanager

import uuid
import time

# Identify Base Directory
BASE_DIR = Path(__file__).resolve().parent

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- ONNX model path ---
MODEL_PATH = BASE_DIR / "models" / "bape_2026-04-13_15-13-22.onnx"

# contextlib.asynccontextmanager used witht the lifespan parameter is recommended for defining app startup and shutdown in FastAPI

# the @asynccontextmanager decorator creats an asynchronous context manager
# it expects an asynchronous function which *yield*s exactly one value
# the code before yield is run at startup, the code after at shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # AT STARTUP: initialize processor and melspec_processor 
    logger.info("BAPE app starting up…")
    # initialize model and melspec preprocessor
    app.state.processor = AcousticModelProcessor(MODEL_PATH)
    logger.info("AcousticModelProcessor initialized as processor.")
    app.state.melspec_preprocessor = MelSpectrogram(
    sr=16000, 
    n_fft=64, 
    hop_size=32, 
    n_mels=16, 
    fmin=20, 
    fmax=8000, 
    power=2.0, 
    log_mag=True,
    trunc=2000
    )
    logger.info("MelSpectrogram initialized as melspec_preprocessor.")

    yield

    logger.info("BAPE app shutting down…")
    # AT SHUTDOWN: Clean up the ML models and release the resources
    app.state.processor = None
    logger.info("CLEANUP: processor set to None.")
    app.state.melspec_preprocessor = None
    logger.info("CLEANUP: melspec_preprocessor set to None.")
    
app = FastAPI(lifespan=lifespan)

#API ENDPOINTS

#HEALTHCHECK ENDPOINT
@app.get("/health")
def health_check(request: Request):
    """Healthcheck endpoint."""
    processor = request.app.state.processor
    return {
        "status": "ok",
        "model_loaded": processor is not None
        }

# DEFAULT ENDPOINT
@app.get("/")
async def get():
    return FileResponse( BASE_DIR / ".."  / "src" / "index.html")

@app.get("/processor.js")
async def get_processor():
    return FileResponse( BASE_DIR / ".." / "src" / "processor.js")

# establish websocket connection
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket.")

    processor = websocket.app.state.processor
    melspec_preprocessor = websocket.app.state.melspec_preprocessor
    audio_buffer = np.array([], dtype=np.float32)
    try:
        while True:
            # receive binary data from frontend websocket endpoint
            raw_data = await websocket.receive_bytes()

            # convert bytes to float32 np array
            converted_data = np.frombuffer(raw_data, dtype=np.float32)
            
            # concatenate converted_data (spliced in index.html's startRecording function) to rolling audio_buffer
            audio_buffer = np.concatenate((audio_buffer, converted_data))

            #check if buffer has enough data for 4 seconds (required by onnx model)
            if len(audio_buffer) >= 64000:
                
                # Initialize inference loop
                session_id = str(uuid.uuid4())
                logger.info("%s samples available.", len(audio_buffer))
                logger.info("session_id: %s", session_id)
                spectrogram_chunk = melspec_preprocessor(audio_buffer)

                # calculate mean and standard
                mean = spectrogram_chunk.mean()
                std = spectrogram_chunk.std()

                # standardize raw spectrogram tensor
                standardized_spectrogram = (spectrogram_chunk - mean) / (std + 1e-12)

                # convert to numpy array
                standardized_spectrogram_nparray = standardized_spectrogram.numpy()
                
                # reshape to 4D tensor
                standardized_spectrogram_4d = np.expand_dims(standardized_spectrogram_nparray, axis=(0,1))

                # run inference
                start_time = time.perf_counter()
                results = processor.run_inference(standardized_spectrogram_4d)
                end_time = time.perf_counter()
                inference_time_ms = ((end_time - start_time)*1000, 2)

                # onnx model returns a list of 3 np arrays, which need to be converted to standard python lists so we can send them as a JSON
                response_json = {
                    "latents": results["latents"].tolist(),
                    "params": results["params"].tolist(),
                    "quantiles": results["quantiles"].tolist()
                }
                
                # Log session data
                log_data = {
                    "event": "inference_complete",
                    "session_id": session_id,
                    "inference_time_ms": inference_time_ms,
                    "shape": standardized_spectrogram_4d.shape,
                    "t60_estimate_1khz_sample": results["params"].tolist()[0][0]
                }

                logger.info(json.dumps(log_data))

                # send results
                await websocket.send_json(response_json)

                # slice buffer to keep the latter half of the window (2 seconds; which will be concatenated with new input if available)
                audio_buffer = audio_buffer[-32000:]

    except Exception as e:
        logger.exception("Error in Websocket: %s", e)

# LAUNCH ON LOCALHOST
#if __name__ == "__main__":
#    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# LAUNCH ON AWS - defined port 8080 in ecs.tf
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
