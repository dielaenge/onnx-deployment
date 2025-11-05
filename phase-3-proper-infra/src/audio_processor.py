import numpy as np
import librosa
import soundfile as sf
import io

TARGET_SR = 16000 # target sample rate – placeholder value but a common one

# --- Prepare data for model input ---

def _apply_preprocessing(audio_data: np.ndarray, sr_native: int) -> np.ndarray: # leading underscore for def indicates function is intended for internal use within a module and should not be considered part of the public API
    """
    Core function to preprocess audio: resample, ensure mono, ensure datatype and adjust shape for ONNX model.
    Assuming audio_data is loadaed (either from disk or memory buffer).
    """
    # 1. Resample if necessary
    if sr_native != TARGET_SR:
        audio_data = librosa.resample(audio_data, orig_sr=sr_native, target_sr=TARGET_SR)

    # 2. Ensure Mono
    if audio_data.ndim == 2:
        audio_data = audio_data.mean(axis=1)
    
    # 3. Ensure dtype = float32
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    # 4. Adjust shape
    audio_data_batched = np.expand_dims(audio_data, axis=0)

    return audio_data_batched

# --- Function for CLI/Disk Input ---
def preprocess_from_path(audio_path: str) -> np.ndarray:
    """Loads audio from local disk and preprocesses it for model input."""
    # use librosa for local audio file handling, resampling and ensuring mono
    audio_data, current_sr = librosa.load(
        audio_path, 
        sr=TARGET_SR, 
        mono=True
    )

    # 3. Ensure dtype = float 32 // librosa handled step 1 and 2 already
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    # 4. Adjust shape for ONNX model input; from (N,) to (1,N)
    audio_data_batched =np.expand_dims(audio_data, axis=0)

    return audio_data_batched

# --- Function for API/Byte Input ---
def preprocess_from_bytes(audio_bytes: bytes) -> np.ndarray:
    """Load audio from raw bytes / API upload and preprocess it."""
    # prepare the bytes for being read by soundfile via io.BytesIO
    audio_buffer = io.BytesIO(audio_bytes)
    # use librosa.load() (instead of sf.read()) for reading bytes from API (accepts many formats, like mp3, wav, flac)
    audio_data, _ = librosa.load(audio_buffer, sr=TARGET_SR, mono=True) #instead of using sf.read, we use librosa.load() which won't crash with different file types but requires FFmpeg

    # ensure datatype
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    #adjust shape for onnx runtime from (N,) to (1,N)
    audio_data_batched = np.expand_dims(audio_data, axis=0)

    return audio_data_batched