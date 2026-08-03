from typing import Union, Optional
from collections import deque
import numpy as np
import torch
from torch import Tensor
from torchaudio.transforms import Spectrogram, MelSpectrogram
from scipy.signal import oaconvolve
from soundfile import read, write

from librosa import resample, mel_frequencies
from librosa.feature import melspectrogram

from src.BAPE_src.files import get_file_list
import matplotlib.pyplot as plt


def load_audio(
    filepath: str,
    fs: float = 16000.0,
    single_channel: bool = True,
) -> tuple:
    """Function to reading and resampling audio"""
    data, sr_file = read(filepath, always_2d=True)

    if data.ndim > 1 and single_channel:
        data = data[:, :1]

    if sr_file != fs:
        out_data = []
        for chan in data.T:
            out_data.append(resample(chan, orig_sr=sr_file, target_sr=fs))
        data = np.vstack(out_data).T
    return data, fs


def write_audio(
    filepath: str,
    sig: np.ndarray,
    in_sr: int,
    out_sr: int,
) -> None:
    if in_sr != out_sr:
        sig = resample(sig, in_sr, out_sr)
    write(filepath, sig, out_sr, "PCM_24")


def reverberate(
    x: np.ndarray,
    h: np.ndarray,
    out_len: Optional[int] = None,
) -> np.ndarray:
    """Convolution in frequency domain"""
    result = oaconvolve(h, x, mode="full")
    if out_len is not None:
        result = result[:out_len]
    return result


def get_onset(rir: np.ndarray, thresh: float = 0.1) -> int:
    # get first index of exceeding a fraction of the peak
    return np.where(np.abs(rir) > np.max(np.abs(rir)) * thresh)[0][0]


def remove_pre_delay(
    rir: np.ndarray, guard: int = 8, thresh: float = 0.1
) -> np.ndarray:
    """Remove initial delay of direct sound"""
    assert guard >= 0
    if rir.ndim == 1:
        idx = get_onset(rir)
        rir = rir[max(idx - guard, 0) :] * np.sign(rir[idx])
    else:
        # rir dims: [channel, time]
        idx = max(min([get_onset(ch, thresh) - guard for ch in rir]), 0)
        rir = rir[:, max(idx - guard, 0) :]
    return rir


def fix_length(rir: np.ndarray, trunc_len: int) -> np.ndarray:
    """Force RIR to a specified length, trunc/pad"""
    if rir.ndim == 1:
        rir_len = rir.shape[0]
        if rir_len < trunc_len:
            rir = np.concatenate((rir, np.zeros(trunc_len - rir_len)))
        else:
            rir = rir[:trunc_len]
    else:
        num_chan, rir_len = rir.shape
        if rir_len < trunc_len:
            rir = np.hstack((rir, np.zeros((num_chan, trunc_len - rir_len))))
        else:
            rir = rir[..., :trunc_len]
    return rir


def stdze(in_array: np.ndarray) -> np.ndarray:
    # standardize data
    return (in_array - np.mean(in_array)) / np.std(in_array)


def mag2db(mag: float) -> float:
    return 20 * np.log10(np.abs(mag))


def db2mag(db: float) -> float:
    return np.power(10, db * 0.05)


def cplx2split(in_array: Tensor) -> Tensor:
    """Separates real and imag parts"""
    return torch.stack([torch.real(in_array), torch.imag(in_array)])


def split2cplx(in_array: Tensor, dim: int = 0) -> Tensor:
    """Create complex tensor, assume real/imag along 0 dim"""
    real, imag = torch.chunk(in_array, chunks=2, dim=dim)
    return real + 1j * imag


def rir_from_tf(tf: Tensor) -> Tensor:
    # get rir from packed tf
    tf = tf[0] + 1j * tf[1]
    tf = torch.cat((tf, torch.imag(tf[0]).reshape(1)))
    tf[0] = torch.real(tf[0].clone())
    tf = torch.cat((tf, torch.conj(torch.flip(tf[1:-1], dims=(0,)))))
    return torch.real(torch.fft.ifft(tf))


def energy_vad(x, frame_len=400, hop=160, thresh_db=-24.0, eps=1e-12):
    """
    Very simple VAD: framewise energy gate relative to the 95th percentile.
    Returns a sample-accurate mask (0/1).
    """
    # frame signal
    n = len(x)
    num_frames = 1 + (n - frame_len) // hop if n >= frame_len else 1
    idx = np.arange(frame_len)[None, :] + hop * np.arange(num_frames)[:, None]
    idx = np.clip(idx, 0, n - 1)
    frames = x[idx] * np.hanning(frame_len)[None, :]
    frame_energy = np.mean(frames**2, axis=1) + eps

    ref = np.percentile(frame_energy, 95) + eps
    gate = frame_energy >= ref * (10.0 ** (thresh_db / 10.0))  # thresh_db below ref
    # upsample gate to samples
    m = np.zeros(n, dtype=bool)
    for i, g in enumerate(gate):
        start = i * hop
        end = min(start + frame_len, n)
        m[start:end] |= g

    # plt.plot(x)
    # plt.plot(m.astype(float) * np.max(np.abs(x)))
    # plt.savefig("plots/dummy_vad.png")
    # plt.close()

    return m.astype(np.float32)


def add_awgn_with_vad(signal: np.ndarray, snr_db: float = 24, vad_mask=None, seed=None):
    """
    x: 1D numpy array (float32/float64), assumed clean speech (SNR=∞).
    snr_db: desired SNR computed over VAD=1 samples.
    vad_mask: optional {0,1} mask same length as x. If None, uses energy VAD.
    seed: optional int for reproducibility.
    """
    rng = np.random.default_rng(seed)

    n = len(signal)
    if vad_mask is None:
        vad_mask = energy_vad(signal)
    else:
        vad_mask = (vad_mask.astype(bool)).astype(np.float64)
        if len(vad_mask) != n:
            raise ValueError("vad_mask must have same length as x")

    if vad_mask.sum() == 0:
        raise ValueError("VAD mask has no active samples")

    # signal power over voiced-only samples
    P_sig = (np.sum(vad_mask * (signal**2))) / vad_mask.sum()

    # target noise power (over voiced-only samples)
    P_noise = P_sig / (10.0 ** (snr_db / 10.0))

    v = rng.standard_normal(n)

    P_v = (np.sum(vad_mask * (v**2))) / vad_mask.sum()

    alpha = np.sqrt(P_noise / (P_v + 1e-12))

    noisy = signal + alpha * v

    # plt.plot(noisy)
    # plt.plot(signal)
    # plt.savefig("plots/dummy_noisy.png")
    # plt.close()

    return noisy


class STFTSpectrogram:
    """Wrapper for STFT-based TF features"""

    def __init__(
        self,
        sr: float,
        n_fft: int,
        hop_size: int,
        mode: str = "complex",
        c: Optional[float] = 0.3,
        trunc: int | None = None,
    ) -> None:
        self.sr = sr
        self.n_fft = n_fft
        self.hop_size = hop_size
        self.c = c
        self.mode = mode
        self.trunc = trunc

        self.spec = Spectrogram(
            n_fft=n_fft,
            hop_length=hop_size,
            power=None,
        )

    def __call__(self, input_signal: np.ndarray) -> np.ndarray:
        spec = self.spec(input_signal)

        if self.mode == "log-mag":
            spec = 20 * torch.log10(torch.abs(spec))

        if self.mode == "mag-c":
            spec = spec.abs().pow(self.c)

        if self.mode == "mag-real-imag":
            spec = torch.cat(
                (
                    spec.abs().pow(self.c),
                    torch.real(spec),
                    torch.imag(spec),
                )
            )

        if self.trunc:
            spec = spec[..., : self.trunc]

        return spec


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
        c_mag: Optional[float] = None,
        trunc: int | None = None,
    ) -> None:
        self.sr = sr
        self.n_fft = n_fft
        self.hop_size = hop_size
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax
        self.power = power
        self.log_mag = log_mag
        self.trunc = trunc

        self.freqs = mel_frequencies(n_mels=n_mels, fmin=fmin, fmax=fmax)

    def __call__(self, input_signal: Union[np.ndarray, Tensor]) -> Tensor:

        if isinstance(input_signal, Tensor):
            input_signal = input_signal.numpy()

        spec = melspectrogram(
            y=input_signal,
            sr=self.sr,
            n_fft=self.n_fft,
            hop_length=self.hop_size,
            n_mels=self.n_mels,
            fmin=self.fmin,
            fmax=self.fmax,
            power=1.0,
        )

        # cast here to Tensor
        spec = Tensor(spec)

        # # normalize, log-power
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


class AudioStream:
    """Successively read audio segments.

    Produces fixed-size segments, optionally drops silent segments, and shuffles
    file order per epoch. Keeps a small queue of ready-made segments to avoid
    repeated reallocations.

    next_segment() returns (segment, epoch_wrapped):
      - segment: np.ndarray, shape (num_samples,), dtype float32
      - epoch_wrapped: True iff at least one full pass over file_list occurred during this fetch
    """

    def __init__(
        self,
        path: str = "",
        sr: float = 48000.0,
        duration: float = 4.0,
        file_list: Optional[list[str]] = None,
        normalize: bool = True,
        drop_silent: bool = True,
        silence_metric: str = "rms",  # "rms" (dBFS) or "peak"
        silence_thresh: float = -35.0,  # dBFS if "rms"; absolute threshold if "peak"
        shuffle: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        self.sr = float(sr)
        self.duration = float(duration)
        self.num_samples = int(round(self.duration * self.sr))

        if self.num_samples <= 0:
            raise ValueError("duration*sr must be > 0")

        if file_list is None:
            files = get_file_list(path=path)
        else:
            files = list(file_list)

        if not files:
            raise ValueError(
                "AudioStream requires a non-empty file_list or path with audio files"
            )

        self.file_list = files
        self.normalize = bool(normalize)
        self.drop_silent = bool(drop_silent)
        self.silence_metric = silence_metric
        self.silence_thresh = float(silence_thresh)
        self.shuffle = bool(shuffle)
        self.seed = seed

        self._rng = np.random.default_rng(seed)
        if self.shuffle:
            self._rng.shuffle(self.file_list)

        self._queue: deque[np.ndarray] = deque()
        self._rem = np.empty(0, dtype=np.float32)
        self._index = 0
        self._epoch = 0

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        if not self.normalize:
            return x
        m = np.max(np.abs(x))
        if m > 0:
            return (x / m).astype(np.float32, copy=False)
        return x.astype(np.float32, copy=False)

    def _is_loud(self, seg: np.ndarray) -> bool:
        if not self.drop_silent:
            return True
        if self.silence_metric == "rms":
            rms = np.sqrt(np.mean(seg.astype(np.float64) ** 2) + 1e-12)
            dbfs = 20.0 * np.log10(rms + 1e-12)
            return dbfs >= self.silence_thresh
        # peak metric
        return np.max(np.abs(seg)) >= self.silence_thresh

    def _advance_index(self) -> bool:
        """Advance file index; return True if we wrapped an epoch."""
        self._index += 1
        if self._index >= len(self.file_list):
            self._index = 0
            self._epoch += 1
            if self.shuffle:
                self._rng.shuffle(self.file_list)
            return True
        return False

    def _fill_queue(self) -> bool:
        """Fill the segment queue until it holds at least one segment.
        Returns True if at least one epoch wrap occurred during filling.
        """
        wrapped = False
        safety_loops = 0
        while not self._queue:
            # Safety: avoid infinite loops if everything is silent/short
            safety_loops += 1
            if (
                safety_loops > len(self.file_list) + 1
                and self._rem.size < self.num_samples
            ):
                # Fallback: emit zeros to make progress
                self._queue.append(np.zeros(self.num_samples, dtype=np.float32))
                break

            # Load next file and normalize
            x = load_audio(self.file_list[self._index], fs=self.sr)[0]
            x = x.astype(np.float32, copy=False)
            x = self._normalize(x)

            # Prepend remainder from previous file
            if self._rem.size:
                x = np.concatenate((self._rem, x), axis=0)

            if x.size >= self.num_samples:
                num_frames = x.size // self.num_samples
                framed = x[: num_frames * self.num_samples].reshape(
                    num_frames, self.num_samples
                )
                # push only segments passing the loudness gate
                for seg in framed:
                    if self._is_loud(seg):
                        # copy to ensure segment memory is independent
                        self._queue.append(seg.astype(np.float32, copy=True))
                # keep leftover for next round
                self._rem = x[num_frames * self.num_samples :]
            else:
                # Not enough samples yet, keep as remainder
                self._rem = x

            # move to next file and track wrap
            wrapped = self._advance_index() or wrapped

        return wrapped

    def next_segment(self) -> tuple[np.ndarray, bool]:
        """Retrieve one segment of length 'num_samples'.

        Returns:
            segment: np.ndarray, shape (num_samples,), float32
            epoch_wrapped: bool, True if at least one full pass over files occurred while preparing this segment
        """
        wrapped = self._fill_queue()
        seg = self._queue.popleft()
        return seg, wrapped

    def segments(self):
        """Infinite generator yielding (segment, epoch_wrapped)."""
        while True:
            yield self.next_segment()

    def reset(
        self, file_list: Optional[list[str]] = None, shuffle: Optional[bool] = None
    ) -> None:
        """Reset internal state; optionally replace files and shuffle setting."""
        if file_list is not None:
            if not file_list:
                raise ValueError("file_list must be non-empty")
            self.file_list = list(file_list)
        if shuffle is not None:
            self.shuffle = bool(shuffle)
        if self.shuffle:
            self._rng.shuffle(self.file_list)
        self._queue.clear()
        self._rem = np.empty(0, dtype=np.float32)
        self._index = 0
        self._epoch = 0
