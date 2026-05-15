import sys
import os

import uuid
import subprocess
import logging
import io
import pathlib

import numpy as np
import librosa
import torch
from torch import Tensor
from librosa.feature import melspectrogram

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TARGET_SR = 16000 # target sample rate – placeholder value but a common one

# before, we did audio normalization at this point but this is now handled via the Web Audio API
# also, we used generate_spectrogram_image() at this point to create the spectrogram PNG, we will add this later as a distributed microservice to prevent increasing latency

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