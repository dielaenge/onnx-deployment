import os
import sys
import librosa
from src.audio_processor import MelSpectrogram
from src.model_processor import AcousticModelProcessor
import numpy as np
import logging
import json

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger("API")

# path variables
REF_PATH = "src/wet_speech.wav"
MODEL_PATH = "onnx/super_param_estimator-2026-03-27.onnx"

processor = None
try:
    processor = AcousticModelProcessor(MODEL_PATH)
except Exception as e:
    logger.critical("FATAL: Could not load model at startup. Server will fail on requests. Error: %s", e)
    sys.exit(1)
    
# Create an instance of the MelSpectogram class
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

# load ref audio
audio_array, _ = librosa.load(REF_PATH, sr=16000)

# create spectrogram
spectrogram_2d = melspec_preprocessor(audio_array) # returns spectogram using height of `n_mels`` and width of `trunc`

print(f"Shape of spectogram_2d after shape preprocessing step 1: {spectrogram_2d.shape}")

# standardize like in bape.src.util.signals.stdze
mean = spectrogram_2d.mean()
std = spectrogram_2d.std()
print(f"\nspectrogram_2d.mean is {mean}\nspectrogram_2d.std is {std}\n")

# Add a tiny epsilon (1e-6) to std to prevent "Division by Zero" if the audio is silent
spectrogram_2d = (spectrogram_2d - mean) / (std + 1e-6)


# Add batch size to the tensor at position 0; shape -> (1, 16, 2000)
spectrogram_3d = np.expand_dims(spectrogram_2d, axis=0)
print(f"Shape of spectogram_3d after shape preprocessing step 2: {spectrogram_3d.shape}")

# Add dimensions for channels at position 1; shape -> (1, 1, 16, 2000)
spectrogram_4d = np.expand_dims(spectrogram_3d, axis=1)
print(f"Shape of spectogram_4d after shape preprocessing step 3: {spectrogram_4d.shape}")

model_outputs = processor.generate_vector(spectrogram_4d)

estimated_params = model_outputs['estimated_params']

# turn flat results back into a NumPy array
results_array = np.array(estimated_params).reshape(7, 3)

print(f"\n{'Band':<6} | {'Lower':<8} | {'Estimate':<8} | {'Upper':<8}\n")

# 2. Loop through the 7 frequency bands
bands = ["125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz"]

for i, band_name in enumerate(bands):
    low, est, high = results_array[i]
    # :.4f rounds to 4 decimal places, just like Paul's
    print(f"{band_name:<6} | {low:>8.4f} | {est:>8.4f} | {high:>8.4f}")

print(
    json.dumps(
        {
        "model_path": MODEL_PATH,
        "onnx_input_shape": list(spectrogram_4d.shape),
        "results_shape": list(estimated_params.shape)
        },
        indent=2
    )
)