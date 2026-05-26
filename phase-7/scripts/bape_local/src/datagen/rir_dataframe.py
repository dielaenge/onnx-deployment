from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from soundfile import read
from librosa import resample

from src.util.files import get_file_list
from src.util.rir_params import RIRParameters
from src.util.signals import remove_pre_delay


def main():

    fs = 16000
    rir_params = RIRParameters(fs=fs)
    rir_dir = Path("data/rirs/meas/")
    subfolders = [folder.name for folder in rir_dir.iterdir() if folder.is_dir()]
    rir_files = get_file_list(path=rir_dir, suffix=[".wav"])
    rir_files.sort()

    rows = []
    for file in tqdm(rir_files):
        rir, fs_file = read(file, always_2d=True)
        if fs_file != fs:
            rir = np.array(
                [resample(ch, orig_sr=fs_file, target_sr=fs) for ch in rir.T]
            ).T

        if "MRTD" in file:
            # add a teeny bit of noise
            rir += np.random.randn(*rir.shape) * 1e-6

        for i, ch in enumerate(rir.T):
            # remove pre-delay
            ch = remove_pre_delay(ch, guard=1, thresh=0.1)

            # normalize peak
            ch /= np.abs(ch).max()

            row = rir_params.analyze(ch)
            row["file"] = file
            row["channel"] = i
            row["rir"] = ch
            row["fs_file"] = fs_file
            row["fs"] = fs

            # store name of the dataset
            if len(subfolders) > 0:
                row["dataset"] = subfolders[
                    [folder in file for folder in subfolders].index(True)
                ]
            else:
                row["dataset"] = rir_dir.name

            rows.append(pd.Series(row))

    df = pd.DataFrame(rows)
    df.to_pickle("data/rirs_dataframe_16k.pkl")


if __name__ == "__main__":

    # generate dataframe
    main()

    # curate dataset, plot and save
    import seaborn as sns
    import matplotlib.gridspec as gridspec
    from matplotlib.colors import ListedColormap
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    # Enable LaTeX fonts
    plt.rcParams["text.usetex"] = True
    plt.rcParams["font.family"] = "serif"

    pth = "data/rirs_dataframe_16k.pkl"
    # pth = "data/rirs/meas/mrtd_dataframe.pkl"
    data = pd.read_pickle(pth)

    # remove all channels > 0
    data = data[data["channel"] < 1].reset_index(drop=True)

    # remove rows that have t60=0 in any subband
    data = data[(data["t60"].apply(lambda x: (x > 0).all()))].reset_index(drop=True)
    data = data[(data["edt"].apply(lambda x: (x > 0).all()))].reset_index(drop=True)

    # clip all t60 adn edt values to min 0.01
    data["t60"] = data["t60"].apply(lambda x: np.clip(x, a_min=0.01, a_max=None))
    data["edt"] = data["edt"].apply(lambda x: np.clip(x, a_min=0.01, a_max=None))

    # remove all rirs that have c50 < x dB in any subband
    data = data[(data["c50"].apply(lambda x: (x >= -9).all()))].reset_index(drop=True)

    # remove all rirs that have t60 > 2.5s in any subband
    data = data[(data["t60"].apply(lambda x: (x <= 2.5).all()))].reset_index(drop=True)

    # filter datasets with fs_file <= 16000
    # data = data[data["fs_file"] > 16000].reset_index(drop=True)

    # # Define the maximum number of samples per subset
    max_samples_per_subset = 1024
    filtered_data = data.groupby("dataset", group_keys=False).apply(
        lambda x: x.sample(n=min(len(x), max_samples_per_subset), random_state=42)
    )
    data = filtered_data.reset_index(drop=True)

    print(len(data))

    out_path = "data/rirs_dataframe_curated_16k.pkl"
    data.to_pickle(out_path)

    # prepare params
    t60 = np.stack([row["t60"] for _, row in data.iterrows()])
    c50 = np.stack([row["c50"] for _, row in data.iterrows()])
    mag_oct = np.stack([row["mag_oct"] for _, row in data.iterrows()])
    edt = np.stack([row["edt"] for _, row in data.iterrows()])

    palette = sns.color_palette("Set1", 7)

    mag_oct_labels = ["125 Hz", "250 Hz", "500 Hz", "2 kHz", "4 kHz", "8 kHz"]
    subband_labels = ["125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz"]
    all_tix = [0, 1, 2, 3, 4, 5, 6]
    mag_oct_tix = [0, 1, 2, 4, 5, 6]

    datasets = data["dataset"].value_counts().index.tolist()

    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
        "#ffbb78",
    ]

    cmap = ListedColormap(colors)
    # Create a figure
    fig = plt.figure(figsize=(4.5, 5))

    # Define the outer gridspec with 2 rows
    outer_gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], figure=fig, hspace=0.25)

    # Top group: scatter plot and histograms
    top_gs = gridspec.GridSpecFromSubplotSpec(
        2,
        2,
        subplot_spec=outer_gs[0],
        width_ratios=[6, 1],
        height_ratios=[1, 4],
        hspace=0.05,
        wspace=0.05,
    )

    # The histogram for t60 (top)
    ax_hist_t60 = fig.add_subplot(top_gs[0, 0])
    ax_hist_t60.hist(t60.mean(axis=-1), bins=30, color="skyblue", edgecolor="gray")
    ax_hist_t60.xaxis.set_visible(False)
    ax_hist_t60.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax_hist_t60.set_yticks([])

    # The scatter plot (middle left)
    ax_scatter = fig.add_subplot(top_gs[1, 0])
    for c, folder in enumerate(datasets):
        subset = data[data.dataset == folder]
        t60_ss, c50_ss = [], []
        for idx, row in subset.iterrows():
            t60_ss.append(row["t60"])
            c50_ss.append(row["c50"])
        t60_ss = np.stack(t60_ss).mean(axis=-1)
        c50_ss = np.stack(c50_ss).mean(axis=-1)
        ax_scatter.scatter(
            t60_ss,
            c50_ss,
            s=8,
            alpha=0.3,
            label=f"{folder}: {len(subset)}",
            color=cmap(c),
        )
    ax_scatter.grid()
    ax_scatter.legend(
        ncol=2, loc="upper right", columnspacing=0.7, handletextpad=0.4, fontsize=8
    )
    ax_scatter.set_xlabel(r"$\overline{\mathrm{T}}_{60}$ [s]", labelpad=1)
    # ax_scatter.set_ylabel(r"$\overline{\mathrm{C}}_{50}$ [dB]", labelpad=1)
    ax_scatter.text(
        x=-0.2,
        y=0.5,
        s=r"$\overline{\mathrm{C}}_{50}$ [dB]",
        rotation=90,
        ha="center",
        va="center",
        transform=ax_scatter.transAxes,
    )

    # The histogram for c50 (side)
    ax_hist_c50 = fig.add_subplot(top_gs[1, 1], sharey=ax_scatter)
    ax_hist_c50.hist(
        c50.mean(axis=-1),
        bins=20,
        orientation="horizontal",
        color="skyblue",
        edgecolor="gray",
    )
    ax_hist_c50.yaxis.set_visible(False)
    ax_hist_c50.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax_hist_c50.set_xticks([])
    ax_hist_c50.set_yticks([0, 20, 40, 60])

    # Bottom group: violin plots
    bottom_gs = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer_gs[1], hspace=0.1
    )

    # Define consistent y-label position
    ylabel_x_pos = -0.143

    # t60
    ax2 = fig.add_subplot(bottom_gs[0])
    sns.violinplot(data=t60, ax=ax2, linewidth=1, palette=palette)
    ax2.set_ylim(0, 2)
    ax2.grid(axis="y")
    ax2.text(
        x=ylabel_x_pos,
        y=0.5,
        s=r"T$_{60}$ [s]",
        rotation=90,
        ha="center",
        va="center",
        transform=ax2.transAxes,
    )
    ax2.set_xticks([])

    # C50
    ax3 = fig.add_subplot(bottom_gs[1])
    sns.violinplot(data=c50, ax=ax3, linewidth=1, palette=palette)
    ax3.set_ylim(-12, 36)
    ax3.grid(axis="y")
    ax3.text(
        x=ylabel_x_pos,
        y=0.5,
        s="C$_{50}$ [dB]",
        rotation=90,
        ha="center",
        va="center",
        transform=ax3.transAxes,
    )
    ax3.set_yticks([-12, 0, 12, 24, 36])
    ax3.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax3.set_xticklabels(subband_labels, rotation=25, fontsize=8)

    plt.subplots_adjust(left=0.12, bottom=0.07, right=0.98, top=0.99)
    plt.savefig(
        "plots/dummy.png",
        dpi=300,
        bbox_inches="tight",
    )
