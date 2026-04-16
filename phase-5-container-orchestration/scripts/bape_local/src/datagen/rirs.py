import os
import random
from typing import Any
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from tqdm import tqdm
from webdataset import ShardWriter

from soundfile import read
from librosa import resample

# import matplotlib.pyplot as plt

from src.util.signals import remove_pre_delay, fix_length
from src.util.files import get_file_list, split_list
from src.util.utils import seed_everything


def generate(
    fs: int,
    duration: float,
    ratios: list,
    out_path: str,
    rir_path: str,
    rir_representation: Any,
    write_flag: bool = True,
    seed: int = 42,
) -> None:
    """rir_dataset generation for distance fingerprinting"""

    seed_everything(seed)

    # subset names
    prefixes = ["train", "valid", "test"]

    rir_path = Path(rir_path)

    if rir_path.is_dir():
        # create subsets of RIRs
        rir_list = get_file_list(rir_path)
        random.shuffle(rir_list)
        # handle training with only one RIR, overfitting experiment
        if len(rir_list) == 1:
            rir_subsets = [rir_list] * len(prefixes)
        else:
            rir_subsets = split_list(rir_list, ratios)
    else:
        rir_data = pd.read_pickle(rir_path)
        rir_data = rir_data.sample(frac=1, random_state=seed).reset_index(drop=True)
        # Calculate split indices
        train_end = int(len(rir_data) * ratios[0])
        valid_end = train_end + int(len(rir_data) * ratios[1])

        # Split the DataFrame
        rir_subsets = [
            rir_data.iloc[:train_end],
            rir_data.iloc[train_end:valid_end],
            rir_data.iloc[valid_end:],
        ]

    for rir_subset, prefix in zip(rir_subsets, prefixes):

        # init shardwriter
        if write_flag:
            sink = ShardWriter(f"{out_path}/{prefix}-%04d.tar", maxsize=1e9)
            sink.verbose = False

        for sample_count in tqdm(range(len(rir_subset))):
            # get rir
            rir_index = sample_count % len(rir_subset)
            if rir_path.is_dir():

                rir, fs_rir = read(rir_subset[rir_index], always_2d=True)
                if rir.shape[-1] > 1:
                    rir = rir[:, 0]
                if fs_rir != fs:
                    rir = resample(y=rir, orig_sr=fs_rir, target_sr=fs)
            else:
                rir = rir_subset.iloc[rir_index]["rir"]

            rir = remove_pre_delay(rir, guard=8, thresh=0.05)

            # fix rir length
            rir = fix_length(rir, fs * duration)

            # flip sign if necessary, normalize
            if np.max(rir) < 0:
                rir = -rir
            rir /= np.max(rir)

            # plt.style.use("dark_background")
            # _, ax = plt.subplots(1, 1, figsize=(9, 3))
            # ax.plot(rir)
            # plt.tight_layout()
            # plt.savefig("dummy.png")
            # plt.close()

            # time-frequency representation
            spec = rir_representation(rir)

            # store normalization
            norm = {
                "rirspec_mean": spec.mean(),
                "rirspec_std": spec.std(),
            }

            spec_n = F.layer_norm(spec, normalized_shape=spec.shape)

            # plt.style.use("dark_background")
            # fg, axs = plt.subplots(2, 1, figsize=(9, 3))
            # ax = axs[0]
            # ph = ax.pcolor(spec.numpy())
            # plt.colorbar(ph, ax=ax)
            # ax = axs[1]
            # ph = ax.pcolor(spec_n.numpy())
            # plt.colorbar(ph, ax=ax)
            # plt.tight_layout()
            # plt.savefig("dummy.png")
            # plt.close()

            tto = lambda x: torch.tensor(x, dtype=torch.float32)

            param = {
                "t60": tto(rir_subset.iloc[rir_index]["t60"]),
                "edt": tto(rir_subset.iloc[rir_index]["edt"]),
                "drr": tto(rir_subset.iloc[rir_index]["drr"]),
                "c50": tto(rir_subset.iloc[rir_index]["c50"]),
                "mag_oct": tto(rir_subset.iloc[rir_index]["mag_oct"]),
                "mag_third_oct": tto(rir_subset.iloc[rir_index]["mag_third_oct"]),
                # "edt": rir_subset.iloc[rir_index]["edt"],
                # "drr": rir_subset.iloc[rir_index]["drr"],
                # "c50": rir_subset.iloc[rir_index]["c50"],
                # "mag_oct": rir_subset.iloc[rir_index]["mag_oct"],
            }

            out_dict = {
                "__key__": f"sample{sample_count:08d}",
                "rir.pyd": torch.tensor(rir, dtype=torch.float32)[None, ...],
                "spec.pyd": spec_n[None, ...],
                "norm.pyd": norm,
                "param.pyd": param,
            }

            if write_flag:
                sink.write(out_dict)

        # close subset sink
        if write_flag:
            sink.close()
