import os
import boto3
from botocore.exceptions import ClientError

from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import time
import json
import logging
import uuid
from pathlib import Path

# Identify Base Directory
BASE_DIR = Path(__file__).resolve().parent

from .inference_engine import AcousticModelProcessor
from .audio_utils import preprocess_audio



# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

app = FastAPI(title="BAPE API")

# S3 BRIDGE
def upload_artifact_and_get_presigned_url(file_bytes: bytes, object_key: str, content_type:str):
    """
    Upload a file to an S3 bucket, if upload succeeds, return presigned URL    
    """

    # set bucket as env var
    bucket_name="bape-lambda-static-frontend"
    # initialize S3 client
    s3_client = boto3.client('s3')
    # Safe object to S3
    try:
        # 1. put_object for raw bytes
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type
        )

        # 2. Generate presigned URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            # Presigned URL expires after 5 minutes
            ExpiresIn=300,
        )
        return url

    except Exception as e:
        logger.error(f"S3 Bridge Error:{e}")
        return None
    

# --- Model init (happens once at server startup) ---
MODEL_PATH = BASE_DIR / "models" / "bape_v2_standardized.onnx"
print(f"DEBUG: Loading model from {MODEL_PATH}")

processor = None
try:
    processor = AcousticModelProcessor(MODEL_PATH)
except Exception as e:
    logger.critical("FATAL: Could not load model at startup. Server will fail on requests. Error: %s", e)
    # note: No exit here as we just set processor = None

#API ENDPOINTS

#HEALTHCHECK ENDPOINT
@app.get("/health")
def health_check():
    """Healthcheck endpoint."""
    return {
        "status": "ok",
        "model_loaded": processor is not None
        }

@app.post("/acou-vec/generate")
async def call_bape_api(audio_file: UploadFile = File(...)):
    
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
    
    # intialize a preprocessing session variable for naming files
    session_id=str(uuid.uuid4())
    wav_key=f"results/{session_id}_input.wav"
    png_key=f"results/{session_id}_spectrogram.png"

    try:
        batch_inference_input, normalized_wav, spectrogram_png, timestamps, input_duration = preprocess_audio(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", batch_inference_input.shape)

    # 4. Safe input to S3
    # 4.1. Upload normalized audio to S3 and generate presigned URL
    try:
        wav_url=upload_artifact_and_get_presigned_url(normalized_wav, wav_key, "audio/wav")
    
    except ClientError as e:
        logging.error(e)
        return None

    # 4.2. Upload to normalized audio to S3 and generate presigned URL
    try:
        png_url=upload_artifact_and_get_presigned_url(spectrogram_png, png_key, "image/png")
    
    except ClientError as e:
        logging.error(e)
        return None

    print(f"Spectrogram for entire input available via {png_url}. Normalized wav input available via {wav_url}. These links will time out after 1 minute. The objects will be deleted in 24 hours.")
    
    # 5. Run inference and get results
    start_time = time.perf_counter()
    model_outputs = processor.run_inference(batch_inference_input)
    # before sliding window input this returned one list of latent_vectors, quantiles and estimated_params; now this should return multiple of these, which we need to order
    end_time = time.perf_counter()

    processing_time_ms = (end_time - start_time) * 1000
    
    logger.info("Inference complete for %s. Time: %s.3f ms", audio_file.filename, processing_time_ms)

    # 6. API respone: Map batch results to timestamps
    batch_fingerprints = model_outputs['latent_vector'] # shape is (N,1024); was (1, 1024)
    batch_estimated_params = model_outputs['estimated_params'] # shape is (N,7,3); was (1,7,3) for estimated_params
    batch_quantiles  = model_outputs['quantiles'] # shape is (N,6,2); (1,6,2)

    # map each timestampt to a result
    timeline_of_results=[]

    for timestamp_step, param_estimation_step, quantiles_step, fingerprint_step in zip(timestamps, batch_estimated_params, batch_quantiles, batch_fingerprints):
        frame = {
            "timestamp_step": timestamp_step,
            "BAPEs": param_estimation_step.flatten().tolist(),
            "quantiles": quantiles_step.flatten().tolist(),
            "fingerprint": "processed - output tbd"
        }
        timeline_of_results.append(frame)


    return {
        "request_metadata": {        
            "filename": audio_file.filename,
            "input_duration": f"{round(input_duration,2)} seconds",
            "processing_time_ms": round(processing_time_ms, 3)
        },

        "preprocessed_inputs": {
          "png_url": png_url,
          "wav_url": wav_url
        },

        "timeline_of_results": timeline_of_results
    }

# LAUNCH
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
