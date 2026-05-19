from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import FileResponse
import uvicorn
import logging
from pathlib import Path
import numpy as np
from contextlib import asynccontextmanager

# Identify Base Directory
BASE_DIR = Path(__file__).resolve().parent

from .inference_engine import AcousticModelProcessor
from .audio_utils import MelSpectrogram

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
                logger.info("4 second window available. Ready to run inference.")
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
                logger.info("Running inference on shape: %s", standardized_spectrogram_4d.shape)
                results = processor.run_inference(standardized_spectrogram_4d)


                # onnx model returns a list of 3 np arrays, which need to be converted to standard python lists so we can send them as a JSON
                response_payload = {
                    "latents": results["latents"].tolist(),
                    "params": results["params"].tolist(),
                    "quantiles": results["quantiles"].tolist()
                }

                # Print the shape to confirm, and just the first 3 parameter estimates 
                logger.info("Inference results for last 4 seconds received.")
                logger.info("First three T60 Params: %s", response_payload['params'][0][0][:3])

                # send results
                await websocket.send_json(response_payload)

                # slice buffer to keep the latter half of the window (2 seconds; which will be concatenated with new input if available)
                audio_buffer = audio_buffer[-32000:]

    except Exception as e:
        logger.exception("Error in Websocket: %s", e)

# LAUNCH ON LOCALHOST
# if __name__ == "__main__":
#    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

# LAUNCH ON AWS - defined port 8080 in ecs.tf
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
