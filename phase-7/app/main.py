from .inference_engine import AcousticModelProcessor
from .audio_utils import MelSpectrogram

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

import numpy as np

import json
import logging
from pathlib import Path

from contextlib import asynccontextmanager

import os
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
T60_MODEL_PATH = BASE_DIR / "models" / "t60_bape_2025-11-18_17-40-57.onnx"
C50_MODEL_PATH = BASE_DIR / "models" / "c50_bape_2025-11-18_19-33-41.onnx"

# contextlib.asynccontextmanager used witht the lifespan parameter is recommended for defining app startup and shutdown in FastAPI

# the @asynccontextmanager decorator creates an asynchronous context manager
# it expects an asynchronous function which *yield*s exactly one value
# the code before yield is run at startup, the code after at shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # AT STARTUP: initialize processor and melspec_processor 
    logger.info("BAPE app starting up…")
    # initialize model and melspec preprocessor
    app.state.t60_processor = AcousticModelProcessor(T60_MODEL_PATH)
    logger.info("AcousticModelProcessor for T60 params initialized as t60_processor.")
    app.state.c50_processor = AcousticModelProcessor(C50_MODEL_PATH)
    logger.info("AcousticModelProcessor for C50 params initialized as processor.")
    app.state.melspec_preprocessor = MelSpectrogram(
    sr=16000, 
    n_fft=64, 
    hop_size=32, 
    n_mels=16, 
    fmin=20, 
    fmax=8000, 
    power=2.0, 
    log_mag=True,
    trunc=2001
    )
    logger.info("MelSpectrogram initialized as melspec_preprocessor.")

    yield

    logger.info("BAPE app shutting down…")
    # AT SHUTDOWN: Clean up the ML models and release the resources
    app.state.t60_processor = None
    logger.info("CLEANUP: T60 processor set to None.")
    # AT SHUTDOWN: Clean up the ML models and release the resources
    app.state.t60_processor = None
    logger.info("CLEANUP: C50 processor set to None.")
    app.state.melspec_preprocessor = None
    logger.info("CLEANUP: melspec_preprocessor set to None.")
    
app = FastAPI(lifespan=lifespan)


#API ENDPOINTS
#HEALTHCHECK ENDPOINT
@app.get("/health")
def health_check(request: Request):
    """Healthcheck endpoint."""
    t60_processor = request.app.state.t60_processor
    c50_processor = request.app.state.c50_processor
    return {
        "status": "ok",
        "t60_model_loaded": t60_processor is not None,
        "c50_model_loaded": c50_processor is not None
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
    
    # retrieve processor instances from asynccontextmanager / app.state
    t60_processor = websocket.app.state.t60_processor
    c50_processor = websocket.app.state.c50_processor
    melspec_preprocessor = websocket.app.state.melspec_preprocessor

    # initialize rolling audio buffer
    audio_buffer = np.array([], dtype=np.float32)

    # initialize spectrogram_buffer
    accumulated_spec = []

    try:
        while True:
            # receive binary data from frontend websocket endpoint
            raw_bytes = await websocket.receive_bytes()

            # convert bytes to float32 np array
            converted_data = np.frombuffer(raw_bytes, dtype=np.float32)
            
            # concatenate converted_data (spliced in index.html's startRecording function) to rolling audio_buffer
            audio_buffer = np.concatenate((audio_buffer, converted_data))
            
            # append 
            #check if buffer has enough data for 4 seconds (required by onnx model)
            if len(audio_buffer) >= 64000:
                
                # Initialize inference loop
                session_id = str(uuid.uuid4())
                logger.info("%s samples available.", len(audio_buffer))
                logger.info("session_id: %s", session_id)
                
                spectrogram_chunk = melspec_preprocessor(audio_buffer) # shape [16, 2000]

                # calculate mean and standard
                mean = spectrogram_chunk.mean()
                std = spectrogram_chunk.std()
                # standardize spectrogram tensor
                standardized_spectrogram = (spectrogram_chunk - mean) / (std + 1e-12)  

                # create spectrogram slice; leave first dimension at index 0 as is (16); slice second dimension to only last 100 frames (100 frames * 32 (hop size) = 3200 samples or 200ms);transform to list as I will send it via JSON which doesn'tz support numpy arrays                    
                
                spectrogram_latest100frames = standardized_spectrogram[:,-100:]
                accumulated_spec.append(spectrogram_latest100frames)
                
                spectrogram_latest100frames = spectrogram_latest100frames.tolist()

                # reshape to 4D nparray, add dimensions at 0 and 1 -> shape [1,1,16,2000]
                onnx_input_spectrogram = np.expand_dims(standardized_spectrogram, axis=(0,1))

                # INITIALIZE CONCURRENT INFERENCE THREADS
                t60_inference = asyncio.to_thread(t60_processor.run_inference, onnx_input_spectrogram)
                c50_inference = asyncio.to_thread(c50_processor.run_inference, onnx_input_spectrogram)

                # RUN AND TIME CONCURRENT INFERENCE THREADS
                start_time = time.perf_counter() # performance measure; can be commented out in prod
                t60_results, c50_results = await asyncio.gather(t60_inference, c50_inference)
                inference_time_ms = round((time.perf_counter() - start_time)*1000, 2) # performance measure; can be commented out in prod

                # onnx model returns a list of 3 np arrays, which need to be converted to standard python lists so we can send them as a JSON
                response_json = {
                    "t60_bapes": {
                        "latents": t60_results["latents"].tolist(),
                        "params": t60_results["params"].tolist(),
                        "quantiles": t60_results["quantiles"].tolist()
                    },
                    "c50_bapes": {
                        "latents": c50_results["latents"].tolist(),
                        "params": c50_results["params"].tolist(),
                        "quantiles": c50_results["quantiles"].tolist()
                    },
                    "spectrogram_latest100frames": spectrogram_latest100frames,
                    "inference_time_ms": inference_time_ms
                }
                
                # Log session data
                log_data = {
                    "event": "inference_complete",
                    "session_id": session_id,
                    "inference_time_ms": inference_time_ms,
                    "shape": onnx_input_spectrogram.shape,
                    "t60_estimate_1khz_sample": t60_results["params"].tolist()[0][0],
                    "c50_estimate_1khz_sample": c50_results["params"].tolist()[0][0]
                }

                logger.info(json.dumps(log_data))

                # send results to client
                await websocket.send_json(response_json)

                # slice buffer by 3200 samples (0.2 seconds), remaining 3.8 seconds will be concatenated with new input when available) // decreased stride vs phase 6
                audio_buffer = audio_buffer[-60800:]
    
    except WebSocketDisconnect:
        logger.info("Client disconnected cleanly.")

    except Exception as e:
        logger.exception("Error in Websocket connection: %s", e)

    finally:
        if len(accumulated_spec) > 0:
            spec_hot = np.concatenate(accumulated_spec, axis=1) #stack on second dimension; shape is (nmels, time) or (16,100)
            np.save(BASE_DIR / "models" / "spec_hot.npy", spec_hot)

@app.get("/api/get-upload-url")
# create presigned URLs
def create_presigned_upload_url(
    expiration=300
):
    """Generate a presigned URL to share an S3 object

    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: JSON response containing upload URL as string and upload file name. If error, returns None.
    """
    
    BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    REGION_NAME = os.environ.get("AWS_REGION")
    session_id = str(uuid.uuid4())

    s3_client=boto3.client(
        's3',
        region_name=REGION_NAME,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'},
            )
        )
    
    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket":BUCKET_NAME,
                "Key":f"uploads/{session_id}.wav"
            },
            ExpiresIn=expiration
        )

        presigned_url_response_json = {
            "upload_url": upload_url,
            "object_key": f"uploads/{session_id}.wav",
        }

    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return presigned_url_response_json

# Mount the static directory containing index.html and processor.js
app.mount("/", StaticFiles(directory= BASE_DIR.parent / "src", html=True), name="static")

# LAUNCH ON LOCALHOST
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# LAUNCH ON AWS - defined port 8080 in ecs.tf
#if __name__ == "__main__":
#    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
