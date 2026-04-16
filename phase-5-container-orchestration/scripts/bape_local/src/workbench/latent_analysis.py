from pathlib import Path

import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from matplotlib import gridspec
from matplotlib.collections import QuadMesh
from tqdm import tqdm
from omegaconf import OmegaConf
from hydra.utils import instantiate

noise_len = 128
latent_dim = 1024
batch_size = 16
batch_lim = 256
snr = 12

# rir data loader
rir_data_cfg = OmegaConf.load("conf/data/rirs.yaml")
rir_data_cfg.train_url = "data/dataset_rirs/train-{0000..0000}.tar"
rir_data_cfg.valid_url = "data/dataset_rirs/valid-{0000..0000}.tar"
rir_data_cfg.test_url = "data/dataset_rirs/test-{0000..0000}.tar"
rir_data_cfg.batch_size = batch_size
rir_data_cfg.num_workers = 0
rir_datamodule = instantiate(rir_data_cfg)

# speech data loader
speech_data_cfg = OmegaConf.load("conf/data/speech.yaml")
speech_data_cfg.train_url = "data/dataset_speech/train-{0000..0015}.tar"
speech_data_cfg.valid_url = "data/dataset_speech/valid-{0000..0001}.tar"
speech_data_cfg.test_url = "data/dataset_speech/test-{0000..0001}.tar"
speech_data_cfg.batch_size = batch_size
speech_data_cfg.num_workers = 0
speech_datamodule = instantiate(speech_data_cfg)

# param estimator paths
estimator_paths_sb = [
    Path("logs/sb/2025-11-03_05-59-37/"),
    Path("logs/sb/2025-11-03_06-07-09/"),
    Path("logs/sb/2025-11-03_06-22-44/"),
    Path("logs/sb/2025-11-03_06-30-44/"),
]

estimator_paths_prop = [
    Path("logs/prop/t60/2025-11-03_20-51-50/"),
    Path("logs/prop/c50/2025-11-03_21-44-08/"),
    Path("logs/prop/edt/2025-11-03_23-12-20/"),
    Path("logs/prop/mag/2025-11-04_00-56-30/"),
]

# param estimator paths
estimator_paths_ctr = [
    Path("logs/ctr_param/t60/2025-11-04_14-04-34/"),
    Path("logs/ctr_param/c50/2025-11-04_14-47-45/"),
    Path("logs/ctr_param/edt/2025-11-04_15-29-28/"),
    Path("logs/ctr_param/mag/2025-11-04_15-56-18/"),
]

# embedders: [rir, prop, ctr]
embedder_states = [
    "logs/vae/2025-11-02_17-44-22/model.pth",
    "logs/speech_encoder/2025-11-01_14-27-32/model.pth",
    "logs/ctr/2025-11-03_18-49-51/model.pth",
]

embedder_config_paths = [
    "conf/model/vae.yaml",
    "conf/model/speech_encoder.yaml",
    "conf/model/speech_encoder_ctr.yaml",
]

# load models
embedders = []
for i, (cfg_path, state) in enumerate(zip(embedder_config_paths, embedder_states)):
    model_cfg = OmegaConf.load(cfg_path)
    model = instantiate(model_cfg)
    state = torch.load(state)
    model.load_state_dict(state, strict=True)
    model.eval()
    embedders.append(model)


# semiblind rir-based model
qa_rir = []
for estimator_path in estimator_paths_sb:
    model_cfg = OmegaConf.load(estimator_path / "config.yaml")
    model_cfg.model["reset_encoder"] = False  # tiny fix
    param_model = instantiate(model_cfg.model)
    state = torch.load(estimator_path / "model.pth")
    param_model.load_state_dict(state, strict=True)
    var_z = []
    batch_count = 0
    param_model.eval()
    with torch.no_grad():
        for i, batch in tqdm(enumerate(rir_datamodule.train_loader)):
            rir, spec, norm, params = batch
            bs = spec.size(0)
            z = embedders[0](spec)[1].flatten(start_dim=1)
            estimates = []
            var_p = []
            # noise_std = torch.sqrt(z.var(dim=1) / (10 ** (snr * 0.1)))
            noise_std = torch.sqrt(z.var(dim=0) / (10 ** (snr * 0.1)))
            for i in range(z.size(-1)):
                zn = z.tile(noise_len, 1)
                # zn[:, i] += torch.randn(noise_len * bs) * noise_std.tile(noise_len)
                zn[:, i] += torch.randn(noise_len * bs) * noise_std[i]
                estimates.append(param_model.heads[0](zn))
            var_z.append(torch.stack(estimates).var(dim=1))
            batch_count += 1
            if batch_count > batch_lim:
                break
        qa_rir.append(torch.stack(var_z).mean(dim=0))
qa_rir = torch.hstack(qa_rir)
dis_rir = torch.corrcoef(qa_rir.T)


# proposed speech-based model
qa_prop = []
for estimator_path in estimator_paths_prop:
    model_cfg = OmegaConf.load(estimator_path / "config.yaml")
    param_model = instantiate(model_cfg.model)
    state = torch.load(estimator_path / "model.pth")
    param_model.load_state_dict(state, strict=True)
    var_z = []
    batch_count = 0
    param_model.eval()
    with torch.no_grad():
        for i, batch in tqdm(enumerate(speech_datamodule.train_loader)):
            wetspec, rirspec, norm, _, param = batch
            bs = wetspec.size(0)
            z = embedders[1](wetspec)[0]
            estimates = []
            var_p = []
            # noise_std = torch.sqrt(z.var(dim=1) / (10 ** (snr * 0.1)))
            noise_std = torch.sqrt(z.var(dim=0) / (10 ** (snr * 0.1)))
            for i in range(z.size(-1)):
                zn = z.tile(noise_len, 1)
                zn[:, i] += torch.randn(noise_len * bs) * noise_std[i]
                estimates.append(param_model.heads[1](zn))
            var_z.append(torch.stack(estimates).var(dim=1))
            batch_count += 1
            if batch_count > batch_lim:
                break
        qa_prop.append(torch.stack(var_z).mean(dim=0))
qa_prop = torch.hstack(qa_prop)
dis_prop = torch.corrcoef(qa_prop.T)


# contrastive speech-based model
qa_ctr = []
for estimator_path in estimator_paths_ctr:
    model_cfg = OmegaConf.load(estimator_path / "config.yaml")
    param_model = instantiate(model_cfg.model)
    state = torch.load(estimator_path / "model.pth")
    param_model.load_state_dict(state, strict=True)
    var_z = []
    batch_count = 0
    param_model.eval()
    with torch.no_grad():
        for i, batch in tqdm(enumerate(speech_datamodule.train_loader)):
            wetspec, rirspec, norm, _, param = batch
            bs = wetspec.size(0)
            z = embedders[2](wetspec)[0]
            estimates = []
            var_p = []
            noise_std = torch.sqrt(z.var(dim=0) / (10 ** (snr * 0.1)))
            for i in range(z.size(-1)):
                zn = z.tile(noise_len, 1)
                zn[:, i] += torch.randn(noise_len * bs) * noise_std[i]
                estimates.append(param_model.heads[1](zn))
            var_z.append(torch.stack(estimates).var(dim=1))
            batch_count += 1
            if batch_count > batch_lim:
                break
        qa_ctr.append(torch.stack(var_z).mean(dim=0))
qa_ctr = torch.hstack(qa_ctr)
dis_ctr = torch.corrcoef(qa_ctr.T)

# Plotting
plt.rcParams.update(
    {
        "text.usetex": True,  # Enable LaTeX rendering
        "font.family": "serif",  # Use a serif font by default
        "font.size": 9,
        "font.serif": [
            "Computer Modern"
        ],  # Use Computer Modern, the default LaTeX font
        "text.latex.preamble": r"\usepackage{amsmath}",
        # Ensure fonts embed nicely in vector outputs; rasterization will apply only to image layers
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

labels = [
    r"$\mathrm{T}_{60}$",
    r"$\mathrm{C}_{50}$",
    r"$\mathrm{EDT}$",
    r"$\mathrm{P}_{\mathrm{rel}}$",
]

label_x = [0.12, 0.4, 0.65, 0.88]
label_y = [0.8, 0.57, 0.32, 0.07]

tixx = [7, 14, 21]
fss = [9, 9, 9, 8]

fg = plt.figure(figsize=(7, 2.4))

titles = [r"$q_\phi$", r"$q_\psi$", r"$q_c$"]

gs = gridspec.GridSpec(nrows=1, ncols=4, wspace=0.12, width_ratios=[1, 1, 1, 0.1])

for i, dmap in enumerate([dis_rir, dis_prop, dis_ctr]):  # dis_maps
    ax = fg.add_subplot(gs[i])  # Use first 3 columns for heatmaps

    # Create a mask for the lower triangle
    mask = np.triu(np.ones_like(dmap, dtype=bool), k=1)
    if i < 2:
        hm_ax = sns.heatmap(
            dmap,
            ax=ax,
            mask=mask,
            cbar=False,
            cmap="viridis",
            vmax=1.0,
            vmin=0.0,
        )  # No colorbar for first 2
    else:
        # Create a separate axis for the colorbar using the 4th column
        cbar_ax = fg.add_subplot(gs[i + 1])
        hm_ax = sns.heatmap(
            # (dmap + 1) * 0.5,
            dmap,
            ax=ax,
            mask=mask,
            cbar=True,
            cbar_ax=cbar_ax,
            cmap="viridis",
            vmax=1.0,
            vmin=0.0,
        )

    # Rasterize only the heatmap artist so lines/text stay as vectors in PDF/SVG
    for coll in ax.collections:
        if isinstance(coll, QuadMesh):
            coll.set_rasterized(True)
    # Optional: also rasterize the colorbar mesh if present
    if "cbar_ax" in locals():
        for coll in cbar_ax.collections:
            if isinstance(coll, QuadMesh):
                coll.set_rasterized(True)

    ax.text(
        0.65,
        0.7,
        titles[i],
        transform=ax.transAxes,
        ha="center",
        fontsize=12,
        bbox=dict(facecolor="white", edgecolor="gray", boxstyle="square,pad=0.5"),
    )

    [ax.plot([0, 27], [tix, tix], lw=1, ls="--", color="white") for tix in tixx]
    [ax.plot([tix, tix], [0, 27], lw=1, ls="--", color="white") for tix in tixx]

    ax.set_xticks([])
    ax.set_yticks([])

    # if i == 0:
    for y, label, fs in zip(label_y, labels, fss):
        ax.text(
            -0.04,
            y,
            label,
            rotation=90,
            transform=ax.transAxes,
            ha="right",
            fontsize=fs,
        )
    for x, label in zip(label_x, labels):
        ax.text(x, -0.07, label, rotation=0, transform=ax.transAxes, ha="center")

    if i == 2:
        cbar_ax.text(1.37, 0.5, "PCC", rotation=-90, transform=ax.transAxes, fontsize=9)

plt.subplots_adjust(left=0.04, bottom=0.12, right=0.93, top=0.97)

# Save both PNG and PDF; PDF will contain rasterized heatmap tiles but vector text/lines
plt.savefig("plots/vars2.png", dpi=300, bbox_inches="tight")
plt.savefig("plots/vars2.pdf", dpi=300, bbox_inches="tight")
plt.show()
