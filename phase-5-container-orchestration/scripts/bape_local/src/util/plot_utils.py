from typing import Optional, List
from pathlib import Path
import pickle
import random
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from librosa.feature import melspectrogram
from librosa import mel_frequencies


def plot_specs(
    t,
    f,
    H_true,
    H_hat,
    path: Path,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    idx: int = 0,
):
    plt.style.use("dark_background")
    fg, axs = plt.subplots(2, 1, figsize=(9, 6))
    ax = axs[0]
    ph = ax.pcolor(t, f, H_true, vmin=vmin, vmax=vmax)
    ax.set_yscale("log")
    ax.set_ylim(f.min(), f.max())
    ax.set_title("Log Mel Spectrogram (Real)")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("frequency [Hz]")
    plt.colorbar(ph, ax=ax)
    ax = axs[1]
    ph = ax.pcolor(t, f, H_hat, vmin=vmin, vmax=vmax)
    ax.set_yscale("log")
    ax.set_ylim(f.min(), f.max())
    ax.set_title("Log Mel Spectrogram (FDN)")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("frequency [Hz]")
    plt.colorbar(ph, ax=ax)
    plt.tight_layout()
    if idx is not None:
        plt.savefig(f"{path}/sample_{idx:02d}.png", dpi=256)
    else:
        plt.savefig(f"{path}/sample.png", dpi=256)
    plt.close()


def speech_encoder_output(outputs: List[dict], path: Path, num: int = 1):

    for i in tqdm(range(num)):
        batch_idx = random.randint(a=0, b=len(outputs) - 1)
        sample_idx = random.randint(a=0, b=len(outputs[batch_idx]["rirspec"]) - 1)

        H_true = outputs[batch_idx]["rirspec"][sample_idx][0]
        H_hat = outputs[batch_idx]["rirspec_hat"][sample_idx][0]

        t = np.arange(H_true.shape[-1]) * 16 / 16000
        f = mel_frequencies(n_mels=16, fmin=20, fmax=8000)

        plot_specs(
            t=t,
            f=f,
            H_true=H_true,
            H_hat=H_hat,
            path=path,
            vmin=-60,
            vmax=0,
            idx=i,
        )


def vae_output(outputs: List[dict], path: Path, num: int = 1):

    for i in tqdm(range(num)):
        batch_idx = random.randint(a=0, b=len(outputs) - 1)
        sample_idx = random.randint(a=0, b=len(outputs[batch_idx]["rir"]) - 1)

        H_true = outputs[batch_idx]["spec"][sample_idx][0]
        H_hat = outputs[batch_idx]["recon"][sample_idx][0]

        try:
            mean = outputs[batch_idx]["norm"]["rirspec_mean"][sample_idx].numpy()
            std = outputs[batch_idx]["norm"]["rirspec_std"][sample_idx].numpy()
        except:
            mean = outputs[batch_idx]["norm"]["fdn_rirspec_mean"][sample_idx].numpy()
            std = outputs[batch_idx]["norm"]["fdn_rirspec_std"][sample_idx].numpy()

        H_true = H_true * std + mean
        H_hat = H_hat * std + mean

        t = np.arange(H_true.shape[-1]) * 16 / 16000
        f = mel_frequencies(n_mels=16, fmin=20, fmax=8000)

        plot_specs(
            t=t,
            f=f,
            H_true=H_true,
            H_hat=H_hat,
            path=path,
            vmin=-60,
            vmax=0,
            idx=i,
        )


def fdn_output(outputs: List[dict], path: Path, num: int = 1):

    melspec = lambda y: melspectrogram(
        y=y,
        sr=48000,
        n_fft=512,
        hop_length=16,
        n_mels=64,
        fmin=20,
        fmax=20000,
    )

    for i in tqdm(range(num)):
        batch_idx = random.randint(a=0, b=len(outputs) - 1)
        sample_idx = random.randint(a=0, b=len(outputs[batch_idx]["rir"]) - 1)
        rir = outputs[batch_idx]["rir"][sample_idx]
        rir_fdn = outputs[batch_idx]["rir_fdn"][sample_idx]

        rir = rir[:48000]
        rir_fdn = rir_fdn[:48000]

        H_true = melspec(rir)
        H_hat = melspec(rir_fdn)

        t = np.arange(H_true.shape[-1]) * 16 / 48000
        f = mel_frequencies(n_mels=64, fmin=20, fmax=20000)

        H_true /= np.max(np.abs(H_true))
        H_hat /= np.max(np.abs(H_hat))

        H_true = 20 * np.log10(np.abs(H_true) + 1e-10)
        H_hat = 20 * np.log10(np.abs(H_hat) + 1e-10)

        plot_specs(
            t=t,
            f=f,
            H_true=H_true,
            H_hat=H_hat,
            path=path,
            vmin=-60,
            vmax=0,
            idx=i,
        )
