from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
import time
import json
import logging
import uuid
from memory_profiler import memory_usage

from src.model_processor import AcousticModelProcessor
from src.audio_processor import transform_audio_to_spectrogram

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

app = FastAPI(title="BAPE API")

# FRONTEND
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# --- Model init (happens once at server startup) ---
# was "onnx/super_param_estimator.onnx" locally
MODEL_PATH = "super_param_estimator.onnx"
processor = None
try:
    processor = AcousticModelProcessor(MODEL_PATH)
except Exception as e:
    logger.critical("FATAL: Could not load model at startup. Server will fail on requests. Error: %s", e)
    # note: No exit here as we just set processor = None


#API ENDPOINTS
@app.get("/health")
def health_check():
    """Healthcheck endpoint."""
    return {
        "status": "ok",
        "model_loaded": processor is not None
        }

@app.post("/acou-vec/generate")
async def generate_vector_endpoint(audio_file: UploadFile = File(...)):
    
    if processor is None:
        raise HTTPException(status_code=503, detail="Service unavailable: Model not loaded.")
    
    logger.info("Received file: %s (%s)", audio_file.filename, audio_file.content_type)

    # 1. Input validation
    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        logger.warning("Upload failed: Invalid file type received: %s", audio_file.content_type)
        raise HTTPException(status_code=400, detail="Invalid file type. Must be audio.")
    
    # 2. Load audio bytes asynchronously
    contents = await audio_file.read()


    # 3. Preprocess audio input using modular function from audio_processor.py
    try:
        audio_spec = transform_audio_to_spectrogram(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", audio_spec.shape)

    # 4. Run inference and get results
    start_time = time.perf_counter()
    mem_profile, model_outputs = memory_usage((processor.generate_vector, (audio_spec,)),
    retval=True,
    interval=0.1)
    end_time = time.perf_counter()

    processing_time_ms = (end_time - start_time) * 1000
    max_mem_profile = round(max(mem_profile))
    logger.info("Inference complete for %s. Time: %s.3f ms", audio_file.filename, processing_time_ms)

    # 5. API respone (improved with BAPE integration)
    latent_vector = model_outputs['latent_vector']
    estimated_params = model_outputs['estimated_params']
    quantiles  = model_outputs['quantiles']

    return {
        "request_metadata": {
            #"request_id": str(uuid.uuid4()),
            "filename": audio_file.filename,
            "processing_time_ms": round(processing_time_ms, 3),
            "max_memory_usage_mb": max_mem_profile 
        },

        "model_metadata": {
            "model_path": MODEL_PATH,
            "onnx_input_shape": list(audio_spec.shape)
        },

        "inference_results": {

            "acoustic_fingerprint" : {
                "shape": list(latent_vector.shape),
                "values": latent_vector.flatten().tolist()[:10],
                "comment": "Only first 10 values of vector for better readability"

            },

            "estimated_parameters": {
                "shape": list(estimated_params.shape),
                "values": estimated_params.flatten().tolist()
            },

            "quantiles": {
                "shape": list(quantiles.shape),
                "values": quantiles.flatten().tolist()
            }
        }
    }

# LAUNCH
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    