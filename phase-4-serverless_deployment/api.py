import os
import boto3
from botocore.exceptions import ClientError
# Check environment variables of Lambda function
#print(f"Debug: NUMBA_CACHE_DIR is {os.environ.get('NUMBA_CACHE_DIR')}")
#print(f"Debug: JOBLIB_TEMP_FOLDER is {os.environ.get('JOBLIB_TEMP_FOLDER')}")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import time
import json
import logging
import uuid

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
    
# HEALTHCHECK ENDPOINT

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# --- Model init (happens once at server startup) ---
# choose export version of model.pth
MODEL_PATH = "onnx/super_param_estimator_opset18_2025-11-18_17-40-57.onnx"
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
        audio_spec, clean_wav, spectrogram_png, input_duration = transform_audio_to_spectrogram(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", audio_spec.shape)
    
    # intialize a preprocessing session variable for naming files
    session_id=str(uuid.uuid4())
    wav_key=f"results/{session_id}_input.wav"
    png_key=f"results/{session_id}_spectrogram.png"

    try:
        audio_spec, normalized_wav, spectrogram_png, input_duration = transform_audio_to_spectrogram(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", audio_spec.shape)

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

    print(f"Spectrogram available via {png_url}. Normalized wav input available via {wav_url}. These links will time out after 1 minute. The objects will be deleted in 24 hours.")
    
    # 5. Run inference and get results
    start_time = time.perf_counter()
    model_outputs = processor.generate_vector(audio_spec)
    end_time = time.perf_counter()

    processing_time_ms = (end_time - start_time) * 1000
    
    logger.info("Inference complete for %s. Time: %s.3f ms", audio_file.filename, processing_time_ms)

    # 6. API respone (improved with BAPE integration)
    #latent_vector = model_outputs['latent_vector']
    estimated_params = model_outputs['estimated_params']
    quantiles  = model_outputs['quantiles']

    return {
        "request_metadata": {        
            "filename": audio_file.filename,
            "input duration": f"{input_duration} seconds",
            "processing_time_ms": round(processing_time_ms, 3)
        },

        "preprocessed_inputs": {
          "png_url": png_url,
          "wav_url": wav_url
        },

        "inference_results": {
            
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
    