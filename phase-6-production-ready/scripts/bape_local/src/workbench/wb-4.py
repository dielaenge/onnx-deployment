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
        Path("logs/prop/t60/2025-11-03_20-35-17/"),
        Path("logs/prop/c50/2025-11-03_21-13-50/"),
        Path("logs/prop/edt/2025-11-03_23-11-58/"),
        Path("logs/prop/mag/2025-11-04_00-04-39/"),
    ]

    pths_prop_ft = [
        Path("logs/prop_ft/t60/2025-11-04_02-10-51/"),
        Path("logs/prop_ft/c50/2025-11-04_03-07-28/"),
        Path("logs/prop_ft/edt/2025-11-04_05-58-24/"),
        Path("logs/prop_ft/mag/2025-11-04_08-14-16/"),
    ]

    pths_ctr = [
        Path("logs/ctr_param/t60/2025-11-04_14-04-34/"),
        Path("logs/ctr_param/c50/2025-11-04_14-47-45/"),
        Path("logs/ctr_param/edt/2025-11-04_15-29-28/"),
        Path("logs/ctr_param/mag/2025-11-04_15-56-18/"),
    ]

    paths_ctr_ft = [
        Path("logs/ctr_param_ft/t60/2025-11-04_17-11-06/"),
        Path("logs/ctr_param_ft/c50/2025-11-04_18-09-05/"),
        Path("logs/ctr_param_ft/edt/2025-11-04_21-01-00/"),
        Path("logs/ctr_param_ft/mag/2025-11-04_22-10-25/"),
    ]

    paths_e2e = [
        Path("logs/e2e/t60/2025-11-05_14-40-17/"),
        Path("logs/e2e/c50/2025-11-05_15-33-32/"),
        Path("logs/e2e/edt/2025-11-05_16-10-48/"),
        Path("logs/e2e/mag/2025-11-05_16-36-23/"),
    ]

    prop, prop_ft, ctr, ctr_ft, e2e = [], [], [], [], []

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

    for pth in paths_e2e:
        with open(pth / "output.pkl", "rb") as f:
            data = pickle.load(f)
            e2e.append(data)

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

    e2e_est_t60, e2e_est_c50, e2e_est_edt, e2e_est_prel = [
        np.vstack([batch["est"] for batch in param]) for param in e2e
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

    e2e_gt_t60, e2e_gt_c50, e2e_gt_edt, e2e_gt_prel = [
        np.vstack([batch["gt"] for batch in param]) for param in e2e
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

    snrs_e2e_t60, snrs_e2e_c50, snrs_e2e_edt, snrs_e2e_prel = [
        np.hstack([batch["snr"] for batch in param]) for param in e2e
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

    t60_e2e_ape = 100 * (np.abs(e2e_est_t60 - e2e_gt_t60) / (np.abs(e2e_gt_t60) + 1e-6))

    # compute absolute errors for c50
    c50_prop_ae = np.abs(prop_est_c50 - prop_gt_c50)
    c50_prop_ft_ae = np.abs(prop_ft_est_c50 - prop_ft_gt_c50)
    c50_ctr_ae = np.abs(ctr_est_c50 - ctr_gt_c50)
    c50_ctr_ft_ae = np.abs(ctr_ft_est_c50 - ctr_ft_gt_c50)

    c50_e2e_ae = np.abs(e2e_est_c50 - e2e_gt_c50)

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

    edt_e2e_ape = 100 * (np.abs(e2e_est_edt - e2e_gt_edt) / (np.abs(e2e_gt_edt) + 1e-6))

    # compute absolute errors for prel
    prel_prop_ae = np.abs(prop_est_prel - prop_gt_prel)
    prel_prop_ft_ae = np.abs(prop_ft_est_prel - prop_ft_gt_prel)
    prel_ctr_ae = np.abs(ctr_est_prel - ctr_gt_prel)
    prel_ctr_ft_ae = np.abs(ctr_ft_est_prel - ctr_ft_gt_prel)

    prel_e2e_ae = np.abs(e2e_est_prel - e2e_gt_prel)

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

    # Prepare data for each parameter (frequency-averaged across octave bands)
    # Note: We average over the octave-band dimension (axis=1). To revert to a single
    # octave band view, replace np.mean(<err>, axis=1) by <err>[:, octave_idx]
    # and reintroduce an "octave_idx = ..." selection above.
    params_data = [
        {  # T60
            "prop": {"errors": np.mean(t60_prop_ape, axis=1), "snrs": snrs_prop_t60},
            "prop_ft": {
                "errors": np.mean(t60_prop_ft_ape, axis=1),
                "snrs": snrs_prop_ft_t60,
            },
            "ctr": {"errors": np.mean(t60_ctr_ape, axis=1), "snrs": snrs_ctr_t60},
            "ctr_ft": {
                "errors": np.mean(t60_ctr_ft_ape, axis=1),
                "snrs": snrs_ctr_ft_t60,
            },
            "e2e": {"errors": np.mean(t60_e2e_ape, axis=1), "snrs": snrs_e2e_t60},
            "ylabel": "MAPE [\%]",
        },
        {  # C50
            "prop": {"errors": np.mean(c50_prop_ae, axis=1), "snrs": snrs_prop_c50},
            "prop_ft": {
                "errors": np.mean(c50_prop_ft_ae, axis=1),
                "snrs": snrs_prop_ft_c50,
            },
            "ctr": {"errors": np.mean(c50_ctr_ae, axis=1), "snrs": snrs_ctr_c50},
            "ctr_ft": {
                "errors": np.mean(c50_ctr_ft_ae, axis=1),
                "snrs": snrs_ctr_ft_c50,
            },
            "e2e": {"errors": np.mean(c50_e2e_ae, axis=1), "snrs": snrs_e2e_c50},
            "ylabel": "MAE [dB]",
        },
        {  # EDT
            "prop": {"errors": np.mean(edt_prop_ape, axis=1), "snrs": snrs_prop_edt},
            "prop_ft": {
                "errors": np.mean(edt_prop_ft_ape, axis=1),
                "snrs": snrs_prop_ft_edt,
            },
            "ctr": {"errors": np.mean(edt_ctr_ape, axis=1), "snrs": snrs_ctr_edt},
            "ctr_ft": {
                "errors": np.mean(edt_ctr_ft_ape, axis=1),
                "snrs": snrs_ctr_ft_edt,
            },
            "e2e": {"errors": np.mean(edt_e2e_ape, axis=1), "snrs": snrs_e2e_edt},
            "ylabel": "MAPE [\%]",
        },
        {  # PREL
            "prop": {"errors": np.mean(prel_prop_ae, axis=1), "snrs": snrs_prop_prel},
            "prop_ft": {
                "errors": np.mean(prel_prop_ft_ae, axis=1),
                "snrs": snrs_prop_ft_prel,
            },
            "ctr": {"errors": np.mean(prel_ctr_ae, axis=1), "snrs": snrs_ctr_prel},
            "ctr_ft": {
                "errors": np.mean(prel_ctr_ft_ae, axis=1),
                "snrs": snrs_ctr_ft_prel,
            },
            "e2e": {"errors": np.mean(prel_e2e_ae, axis=1), "snrs": snrs_e2e_prel},
            "ylabel": "MAE [dB]",
        },
    ]

    variant_names = ["prop", "prop_ft", "ctr", "ctr_ft", "e2e"]
    variant_labels = ["PROP", "PROP-FT", "CTR", "CTR-FT", "E2E"]
    colors = [
        "#1f77b4",  # blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#d62728",  # red
        "#9467bd",  # purple
    ]  # distinct colors
    # Use same markers/line styles as in wb-1.py for first five variants
    markers = ["D", "d", "x", "X", "o"]
    lss = ["-", "-", "-", "-", "-"]

    # Create figure with a dedicated bottom row for legend using GridSpec
    fig = plt.figure(figsize=(8, 2.2))
    gs = fig.add_gridspec(
        nrows=2, ncols=4, height_ratios=[12, 4], hspace=0.2, wspace=0.5
    )
    axes = [fig.add_subplot(gs[0, i]) for i in range(4)]

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
                linewidth=1.2,
                marker=markers[variant_idx],
                linestyle=lss[variant_idx],
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

    # Create a dedicated legend axis on the bottom row spanning all columns
    handles, labels_legend = axes[0].get_legend_handles_labels()
    legend_ax = fig.add_subplot(gs[1, :])
    legend_ax.axis("off")
    legend_ax.legend(
        handles,
        labels_legend,
        loc="lower center",
        ncol=5,
        frameon=False,
        bbox_transform=fig.transFigure,  # figure-normalized coordinates [0,1]
        bbox_to_anchor=(0.5, 0.0),  # keep at the figure bottom
        borderaxespad=0.0,
    )
    # Reduce bottom margin so legend sits closer to the figure edge
    fig.subplots_adjust(bottom=0.02, left=0.06, right=0.99, top=0.9)

    plt.savefig("plots/snr_vs_error.pdf", dpi=300)
    plt.savefig("plots/snr_vs_error.png", dpi=300)

    plt.close()


if __name__ == "__main__":

    main()
