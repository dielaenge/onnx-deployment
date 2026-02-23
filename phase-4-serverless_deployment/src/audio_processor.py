import os
import uuid
import subprocess
import logging
import base64

import numpy as np

import matplotlib
# explicitly set the Anti-Grain Geometry backend which is designed for headless servers
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import librosa
import io
import torch
from torch import Tensor
from librosa.feature import melspectrogram


TARGET_SR = 16000 # target sample rate – placeholder value but a common one

# Normalizing any input to the required wav format

def _normalize_audio_with_ffmpeg(audio_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    """
    Librosa/Soundfile cannot read compressed formats (M4A/WebM) 
    from memory streams. They need a real file on disk.

    Saves audio bytes to disk, uses FFmpeg to convert any format to 
    16kHz Mono WAV, and loads it back.
    """
    # 1. Generate unique temp filenames (prevents collisions in parallel requests)
    # /tmp is the only writable place in Lambda
    session_id = str(uuid.uuid4())
    input_path = f"/tmp/{session_id}_in"  # FFmpeg figures out the extension
    output_path = f"/tmp/{session_id}_out.wav"

    try:
        # 2. Dump raw bytes to disk
        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        # 3. The FFmpeg convertion command
        # -y: Overwrite output
        # -i: Input file
        # -ar: Audio Rate (Resample to 16000)
        # -ac: Audio Channels (Mix down to 1 Mono channel)
        # -loglevel error: Don't clutter logs unless it fails
        cmd = [
            "ffmpeg", 
            "-y", 
            "-i", input_path, 
            "-ar", str(target_sr), 
            "-ac", "1", 
            "-loglevel", "error", 
            output_path
        ]
        
        # Run subprocess. check=True raises an error if FFmpeg fails (exit code != 0)
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 4. Load the clean WAV
        # FFmpeg did the resampling, but passing sr=target_sr is a good safety check
        audio_array, _ = librosa.load(output_path, sr=TARGET_SR)

        # 5. Get the cleaned WAV for the frontend ("r"eading as "b"inary)
        with open(output_path, "rb") as f:
            clean_wav_bytes=f.read()
            #we don't want to store any data persistently, so we encode the wav to b64 so we can pass it into the JSON result
            clean_wav_b64=base64.b64encode(clean_wav_bytes).decode('utf-8')
        
        return audio_array, clean_wav_b64

    except subprocess.CalledProcessError as e:
        # Capture FFmpeg stderr (Standard Error) for debugging
        logging.error(f"FFmpeg failed: {e.stderr.decode()}")
        raise RuntimeError(f"Could not process audio file: {e.stderr.decode()}")
        
    except Exception as e:
        logging.error(f"Audio processing error: {str(e)}")
        raise e

    finally:
        # Cleanup: Look for any uploaded and normalized files and delete them
        # If we don't delete files, /tmp is filled up to its 512MB limit and Lambda crashes
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# generating the spectrogram image 

def generate_spectrogram_image(spectrogram_2d: np.ndarray) -> str:
    """
    Converts the 2D Spectrogram (a numpy array) into a Base64 encoded PNG string.
    """
    plt.figure(figsize=(10,4))

    # Render the spectrogram using matplotlib's imshow instead of librosa's display
    # imshow is lighter and doesn't require importing librosa.display
    # origin='lower' ensures low frequencies are at the bottom
    # cmap defines colormap, viridis is the default
    plt.imshow(spectrogram_2d, aspect="auto", origin="lower", cmap="viridis")
    plt.axis('off') # hide axis for cleaner look
    plt.tight_layout(pad=0) #padding layout

    #save the plot to memory buffer
    buf=io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close() #close plot to save memory

    buf.seek(0) #start stream at position 0 of buffer
    img_b64=base64.b64encode(buf.getvalue()).decode('utf-8')
    return img_b64

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
        
        # the following check is redundant as the transform_audio_to_spectogram function we define further down always passes NumPy arrays from librosa.load()
        #if isinstance(input_signal, Tensor):
        #    input_signal = input_signal.numpy()

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

        # Edited to be returned as a NumPy array for ONNX Runtime
        return spec.numpy()
    
# --- Create an instance of the MelSpectogram class ---
    
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

def transform_audio_to_spectrogram(audio_bytes: bytes): #in phase 3 this was a path but after adding the normalization function it expects raw audio bytes
    """Loads raw audio bytes, normalizes them and returns a 4D spectogram tensor the ONNX model expects."""

    try:
        #we catch the additional output clean_wav_b64, which will be the preprocessed input
        audio_array, clean_wav_b64 = _normalize_audio_with_ffmpeg(audio_bytes, target_sr=16000)

        #JUST COMMENTED OUT
        #audio_buffer = io.BytesIO(audio_array)
        #audio_data, _ = librosa.load(audio_buffer, sr=TARGET_SR, mono=True, dtype=np.float32) #librosa.load returns an np.ndarray / audio time series, here audio_data, and a sample rate `_`, ensure datatype is float32
        
        #audio_data has to be adjusted for onnx runtime from (N,) to (1, 1, 16, 2000), this happens in 3 steps
        
        # Step 1. Create 2D Mel Spectogram; shape -> (16, 2000) (height, width)
        spectrogram_2d = melspec_preprocessor(audio_array) # returns spectogram using height of `n_mels`` and width of `trunc`

        input_duration=len(audio_array) / TARGET_SR
        print(f"Input length is {input_duration} seconds.")

        print(f"Shape of spectogram_2d after shape preprocessing step 1: {spectrogram_2d.shape}")

        # generate the spectrogram as b64 encoded png 
        spectrogram_b64=generate_spectrogram_image(spectrogram_2d)
        print(f"Spectrogram rendered and written to buffer.")

        # Step 2. Add batch size to the tensor at position 0; shape -> (1, 16, 2000) (bacth size, height, width)
        spectrogram_3d = np.expand_dims(spectrogram_2d, axis=0)
        print(f"Shape of spectogram_3d after shape preprocessing step 2: {spectrogram_3d.shape}")
        
        # Step 3. Add dimensions for channels at position 1; shape -> (1, 1, 16, 2000) (batch size, channels, height, width)
        spectrogram_4d = np.expand_dims(spectrogram_3d, axis=1)
        print(f"Shape of spectogram_4d after shape preprocessing step 3: {spectrogram_4d.shape}")
        
        # Return the final tensor: Innference input as array (for model), as wav and png (for user) 
        # print(f"Data type is:{spectogram_4d.dtype}")
        return spectrogram_4d, clean_wav_b64, spectrogram_b64, input_duration
    
    except Exception as e:
        logging.error(f"Spectrogram generation failed: {e}")
        raise e
    


