import json
import pickle

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def read_metrics(paths) -> dict:
    # compute average metrics over multiple runs from json files

    all_metrics = []
    for path in paths:
        # open json metrics file
        with open(f"logs/{path}/metrics.json", "r") as f:
            metrics = json.load(f)
            all_metrics.append(metrics)

    average_metrics = {key: [] for key in all_metrics[0].keys()}

    for key in average_metrics.keys():
        for metrics in all_metrics:
            average_metrics[key].append(metrics[key])

    for key in average_metrics.keys():
        mean = np.array(average_metrics[key]).mean(axis=0)
        std = np.array(average_metrics[key]).std(axis=0)
        average_metrics[key] = np.vstack((mean, std))

    return average_metrics


def main():

    prop_t60 = [
        "prop/t60/2025-11-03_20-35-17",
        "prop/t60/2025-11-03_20-51-50",
        "prop/t60/2025-11-05_17-36-34",
    ]
    prop_c50 = [
        "prop/c50/2025-11-03_21-13-50",
        "prop/c50/2025-11-03_21-44-08",
        "prop/c50/2025-11-05_17-53-12",
    ]
    prop_edt = [
        "prop/edt/2025-11-03_23-11-58",
        "prop/edt/2025-11-03_23-12-20",
        "prop/edt/2025-11-05_18-42-41",
    ]
    prop_mag = [
        "prop/mag/2025-11-04_00-04-39",
        "prop/mag/2025-11-04_00-56-30",
        "prop/mag/2025-11-05_19-13-44",
    ]

    prop_ft_t60 = [
        "prop_ft/t60/2025-11-04_02-10-51",
        "prop_ft/t60/2025-11-04_02-15-27",
        "prop_ft/t60/2025-11-05_19-36-12",
    ]

    prop_ft_c50 = [
        "prop_ft/c50/2025-11-04_03-44-25",
        "prop_ft/c50/2025-11-05_20-10-09",
        "prop_ft/c50/2025-11-06_12-43-11",
    ]
    prop_ft_edt = [
        "prop_ft/edt/2025-11-04_05-58-24",
        "prop_ft/edt/2025-11-04_06-38-06",
        "prop_ft/edt/2025-11-05_21-09-47",
    ]
    prop_ft_mag = [
        "prop_ft/mag/2025-11-04_08-14-16",
        "prop_ft/mag/2025-11-04_08-14-34",
        "prop_ft/mag/2025-11-05_21-57-02",
    ]

    ctr_param_t60 = [
        "ctr_param/t60/2025-11-04_14-04-34",
        "ctr_param/t60/2025-11-05_03-09-13",
        "ctr_param/t60/2025-11-06_02-21-21",
    ]
    ctr_param_c50 = [
        "ctr_param/c50/2025-11-04_14-47-45",
        "ctr_param/c50/2025-11-05_03-53-13",
        "ctr_param/c50/2025-11-06_03-07-13",
    ]
    ctr_param_edt = [
        "ctr_param/edt/2025-11-04_15-29-28",
        "ctr_param/edt/2025-11-05_05-25-18",
        "ctr_param/edt/2025-11-06_04-29-24",
    ]
    ctr_param_mag = [
        "ctr_param/mag/2025-11-04_15-56-18",
        "ctr_param/mag/2025-11-05_06-12-24",
        "ctr_param/mag/2025-11-06_05-18-46",
    ]

    ctr_param_ft_t60 = [
        "ctr_param_ft/t60/2025-11-04_17-11-06",
        "ctr_param_ft/t60/2025-11-07_01-43-52",
        "ctr_param_ft/t60/2025-11-07_01-43-52",
    ]
    ctr_param_ft_c50 = [
        "ctr_param_ft/c50/2025-11-04_18-09-05",
        "ctr_param_ft/c50/2025-11-05_08-33-08",
        "ctr_param_ft/c50/2025-11-06_07-13-50",
    ]
    ctr_param_ft_edt = [
        "ctr_param_ft/edt/2025-11-04_21-01-00",
        "ctr_param_ft/edt/2025-11-06_19-37-37",
        "ctr_param_ft/edt/2025-11-07_02-49-35",
    ]
    ctr_param_ft_mag = [
        "ctr_param_ft/mag/2025-11-04_22-10-25",
        "ctr_param_ft/mag/2025-11-05_11-14-27",
        "ctr_param_ft/mag/2025-11-06_09-00-42",
    ]

    e2e_t60 = [
        "e2e/t60/2025-11-05_14-40-17",
        "e2e/t60/2025-11-05_22-42-34",
    ]
    e2e_c50 = [
        "e2e/c50/2025-11-05_15-33-32",
        "e2e/c50/2025-11-05_23-42-14",
    ]
    e2e_edt = [
        "e2e/edt/2025-11-05_16-10-48",
        "e2e/edt/2025-11-06_00-36-44",
    ]
    e2e_mag = [
        "e2e/mag/2025-11-05_16-36-23",
        "e2e/mag/2025-11-06_01-21-21",
    ]

    sb_t60 = [
        "sb/t60/2025-10-31_15-01-53",
        "sb/t60/2025-11-02_04-20-34",
        "sb/t60/2025-11-03_05-59-37",
    ]
    sb_c50 = [
        "sb/c50/2025-11-06_17-21-24",
        "sb/c50/2025-11-07_01-00-43",
        "sb/c50/2025-11-07_10-08-17",
    ]
    sb_edt = [
        "sb/edt/2025-11-03_06-22-44",
        "sb/edt/2025-11-07_01-10-34",
        "sb/edt/2025-11-07_10-16-45",
    ]
    sb_mag = [
        "sb/mag/2025-10-31_15-36-53",
        "sb/mag/2025-11-02_04-45-53",
        "sb/mag/2025-11-03_06-30-44",
    ]
    nb_t60 = [
        "nb/t60/2025-10-31_15-50-25",
        "nb/t60/2025-11-02_04-55-44",
        "nb/t60/2025-11-03_06-42-48",
    ]
    nb_c50 = [
        "nb/c50/2025-11-06_17-45-46",
        "nb/c50/2025-11-06_18-01-27",
        "nb/c50/2025-11-07_01-22-29",
    ]
    nb_edt = [
        "nb/edt/2025-11-07_00-34-33",
        "nb/edt/2025-11-07_01-30-39",
        # "nb/edt/2025-11-03_06-54-21",
    ]
    nb_mag = [
        "nb/mag/2025-10-31_16-22-39",
        "nb/mag/2025-11-02_05-29-24",
        "nb/mag/2025-11-03_07-14-56",
    ]
    params = [
        r"$\mathrm{T}_{60}$",
        r"$\mathrm{C}_{50}$",
        r"$\mathrm{EDT}$",
        r"$\mathrm{P}_{rel}$",
    ]

    prop_t60_metrics = read_metrics(prop_t60)
    prop_c50_metrics = read_metrics(prop_c50)
    prop_edt_metrics = read_metrics(prop_edt)
    prop_mag_metrics = read_metrics(prop_mag)

    prop_ft_t60_metrics = read_metrics(prop_ft_t60)
    prop_ft_c50_metrics = read_metrics(prop_ft_c50)
    prop_ft_edt_metrics = read_metrics(prop_ft_edt)
    prop_ft_mag_metrics = read_metrics(prop_ft_mag)

    ctr_t60_metrics = read_metrics(ctr_param_t60)
    ctr_c50_metrics = read_metrics(ctr_param_c50)
    ctr_edt_metrics = read_metrics(ctr_param_edt)
    ctr_mag_metrics = read_metrics(ctr_param_mag)

    ctr_ft_t60_metrics = read_metrics(ctr_param_ft_t60)
    ctr_ft_c50_metrics = read_metrics(ctr_param_ft_c50)
    ctr_ft_edt_metrics = read_metrics(ctr_param_ft_edt)
    ctr_ft_mag_metrics = read_metrics(ctr_param_ft_mag)

    e2e_t60_metrics = read_metrics(e2e_t60)
    e2e_c50_metrics = read_metrics(e2e_c50)
    e2e_edt_metrics = read_metrics(e2e_edt)
    e2e_mag_metrics = read_metrics(e2e_mag)

    semiblind_t60_metrics = read_metrics(sb_t60)
    semiblind_c50_metrics = read_metrics(sb_c50)
    semiblind_edt_metrics = read_metrics(sb_edt)
    semiblind_mag_metrics = read_metrics(sb_mag)

    nonblind_t60_metrics = read_metrics(nb_t60)
    nonblind_c50_metrics = read_metrics(nb_c50)
    nonblind_edt_metrics = read_metrics(nb_edt)
    nonblind_mag_metrics = read_metrics(nb_mag)

    all_results = [
        [
            prop_t60_metrics,
            prop_ft_t60_metrics,
            ctr_t60_metrics,
            ctr_ft_t60_metrics,
            e2e_t60_metrics,
            nonblind_t60_metrics,
            semiblind_t60_metrics,
        ],
        [
            prop_edt_metrics,
            prop_ft_edt_metrics,
            ctr_edt_metrics,
            ctr_ft_edt_metrics,
            e2e_edt_metrics,
            nonblind_edt_metrics,
            semiblind_edt_metrics,
        ],
        [
            prop_mag_metrics,
            prop_ft_mag_metrics,
            ctr_mag_metrics,
            ctr_ft_mag_metrics,
            e2e_mag_metrics,
            nonblind_mag_metrics,
            semiblind_mag_metrics,
        ],
        [
            prop_c50_metrics,
            prop_ft_c50_metrics,
            ctr_c50_metrics,
            ctr_ft_c50_metrics,
            e2e_c50_metrics,
            nonblind_c50_metrics,
            semiblind_c50_metrics,
        ],
    ]

    f_labels = ["125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz"]

    prel_labels = ["125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz"]

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

    keys = [
        ["mape", "bias", "pcc"],
        ["mape", "bias", "pcc"],
        ["mae", "bias", "pcc"],
        ["mae", "bias", "pcc"],
    ]

    metrics = [
        [r"$\mathrm{MAPE}\,[\%]$", "BIAS [s]", r"PCC"],
        [r"$\mathrm{MAPE}\,[\%]$", "BIAS [s]", r"PCC"],
        ["MAE [dB]", "BIAS [dB]", r"PCC"],
        ["MAE [dB]", "BIAS [dB]", r"PCC"],
    ]

    cmap = plt.get_cmap("tab10")

    x = np.arange(len(f_labels))

    params = [
        r"$\mathrm{T}_{60}$",
        r"$\mathrm{EDT}$",
        r"$\mathrm{P}_{\mathrm{rel}}$",
        r"$\mathrm{C}_{50}$",
    ]

    variants = [
        "PR",
        "PR-FT",
        "CTR",
        "CTR-FT",
        "E2E",
        "NB",
        "SB",
    ]

    color_inds = [0, 0, 1, 1, 2, 3, 4]
    lss = ["-", "-", "-", "-", "-", "--", "--"]
    markers = ["D", "d", "x", "X", "o", "<", ">"]
    handles = []

    fig = plt.figure(figsize=(7, 5.5))
    # Define the overall gridspec with two main rows
    gs = gridspec.GridSpec(4, 3, hspace=0.1, wspace=0.3)

    text_locs = [[0.5, 0.85], [0.5, 0.1], [0.5, 0.1]]

    # For magnitude plots (P_rel has no 1kHz, so only 6 bands)
    x_mag = np.array([0, 1, 2, 4, 5, 6])
    x_mag_lo = np.array([0, 1, 2])
    x_mag_hi = np.array([4, 5, 6])

    for p, (param, result) in enumerate(zip(params, all_results)):
        for i, (metric, key) in enumerate(zip(metrics[p], keys[p])):
            ax = fig.add_subplot(gs[p, i])

            # Add metric label box
            ax.text(
                *text_locs[i],
                s=metric,
                fontsize=8,
                transform=ax.transAxes,
                ha="center",
                bbox=dict(
                    facecolor="white",
                    edgecolor="lightgrey",
                    boxstyle="round,pad=0.2",
                ),
            )

            # Add reference line at y=0 for bias plots
            if "bias" in key.lower():
                ax.plot([0, len(f_labels) - 1], [0, 0], color="k", ls="--", lw=1)

            # Plot each variant
            for cind, ls, marker, variant, res in zip(
                color_inds, lss, markers, variants, result
            ):
                mean = res[key][0]

                # Handle magnitude plots with split x-axis (only 6 bands, no 1kHz)
                if p == 2:  # P_rel parameter
                    ax.plot(
                        x_mag_lo, mean[:3], color=cmap(cind), ls=ls, marker=marker, lw=1
                    )
                    line = ax.plot(
                        x_mag_hi, mean[3:], color=cmap(cind), ls=ls, marker=marker, lw=1
                    )
                else:
                    line = ax.plot(
                        x, mean, color=cmap(cind), ls=ls, marker=marker, lw=1
                    )

                # Collect handles for legend (only from one column)
                if i == 0 and p == 1:
                    handles.append(line[0])

            # Set x-axis
            ax.set_xticks(x)
            ax.grid()

            # Add x-axis labels only for bottom row
            if p == 3:
                ax.set_xticklabels(f_labels, rotation=30)
            else:
                ax.set_xticklabels(["" for _ in range(len(x))])

            # Add parameter labels on the left
            if i == 0:
                ax.text(
                    -0.3,
                    0.4,
                    param,
                    rotation=90,
                    fontsize=12,
                    transform=ax.transAxes,
                )

    # Add legend at the top
    fig.legend(
        handles=handles,
        labels=variants,
        loc="upper center",
        ncol=7,
        bbox_to_anchor=(0.5, 1.0),
        fontsize=8,
        handletextpad=0.3,
        labelspacing=0.1,
        frameon=True,
    )

    plt.subplots_adjust(left=0.08, right=0.99, top=0.93, bottom=0.05)
    plt.savefig("plots/results.png", dpi=300, bbox_inches="tight")
    plt.savefig("plots/results.pdf", dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
