import sys
import os

import uuid
import subprocess
import logging
import io
import pathlib

import numpy as np
import matplotlib
# explicitly set the Anti-Grain Geometry backend which is designed for headless servers
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa
import torch
from torch import Tensor
from librosa.feature import melspectrogram


TARGET_SR = 16000 # target sample rate – placeholder value but a common one

# Normalizing any input to the required wav format

def normalize_with_ffmpeg(audio_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
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
            clean_wav=f.read()
            
        return audio_array, clean_wav

    except subprocess.CalledProcessError as e:
        # Capture FFmpeg stderr (Standar Error) for debugging
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


# deactivated the old slicing mechanism; now slicing spectrogram instead of raw audio_array
# def slice_audio_to_chunks(audio_array: np.ndarray, sr=16000):
#     window_size = 4 * sr
#     stride_size = 2 * sr

#     slices = []
#     timestamps = []

#     for i in range(0, len(audio_array), stride_size):
#         # define slice size
#         start = i
#         end = i + window_size
#         chunk = audio_array[start:end]

#         # pad end of chunk if slice is smaller than 4 seconds
#         if len(chunk) < window_size:
#             padding_needed = window_size - len(chunk)
#             chunk = np.pad(chunk, (0, padding_needed), mode="constant")

#         # add chunk to list of slices
#         slices.append(chunk)

#         # add timestamps in seconds (i / sample rate)
#         timestamps.append(i / sr)

#         # prevent producing empty windows by breaking when the audio_array is exceeded
#         if end >= len(audio_array):
#             break
        
#   return slices, timestamps

# generating the spectrogram image 
def generate_spectrogram_image(spectrogram_2d: np.ndarray) -> str:
    """
    Converts the 2D Spectrogram (a numpy array) into a PNG in bytes.
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
    spectrogram_png=buf.getvalue()

    return spectrogram_png #returns png in bytes

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
    
# --- Create an instance of the MelSpectogram class ---
    
melspec_preprocessor = MelSpectrogram(
    sr=16000, 
    n_fft=64, 
    hop_size=32, 
    n_mels=16, 
    fmin=20, 
    fmax=8000, 
    power=2.0, 
    log_mag=True
    )

def slice_spectrogram(standardized_spectrogram):
    # the model expects spectrograms 2000 frames wide ( 4 seconds )
    window_frames = 2000
    # we want to create overlapping spectrograms
    # subsequent spectrograms contain latter half of predecessor
    stride_frames = 1000

    # create empty lists for slices and timestamps
    slices=[]
    timestamps_sec=[]

    # store amount of total frames; shape[1]
    total_frames = standardized_spectrogram.shape[1]

    # loop step by step through entire input range, start at 0, end at end of input, move in stride_frames / 2 second steps
    for step in range(0, total_frames, stride_frames):
        # set start and end for step
        start = step
        end = step + window_frames

        # extract 2D chunk from entire input (select all rows (1), and columns from start to end [16, 2000])
        chunk = standardized_spectrogram[:,start:end]

        # if last step is bigger than remaining input
        if chunk.shape[1] < window_frames :
            # how much input is missing for a full window?
            padding_required = window_frames - chunk.shape[1]
            # pad remaining input:
            # no vertical padding
            # only horizontal padding_required to the right
            chunk = np.pad(chunk, ((0,0), (0, padding_required)), mode="constant")
        
        # append chunk to slices
        slices.append(chunk)

        # calculate timestamp second for this step // 2000 frames = 4 secs; 1 sec = 500 frames
        timestamp_sec = step / 500
        timestamps_sec.append(timestamp_sec)

        # break when end exceeds total amount of frames
        if end > total_frames:
            break

    return slices, timestamps_sec



def preprocess_audio(audio_bytes: bytes): #in phase 3 this was a path but after adding the normalization function it expects raw audio bytes
    """Preprocesses audio and returns normalized wav, spectrogram as array and png."""

    try:
        #normalize audio
        audio_array, clean_wav = normalize_with_ffmpeg(audio_bytes, target_sr=16000)
        
        input_duration = len(audio_array)/16000

        #generate one full spectrogram (tensor)
        raw_spectrogram = melspec_preprocessor(audio_array)

        # calculate mean and standard
        mean = raw_spectrogram.mean()
        std = raw_spectrogram.std()

        # standardize raw spectrogram tensor
        standardized_spectrogram = (raw_spectrogram - mean) / (std + 1e-12)

        # generate PNG (binary) from standarized spectrogram
        std_spectrogram_png = generate_spectrogram_image(standardized_spectrogram)
        
        # slice full spectrogram; 
        slices, timestamps = slice_spectrogram(standardized_spectrogram)

        # batch slices into one 3D array (N, 16, 2000)
        batched_spectrograms_3d = np.stack(slices, axis=0)

        # add channel dimension at index 1
        batched_spectrograms_4d = np.expand_dims(batched_spectrograms_3d, axis=1)
        
        # Return 
        # - final numpy array (batched_spectrograms_4d)
        # - normalized wav (clean_wav)
        # - spectrogram for entire input (spectrogram_png)
        # - timestamps in seconds (timestamps) – necessary for correct visualization
        return batched_spectrograms_4d, clean_wav, std_spectrogram_png, timestamps, input_duration
    
    except Exception as e:
        logging.error(f"Spectrogram generation failed: {e}")
        raise e