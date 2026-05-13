from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.responses import FileResponse
import uvicorn
import logging
import traceback
from pathlib import Path
import numpy as np
from contextlib import asynccontextmanager
from librosa.feature import melspectrogram
import torch
from torch import Tensor

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

# --- Model init (happens once at server startup) ---
MODEL_PATH = BASE_DIR / "models" / "bape_2026-04-13_15-13-22.onnx"
processor = None
melspec_preprocessor = None

# --- Preprocessing class `MelSpectrogram` copied from [BAPE repository: bape/src/util/signals.py](https://github.com/philipp-goetz/bape/blob/7988f939d1c69301e31d322fecbbaa2a031ef3e1/src/util/signals.py) and adapted (see comments) for deployment---

class MelSpectrogram:
    """Spectrogram with a mel frequency scale"""
    def __init__(
        self, 
        sr: float = 16000.0, 
        n_fft: int = 64, 
        hop_size: int = 16,
        n_mels: int = 17, 
        fmin: float = 100.0, 
        fmax: float = 8000,
        power: float = 2.0, 
        log_mag: bool = False, 
        # c_mag: Optional[float] = None, (not used for SpeechEncoder model)
        trunc: int | None = None,
) -> None:
        self.sr, self.n_fft, self.hop_size, self.n_mels = sr, n_fft, hop_size, n_mels
        self.fmin, self.fmax, self.power, self.log_mag = fmin, fmax, power, log_mag
        self.trunc = trunc
        # self.freqs = mel_frequencies(n_mels=n_mels, fmin=fmin, fmax=fmax) #not used in the __call__ function
    
    def __call__(self, input_signal: np.ndarray) -> np.ndarray:
        """Takes 1D audio signal as input and returns the melspectrogram as tensor."""

        # From here until `return` statement code is copied from BAPE repo
        spec = melspectrogram(
            y=input_signal, sr=self.sr, n_fft=self.n_fft, hop_length=self.hop_size,
            n_mels=self.n_mels, fmin=self.fmin, fmax=self.fmax, power=1.0,
        )
        spec = Tensor(spec)
        spec /= spec.max()
        spec = spec.pow(self.power)
        if self.log_mag:
            spec = 10 * torch.log10(spec + 1e-12)
        if self.trunc is not None:
            nbins, length = spec.size()
            if length < self.trunc:
                spec = torch.cat(
                    (spec, torch.zeros((nbins, self.trunc - length))), dim=-1
                )
            else:
                spec = spec[:, : self.trunc]

        return spec

# contextlib.asynccontextmanager used witht the lifespan parameter is recommended for defining app startup and shutdown in FastAPI

# the @asynccontextmanager decorator creats an asynchronous context manager
# it expects an asynchronous function which *yield*s exactly one value
# the code before yield is run at startup, the code after at shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # AT STARTUP: initialize processor and melspec_
    global processor, melspec_preprocessor
    # initialize model and melspec preprocessor
    processor = AcousticModelProcessor(MODEL_PATH)
    melspec_preprocessor = MelSpectrogram(
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
    
    yield

    # AT SHUTDOWN: Clean up the ML models and release the resources
    processor = None
    melspec_preprocessor = None
    
app = FastAPI(lifespan=lifespan)

#API ENDPOINTS

#HEALTHCHECK ENDPOINT
@app.get("/health")
def health_check():
    """Healthcheck endpoint."""
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
    print("Client connected via WebSocket.")
    
    audio_buffer = np.array([], dtype=np.float32)
    try:
        while True:
            # receive binary data from frontend
            raw_data = await websocket.receive_bytes()

            # convert bytes to float32 np array
            converted_data = np.frombuffer(raw_data, dtype=np.float32)
            
            # add 2 second converted_data (spliced in index.html's JavaScript) to rolling buffer
            audio_buffer = np.concatenate((audio_buffer, converted_data))

            #check if buffer has enough data for 4 seconds (required by onnx model)
            if len(audio_buffer) >= 64000:
                print(f"4 second window available. Ready to run inference.")
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
                print(f"Running inference on shape: {standardized_spectrogram_4d.shape}")
                results = processor.run_inference(standardized_spectrogram_4d)


                # onnx model returns a list of 3 np arrays, which need to be converted to standard python lists so we can send them as a JSON
                response_payload = {
                    "latents": results["latents"].tolist(),
                    "params": results["params"].tolist(),
                    "quantiles": results["quantiles"].tolist()
                }

                # Print the shape to confirm, and just the first 3 parameter estimates 
                print(f"Inference complete.\nFirst three T60 Params: {response_payload['params'][0][0][:3]}")

                # send results
                await websocket.send_json(response_payload)
                
                # confirm completed inference
                await websocket.send_text("DUMMY: Inference complete for window.")

                # slice buffer to keep the latter half of the window (2 seconds; which will be concatenated with new input if available)
                audio_buffer = audio_buffer[-32000:]

    except Exception as e:
        print(f"Connection closed: {e}")
        traceback.print_exc()

# LAUNCH
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
