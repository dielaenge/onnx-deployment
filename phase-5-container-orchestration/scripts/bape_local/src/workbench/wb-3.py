from pathlib import Path
import pickle
import torch
import matplotlib.pyplot as plt
import numpy as np
import umap

from hydra.utils import instantiate
from src.model.vae import VAE
from src.model.speech_encoder import SpeechEncoder

from omegaconf import OmegaConf

from src.data.datamodule import DataModule


def main():

    pth_vae = Path("logs/vae/2025-10-17_16-19-32/model.pth")
    model_cfg = OmegaConf.load(pth_vae.parent / "config.yaml")
    model_vae: VAE = instantiate(model_cfg.model)
    state_vae = torch.load(pth_vae)
    model_vae.load_state_dict(state_vae, strict=True)
    model_vae.eval()

    pth_prop = Path("logs/speech_encoder/2025-10-16_10-00-28/model.pth")
    model_cfg = OmegaConf.load(pth_prop.parent / "config.yaml")
    model_prop: SpeechEncoder = instantiate(model_cfg.model)
    state_prop = torch.load(pth_prop)
    model_prop.load_state_dict(state_prop, strict=True)
    model_prop.eval()

    pth_ctr = Path("logs/ctr/2025-10-14_19-03-16/model.pth")
    model_cfg = OmegaConf.load(pth_ctr.parent / "config.yaml")
    model_ctr: SpeechEncoder = instantiate(model_cfg.model)
    state_ctr = torch.load(pth_ctr)
    model_ctr.load_state_dict(state_ctr, strict=True)
    model_ctr.eval()

    dm_cfg = OmegaConf.load(Path("conf/data/speech.yaml"))
    dm_speech: DataModule = instantiate(dm_cfg)

    dm_cfg = OmegaConf.load(Path("conf/data/rirs.yaml"))
    dm_rirs: DataModule = instantiate(dm_cfg)

    z_vae, z_prop, z_ctr, t60, c50, t60_rir, c50_rir = [], [], [], [], [], [], []

    print("Extracting embeddings...")
    for batch in dm_rirs.test_loader:
        rir, rirspec, norm, params = batch
        z_vae.append(model_vae.encode(rirspec)[0].flatten(start_dim=1).detach())
        t60_rir.append(params["t60"])
        c50_rir.append(params["c50"])

    for batch in dm_speech.test_loader:
        dry, wet, rir, dryspec, wetspec, rirspec, norm, snr, params = batch
        z_prop.append(model_prop(wetspec)[0].detach())
        z_ctr.append(model_ctr(wetspec)[0].detach())
        t60.append(params["t60"])
        c50.append(params["c50"])

    z_vae = torch.vstack(z_vae).cpu().numpy()
    z_prop = torch.vstack(z_prop).cpu().numpy()
    z_ctr = torch.vstack(z_ctr).cpu().numpy()
    t60 = torch.vstack(t60).cpu().numpy()
    c50 = torch.vstack(c50).cpu().numpy()

    t60_rir = torch.vstack(t60_rir).cpu().numpy()
    c50_rir = torch.vstack(c50_rir).cpu().numpy()

    print("Computing UMAP embeddings...")
    reducer = umap.UMAP()
    emb_vae = reducer.fit_transform(z_vae)
    emb_prop = reducer.fit_transform(z_prop)
    emb_ctr = reducer.fit_transform(z_ctr)

    octave_freqs = [125, 250, 500, 1000, 2000, 4000, 8000]

    # Compute mean across all octaves
    t60_mean = t60.mean(axis=1)
    c50_mean = c50.mean(axis=1)

    t60_rir_mean = t60_rir.mean(axis=1)
    c50_rir_mean = c50_rir.mean(axis=1)

    fig, axes = plt.subplots(2, 3, figsize=(14, 6))

    # Top row: T60 (mean across octaves)
    # Column 0: VAE
    sc1 = axes[0, 0].scatter(
        emb_vae[:, 0],
        emb_vae[:, 1],
        c=t60_rir_mean,
        cmap="viridis",
        s=10,
        alpha=0.6,
    )
    axes[0, 0].set_title("VAE - T60 (mean)", fontsize=14, fontweight="bold")
    axes[0, 0].set_xlabel("UMAP 1")
    axes[0, 0].set_ylabel("UMAP 2")
    plt.colorbar(sc1, ax=axes[0, 0], label="T60 [s]")

    # Column 1: Proposed
    sc2 = axes[0, 1].scatter(
        emb_prop[:, 0],
        emb_prop[:, 1],
        c=t60_mean,
        cmap="viridis",
        s=10,
        alpha=0.6,
    )
    axes[0, 1].set_title("Proposed - T60 (mean)", fontsize=14, fontweight="bold")
    axes[0, 1].set_xlabel("UMAP 1")
    axes[0, 1].set_ylabel("UMAP 2")
    plt.colorbar(sc2, ax=axes[0, 1], label="T60 [s]")

    # Column 2: Contrastive
    sc3 = axes[0, 2].scatter(
        emb_ctr[:, 0],
        emb_ctr[:, 1],
        c=t60_mean,
        cmap="viridis",
        s=10,
        alpha=0.6,
    )
    axes[0, 2].set_title("Contrastive - T60 (mean)", fontsize=14, fontweight="bold")
    axes[0, 2].set_xlabel("UMAP 1")
    axes[0, 2].set_ylabel("UMAP 2")
    plt.colorbar(sc3, ax=axes[0, 2], label="T60 [s]")

    # Bottom row: C50 (mean across octaves)
    # Column 0: VAE
    sc4 = axes[1, 0].scatter(
        emb_vae[:, 0],
        emb_vae[:, 1],
        c=c50_rir_mean,
        cmap="plasma",
        s=10,
        alpha=0.6,
    )
    axes[1, 0].set_title("VAE - C50 (mean)", fontsize=14, fontweight="bold")
    axes[1, 0].set_xlabel("UMAP 1")
    axes[1, 0].set_ylabel("UMAP 2")
    plt.colorbar(sc4, ax=axes[1, 0], label="C50 [dB]")

    # Column 1: Proposed
    sc5 = axes[1, 1].scatter(
        emb_prop[:, 0],
        emb_prop[:, 1],
        c=c50_mean,
        cmap="plasma",
        s=10,
        alpha=0.6,
    )
    axes[1, 1].set_title("Proposed - C50 (mean)", fontsize=14, fontweight="bold")
    axes[1, 1].set_xlabel("UMAP 1")
    axes[1, 1].set_ylabel("UMAP 2")
    plt.colorbar(sc5, ax=axes[1, 1], label="C50 [dB]")

    # Column 2: Contrastive
    sc6 = axes[1, 2].scatter(
        emb_ctr[:, 0], emb_ctr[:, 1], c=c50_mean, cmap="plasma", s=10, alpha=0.6
    )
    axes[1, 2].set_title("Contrastive - C50 (mean)", fontsize=14, fontweight="bold")
    axes[1, 2].set_xlabel("UMAP 1")
    axes[1, 2].set_ylabel("UMAP 2")
    plt.colorbar(sc6, ax=axes[1, 2], label="C50 [dB]")

    plt.tight_layout()
    plt.savefig("plots/umap.png", dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":

    main()
