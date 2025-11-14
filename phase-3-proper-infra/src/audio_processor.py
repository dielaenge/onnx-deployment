import numpy as np
import librosa
import io
import torch
from torch import Tensor
from librosa.feature import melspectrogram


TARGET_SR = 16000 # target sample rate – placeholder value but a common one

# --- Preprocessing class `MelSpectrogram` copied from [BAPE repository: bape/src/util/signals.py](https://github.com/philipp-goetz/bape/blob/7988f939d1c69301e31d322fecbbaa2a031ef3e1/src/util/signals.py) and adapted (see comments) for deployment---

class MelSpectrogram:
    """Spectogram with a mel frequency scale"""
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
        # self.freqs = mel_frequencies(n_mels=n_mels, fmin=fmin, fmax=fmax) #not used in the __call_ function
    
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

def transform_audio_to_spectogram(audio_bytes): #audio_bytes describe a path
    """Loads raw audio bytes and converts them to a 4D spectogram tensor the ONNX model expects."""
    audio_buffer = io.BytesIO(audio_bytes)
    audio_data, _ = librosa.load(audio_buffer, sr=TARGET_SR, mono=True, dtype=np.float32) #librosa.load returns an np.ndarray / audio time series, here audio_data, and a sample rate `_`, ensure datatype is float32
    
    #audio_data has to be adjusted for onnx runtime from (N,) to (1, 1, 16, 2000), this happens in 3 steps
    
    # Step 1. Create 2D Mel Spectogram; shape -> (16, 2000)
    spectogram_2d = melspec_preprocessor(audio_data) # returns spectogram using height of `n_mels`` and width of `trunc`
    print(f"Shape of spectogram_2d after shape preprocessing step 1: {spectogram_2d.shape}")

    # Step 2. Add batch size to the tensor at position 0; shape -> (1, 16, 2000)
    spectogram_3d = np.expand_dims(spectogram_2d, axis=0)
    print(f"Shape of spectogram_3d after shape preprocessing step 2: {spectogram_3d.shape}")
    
    # Step 3. Add dimensions for channels at position 1; shape -> (1, 1, 16, 2000)
    spectogram_4d = np.expand_dims(spectogram_3d, axis=1)
    print(f"Shape of spectogram_4d after shape preprocessing step 3: {spectogram_4d.shape}")
    
    # Return the final tensor
    # print(f"Data type is:{spectogram_4d.dtype}")
    return spectogram_4d
    