from pathlib import Path
from tqdm import tqdm
import torch
from lightning import seed_everything
import matplotlib.pyplot as plt

from omegaconf import OmegaConf
from hydra.utils import instantiate

seed_everything(42)

noise_len = 128
latent_dim = 1024
batch_size = 16
batch_lim = 256

snrs = torch.linspace(0, 30, 6)

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

disses_rir, disses_prop, disses_ctr = [], [], []
for snr in tqdm(snrs):
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
            for i, batch in enumerate(rir_datamodule.test_loader):
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
    disses_rir.append(torch.corrcoef(qa_rir.T))

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
            for i, batch in enumerate(speech_datamodule.test_loader):
                wetspec, rirspec, norm, _, param = batch
                bs = wetspec.size(0)
                z = embedders[1](wetspec)[0]
                estimates = []
                var_p = []
                # noise_std = torch.sqrt(z.var(dim=1) / (10 ** (snr * 0.1)))
                noise_std = torch.sqrt(z.var(dim=0) / (10 ** (snr * 0.1)))
                for i in range(z.size(-1)):
                    zn = z.tile(noise_len, 1)
                    # zn[:, i] += torch.randn(noise_len * bs) * noise_std.tile(noise_len)
                    zn[:, i] += torch.randn(noise_len * bs) * noise_std[i]
                    estimates.append(param_model.heads[1](zn))
                var_z.append(torch.stack(estimates).var(dim=1))
                batch_count += 1
                if batch_count > batch_lim:
                    break
            qa_prop.append(torch.stack(var_z).mean(dim=0))
    qa_prop = torch.hstack(qa_prop)
    disses_prop.append(torch.corrcoef(qa_prop.T))

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
            for i, batch in enumerate(speech_datamodule.test_loader):
                wetspec, rirspec, norm, _, param = batch
                bs = wetspec.size(0)
                z = embedders[2](wetspec)[0]
                estimates = []
                var_p = []
                # noise_std = torch.sqrt(z.var(dim=1) / (10 ** (snr / 10)))
                noise_std = torch.sqrt(z.var(dim=0) / (10 ** (snr * 0.1)))
                for i in range(z.size(-1)):
                    zn = z.tile(noise_len, 1)
                    # zn[:, i] += torch.randn(noise_len * bs) * noise_std.tile(noise_len)
                    zn[:, i] += torch.randn(noise_len * bs) * noise_std[i]
                    estimates.append(param_model.heads[1](zn))
                var_z.append(torch.stack(estimates).var(dim=1))
                batch_count += 1
                if batch_count > batch_lim:
                    break
            qa_ctr.append(torch.stack(var_z).mean(dim=0))
    qa_ctr = torch.hstack(qa_ctr)
    disses_ctr.append(torch.corrcoef(qa_ctr.T))

n = disses_rir[0].shape[0]
mle_rir = [1 / (n**2 - n) * (torch.sum(dis) - n) for dis in disses_rir]
mle_prop = [1 / (n**2 - n) * (torch.sum(dis) - n) for dis in disses_prop]
mle_ctr = [1 / (n**2 - n) * (torch.sum(dis) - n) for dis in disses_ctr]

titles = [r"$q_\phi$", r"$q_\psi$", r"$q_c$"]


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
    }
)

# Get the viridis colormap
viridis = plt.get_cmap("viridis")

# Extract colors at positions 0.0, 0.5, and 1.0
colors = [viridis(0.0), viridis(0.5), viridis(1.0)]

fg = plt.figure(figsize=(4, 1.7))

ax = fg.add_subplot(1, 1, 1)
ax.plot(snrs, mle_rir, label=titles[0], color=colors[0], marker="o")
ax.plot(snrs, mle_prop, label=titles[1], color=colors[1], marker="s")
ax.plot(snrs, mle_ctr, label=titles[2], color=colors[2], marker="x")
ax.grid()
# ax.set_xlim(snrs.min(), snrs.max())
ax.legend(loc="upper right", fontsize=8, ncols=1)
ax.set_xlabel(r"$\mathrm{SNR}_z\;\mathrm{[dB]}$", fontsize=10)
ax.set_ylabel("MLE")

ax.set_xticks(snrs)

plt.subplots_adjust(left=0.15, bottom=0.24, right=0.98, top=0.98)
# plt.tight_layout()
plt.savefig("plots/var_sweep_xxxxxxx.png", dpi=300, bbox_inches="tight")
plt.savefig("plots/var_sweep_xxxxxxx.pdf", dpi=300, bbox_inches="tight")
