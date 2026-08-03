import pickle
import numpy as np
from pathlib import Path

import matplotlib.pyplot as plt

import seaborn as sns

from src.util.metrics import single_compute


"""
mae = np.mean(np.abs(gt - pred))
pcc = np.corrcoef(gt, pred)[0, 1]
bias = np.mean(pred - gt)
mape = np.mean(np.abs(gt - pred) / (np.abs(gt) + 1e-6)) * 100
smape = np.mean(np.abs(gt - pred) / (np.abs(gt) + np.abs(pred) + 1e-6)) * 100
"""


def main():
    """SNR plot"""

    pths_prop = [
        Path("logs/prop/2025-10-29_21-45-58/"),
        Path("logs/prop/2025-10-29_22-01-48/"),
        Path("logs/prop/2025-10-29_22-30-44/"),
        Path("logs/prop/2025-10-29_22-48-17/"),
    ]

    pths_ctr = [
        Path("logs/ctr_param/2025-10-30_01-55-26/"),
        Path("logs/ctr_param/2025-10-30_02-32-48/"),
        Path("logs/ctr_param/2025-10-30_03-12-46/"),
        Path("logs/ctr_param/2025-10-30_03-44-14/"),
    ]

    pths_prop_ft = [
        Path("logs/prop_ft/2025-10-29_23-04-03/"),
        Path("logs/prop_ft/2025-10-29_23-19-53/"),
        Path("logs/prop_ft/2025-10-29_23-44-41/"),
        Path("logs/prop_ft/2025-10-30_00-12-16/"),
    ]

    paths_ctr_ft = [
        Path("logs/ctr_param_ft/2025-10-30_04-28-11/"),
        Path("logs/ctr_param_ft/2025-10-30_05-06-00/"),
        Path("logs/ctr_param_ft/2025-10-30_05-34-26/"),
        Path("logs/ctr_param_ft/2025-10-30_11-24-53/"),
    ]

    prop, prop_ft, ctr, ctr_ft = [], [], [], []

    for pth in pths_prop:
        with open(pth / "output.pkl", "rb") as f:
            data = pickle.load(f)
            prop.append(data)

    for pth in pths_prop_ft:
        with open(pth / "output.pkl", "rb") as f:
            data = pickle.load(f)
            prop_ft.append(data)

    for pth in pths_ctr:
        with open(pth / "output.pkl", "rb") as f:
            data = pickle.load(f)
            ctr.append(data)

    for pth in paths_ctr_ft:
        with open(pth / "output.pkl", "rb") as f:
            data = pickle.load(f)
            ctr_ft.append(data)

    prop_est_t60, prop_est_c50, prop_est_edt, prop_est_prel = [
        np.vstack([batch["est"] for batch in param]) for param in prop
    ]
    prop_ft_est_t60, prop_ft_est_c50, prop_ft_est_edt, prop_ft_est_prel = [
        np.vstack([batch["est"] for batch in param]) for param in prop_ft
    ]
    ctr_est_t60, ctr_est_c50, ctr_est_edt, ctr_est_prel = [
        np.vstack([batch["est"] for batch in param]) for param in ctr
    ]
    ctr_ft_est_t60, ctr_ft_est_c50, ctr_ft_est_edt, ctr_ft_est_prel = [
        np.vstack([batch["est"] for batch in param]) for param in ctr_ft
    ]

    prop_gt_t60, prop_gt_c50, prop_gt_edt, prop_gt_prel = [
        np.vstack([batch["gt"] for batch in param]) for param in prop
    ]
    prop_ft_gt_t60, prop_ft_gt_c50, prop_ft_gt_edt, prop_ft_gt_prel = [
        np.vstack([batch["gt"] for batch in param]) for param in prop_ft
    ]
    ctr_gt_t60, ctr_gt_c50, ctr_gt_edt, ctr_gt_prel = [
        np.vstack([batch["gt"] for batch in param]) for param in ctr
    ]
    ctr_ft_gt_t60, ctr_ft_gt_c50, ctr_ft_gt_edt, ctr_ft_gt_prel = [
        np.vstack([batch["gt"] for batch in param]) for param in ctr_ft
    ]

    snrs_prop_t60, snrs_prop_c50, snrs_prop_edt, snrs_prop_prel = [
        np.hstack([batch["snr"] for batch in param]) for param in prop
    ]
    snrs_prop_ft_t60, snrs_prop_ft_c50, snrs_prop_ft_edt, snrs_prop_ft_prel = [
        np.hstack([batch["snr"] for batch in param]) for param in prop_ft
    ]
    snrs_ctr_t60, snrs_ctr_c50, snrs_ctr_edt, snrs_ctr_prel = [
        np.hstack([batch["snr"] for batch in param]) for param in ctr
    ]
    snrs_ctr_ft_t60, snrs_ctr_ft_c50, snrs_ctr_ft_edt, snrs_ctr_ft_prel = [
        np.hstack([batch["snr"] for batch in param]) for param in ctr_ft
    ]

    # compute absolute percentage errors for t60
    t60_prop_ape = 100 * (
        np.abs(prop_est_t60 - prop_gt_t60) / (np.abs(prop_gt_t60) + 1e-6)
    )
    t60_prop_ft_ape = 100 * (
        np.abs(prop_ft_est_t60 - prop_ft_gt_t60) / (np.abs(prop_ft_gt_t60) + 1e-6)
    )
    t60_ctr_ape = 100 * (np.abs(ctr_est_t60 - ctr_gt_t60) / (np.abs(ctr_gt_t60) + 1e-6))
    t60_ctr_ft_ape = 100 * (
        np.abs(ctr_ft_est_t60 - ctr_ft_gt_t60) / (np.abs(ctr_ft_gt_t60) + 1e-6)
    )

    # compute absolute errors for c50
    c50_prop_ae = np.abs(prop_est_c50 - prop_gt_c50)
    c50_prop_ft_ae = np.abs(prop_ft_est_c50 - prop_ft_gt_c50)
    c50_ctr_ae = np.abs(ctr_est_c50 - ctr_gt_c50)
    c50_ctr_ft_ae = np.abs(ctr_ft_est_c50 - ctr_ft_gt_c50)

    # compute absolute percentage errors for edt
    edt_prop_ape = 100 * (
        np.abs(prop_est_edt - prop_gt_edt) / (np.abs(prop_gt_edt) + 1e-6)
    )
    edt_prop_ft_ape = 100 * (
        np.abs(prop_ft_est_edt - prop_ft_gt_edt) / (np.abs(prop_ft_gt_edt) + 1e-6)
    )
    edt_ctr_ape = 100 * (np.abs(ctr_est_edt - ctr_gt_edt) / (np.abs(ctr_gt_edt) + 1e-6))
    edt_ctr_ft_ape = 100 * (
        np.abs(ctr_ft_est_edt - ctr_ft_gt_edt) / (np.abs(ctr_ft_gt_edt) + 1e-6)
    )

    # compute absolute errors for prel
    prel_prop_ae = np.abs(prop_est_prel - prop_gt_prel)
    prel_prop_ft_ae = np.abs(prop_ft_est_prel - prop_ft_gt_prel)
    prel_ctr_ae = np.abs(ctr_est_prel - ctr_gt_prel)
    prel_ctr_ft_ae = np.abs(ctr_ft_est_prel - ctr_ft_gt_prel)

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

    labels = [
        r"$\mathrm{T}_{60}$",
        r"$\mathrm{C}_{50}$",
        r"$\mathrm{EDT}$",
        r"$\mathrm{P}_{\mathrm{rel}}$",
    ]

    # SNR vs Error plotting
    num_bins = 6
    snr_min, snr_max = 0, 30
    bin_edges = np.linspace(snr_min, snr_max, num_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    octave_idx = 4  # 1kHz octave

    # Prepare data for each parameter
    params_data = [
        {  # T60
            "prop": {"errors": t60_prop_ape[:, octave_idx], "snrs": snrs_prop_t60},
            "prop_ft": {
                "errors": t60_prop_ft_ape[:, octave_idx],
                "snrs": snrs_prop_ft_t60,
            },
            "ctr": {"errors": t60_ctr_ape[:, octave_idx], "snrs": snrs_ctr_t60},
            "ctr_ft": {
                "errors": t60_ctr_ft_ape[:, octave_idx],
                "snrs": snrs_ctr_ft_t60,
            },
            "ylabel": "MAPE [\%]",
        },
        {  # C50
            "prop": {"errors": c50_prop_ae[:, octave_idx], "snrs": snrs_prop_c50},
            "prop_ft": {
                "errors": c50_prop_ft_ae[:, octave_idx],
                "snrs": snrs_prop_ft_c50,
            },
            "ctr": {"errors": c50_ctr_ae[:, octave_idx], "snrs": snrs_ctr_c50},
            "ctr_ft": {"errors": c50_ctr_ft_ae[:, octave_idx], "snrs": snrs_ctr_ft_c50},
            "ylabel": "MAE [dB]",
        },
        {  # EDT
            "prop": {"errors": edt_prop_ape[:, octave_idx], "snrs": snrs_prop_edt},
            "prop_ft": {
                "errors": edt_prop_ft_ape[:, octave_idx],
                "snrs": snrs_prop_ft_edt,
            },
            "ctr": {"errors": edt_ctr_ape[:, octave_idx], "snrs": snrs_ctr_edt},
            "ctr_ft": {
                "errors": edt_ctr_ft_ape[:, octave_idx],
                "snrs": snrs_ctr_ft_edt,
            },
            "ylabel": "MAPE [\%]",
        },
        {  # PREL
            "prop": {"errors": prel_prop_ae[:, octave_idx], "snrs": snrs_prop_prel},
            "prop_ft": {
                "errors": prel_prop_ft_ae[:, octave_idx],
                "snrs": snrs_prop_ft_prel,
            },
            "ctr": {"errors": prel_ctr_ae[:, octave_idx], "snrs": snrs_ctr_prel},
            "ctr_ft": {
                "errors": prel_ctr_ft_ae[:, octave_idx],
                "snrs": snrs_ctr_ft_prel,
            },
            "ylabel": "MAE [dB]",
        },
    ]

    variant_names = ["prop", "prop_ft", "ctr", "ctr_ft"]
    variant_labels = ["PROP", "PROP-FT", "CTR", "CTR-FT"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]  # distinct colors

    fig, axes = plt.subplots(1, 4, figsize=(10, 2.5))

    for param_idx, (ax, param_label, param_data) in enumerate(
        zip(axes, labels, params_data)
    ):
        for variant_idx, variant_name in enumerate(variant_names):
            errors = param_data[variant_name]["errors"]
            snrs = param_data[variant_name]["snrs"]

            bin_means = []
            bin_stds = []

            for i in range(num_bins):
                bin_mask = (snrs >= bin_edges[i]) & (snrs < bin_edges[i + 1])
                if bin_mask.sum() > 0:
                    bin_means.append(np.mean(errors[bin_mask]))
                    bin_stds.append(np.std(errors[bin_mask]))
                else:
                    bin_means.append(np.nan)
                    bin_stds.append(np.nan)

            bin_means = np.array(bin_means)
            bin_stds = np.array(bin_stds)

            # Plot mean with shaded std
            ax.plot(
                bin_centers,
                bin_means,
                label=variant_labels[variant_idx],
                color=colors[variant_idx],
                linewidth=1.5,
                marker="o",
                markersize=4,
            )
            # ax.fill_between(
            #     bin_centers,
            #     bin_means - bin_stds,
            #     bin_means + bin_stds,
            #     alpha=0.2,
            #     color=colors[variant_idx],
            # )

        ax.set_xlabel("SNR [dB]")
        ax.set_ylabel(param_data["ylabel"])
        ax.set_title(param_label)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(snr_min, snr_max)

    # Create a single legend below the subplots
    handles, labels_legend = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels_legend,
        loc="lower center",
        ncol=4,
        bbox_to_anchor=(0.5, -0.05),
        frameon=False,
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.25)  # Make room for legend
    # plt.savefig("snr_vs_error.pdf", dpi=300, bbox_inches="tight")
    plt.savefig("plots/snr_vs_error.png", dpi=300, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":

    main()
