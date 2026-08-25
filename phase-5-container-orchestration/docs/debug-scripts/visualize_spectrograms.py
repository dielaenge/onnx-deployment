import torch
import numpy as np
import matplotlib.pyplot as plt
import librosa
from src.audio_processor import MelSpectrogram 
# 1. Load reference spectrogram
ref_spectrogram = torch.load("src/input_spec.pt", map_location="cpu")
if ref_spectrogram.shape[1] == 2001: ref_spectrogram = ref_spectrogram[:, :2000]

# 2. Generate Spectrogram like before inference debugging (not standardized)

preprocessor = MelSpectrogram(
  sr= 16000,
  n_fft= 64,
  hop_size= 32,
  n_mels= 16,
  fmin= 20,
  fmax= 8000,
  power= 2.0,
  log_mag= True,
  trunc= 2000
)

audio, _ = librosa.load("src/wet_speech.wav", sr=16000)
nonstd_spectrogram = preprocessor(audio)
if nonstd_spectrogram.shape[1] == 2001: nonstd_spectrogram = nonstd_spectrogram[:, :2000]

# 3. Standardize data (fix)
mean, std = nonstd_spectrogram.mean(), nonstd_spectrogram.std()
std_spectrogram = (nonstd_spectrogram - mean) / (std + 1e-6)

# 4. PLOT
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Spectrogram before Standarization
im0 = axes[0].imshow(nonstd_spectrogram, aspect='auto', origin='lower')
axes[0].set_title(f"1. Spectrogram before Standarization (Max: {nonstd_spectrogram.max():.2f}, Mean: {nonstd_spectrogram.mean():.2f})")
fig.colorbar(im0, ax=axes[0])

# Reference Spectrogram
im1 = axes[1].imshow(ref_spectrogram, aspect='auto', origin='lower')
axes[1].set_title(f"2. Reference Spectrogram (Max: {ref_spectrogram.max():.2f}, Mean: {ref_spectrogram.mean():.2f})")
fig.colorbar(im1, ax=axes[1])

# Spectrogram after Standardization
im2 = axes[2].imshow(std_spectrogram, aspect='auto', origin='lower')
axes[2].set_title(f"3. Spectrogram after Standardization (Max: {std_spectrogram.max():.2f}, Mean: {std_spectrogram.mean():.2f})")
fig.colorbar(im2, ax=axes[2])

plt.tight_layout()
plt.savefig("spectrogram_comparison.png")
print("Visualization created. Check spectrogram_comparison.png .")