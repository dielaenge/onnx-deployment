from pathlib import Path
import pickle
import torch
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.util.rir_params import generate_fractional_octaves


def main():

    with open("logs/param/2025-08-13_09-33-49/outputs/output.pkl", "rb") as f:
        outputs = pickle.load(f)

    f = generate_fractional_octaves(f_min=62.5, f_max=8000, fraction=3)
    f = np.concatenate((f[:12], f[13:]))

    est = torch.cat([out["est"] for out in outputs], dim=0)
    gt = torch.cat([out["gt"] for out in outputs], dim=0)

    maes = (gt - est).abs().mean(dim=1)

    # Create 1x4 subplot: 1 histogram + 3 random sample plots
    fig, axes = plt.subplots(1, 4, figsize=(16, 3))

    # Histogram of MAEs
    axes[0].hist(maes.numpy(), bins=30, color="skyblue", edgecolor="black")
    axes[0].set_xlabel("MAE [dB]")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Error distribution (freq.-av.)")
    axes[0].grid()
    axes[0].set_xlim(0, 7)

    # Plot samples for lower quartile, median, and upper quartile of MAEs
    percentiles = [25, 50, 75]
    values = np.percentile(maes.numpy(), percentiles)
    indices = [np.argmin(np.abs(maes.numpy() - v)) for v in values]
    titles = ["Lower Quartile", "Median", "Upper Quartile"]
    for i, idx in enumerate(indices):
        axes[i + 1].plot(f, est[idx].cpu().numpy(), label="Estimate")
        axes[i + 1].plot(f, gt[idx].cpu().numpy(), label="Ground Truth")
        axes[i + 1].set_title(f"{titles[i]}\nMAE: {maes[idx].item():.2f} dB")
        axes[i + 1].set_xlabel("Frequency [Hz]")
        axes[i + 1].legend()
        axes[i + 1].set_xscale("log")
        axes[i + 1].grid()
        axes[i + 1].set_xlim(np.min(f), np.max(f))
        axes[i + 1].set_ylabel("Magnitude [dB]")

    plt.tight_layout()
    plt.savefig("plots/mae_histogram_and_samples_8s_ft.png", dpi=256)
    plt.close()


if __name__ == "__main__":

    main()
