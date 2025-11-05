from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import time
import json
import logging

from src.model_processor import AcousticModelProcessor
from src.audio_processor import preprocess_from_bytes, TARGET_SR

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

app = FastAPI(title="Acoustic Vector Generator API")

# --- Model init (happens once at server startup) ---
MODEL_PATH = "dummy_acoustic_model.onnx"
processor = None
try:
    processor = AcousticModelProcessor(MODEL_PATH)
except Exception as e:
    logger.critical("FATAL: Could not load model at startup. Server will fail on requests. Error: %s", e)
    # note: No exit here as we just set processor = None

@app.get("/health")
def health_check():
    """Healthcheck endpoint."""
    return {
        "status": "ok",
        "model_loaded": processor is not None
        }

@app.post("/acou-vec-v0-1/generate")
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
        preprocessed_audio = preprocess_from_bytes(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", preprocessed_audio.shape)

    # 4.
    start_time = time.perf_counter()
    vector = processor.generate_vector(preprocessed_audio)
    end_time = time.perf_counter()

    processing_time_ms = (end_time - start_time) * 1000

    logger.info("Inference complete for %s. Time: %s.3f ms", audio_file.filename, processing_time_ms)

    return {
        "filename" : audio_file.filename,
        "input_samples" : preprocessed_audio.shape[1],
        "vector_shape" : list(vector.shape), #why list?
        "acoustic_vector": vector.flatten().tolist(), #convert NumPy array to list for JSON // why flatten?
        "preprocessing_time_ms": processing_time_ms
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    