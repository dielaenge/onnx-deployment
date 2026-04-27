import os
import random
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from tqdm import trange
from webdataset import ShardWriter
from soundfile import read
from librosa import resample
from omegaconf import ListConfig

# import matplotlib.pyplot as plt

from src.util.signals import (
    AudioStream,
    reverberate,
    remove_pre_delay,
    fix_length,
    add_awgn_with_vad,
)
from src.util.files import get_file_list, split_list
from src.util.utils import seed_everything


def generate(
    fs: int,
    duration: float,
    num_samps: ListConfig[int],
    snr_range: ListConfig[int] | None,
    speech_path: str,
    out_path: str,
    rir_path: str,
    speech_representation: Any,
    rir_representation: Any,
    write_flag: bool = True,
    seed: int = 42,
) -> None:
    """rir_dataset generation for distance fingerprinting"""

    seed_everything(seed)

    # subset names
    prefixes = ["train", "valid", "test"]

    # create subsets of RIRs and speech
    ratios = [num / sum(num_samps) for num in num_samps]

    rir_path = Path(rir_path)

    if rir_path.is_dir():
        # create subsets of RIRs
        rir_list = get_file_list(rir_path)
        random.shuffle(rir_list)
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

    speech_list = get_file_list(speech_path)
    random.shuffle(speech_list)
    speech_subsets = split_list(speech_list, ratios)

    for speech_subset, rir_subset, num, prefix in zip(
        speech_subsets, rir_subsets, num_samps, prefixes
    ):
        # retrieves anechoic source and noise segments
        speech_stream = AudioStream(file_list=speech_subset, sr=fs, duration=duration)

        # init shardwriter
        if write_flag:
            sink = ShardWriter(f"{out_path}/{prefix}-%04d.tar", maxsize=1e9)
            sink.verbose = False

        for sample_count in trange(num):

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

            rir = remove_pre_delay(rir, guard=1)
            rir /= np.max(np.abs(rir))

            # fix rir length
            rir = fix_length(rir, 2 * fs)

            # get next anechoic speech and noise segments
            dry, _ = speech_stream.next_segment()

            # reverberant input signal
            wet = reverberate(dry, rir, int(duration * fs))

            if snr_range is not None:
                # add noise to wet signal
                snr = random.uniform(snr_range[0], snr_range[1])
                wet = add_awgn_with_vad(signal=wet, snr_db=snr)
            else:
                snr = None

            # spectrograms
            wetspec = speech_representation(wet)
            dryspec = speech_representation(dry)
            rirspec = rir_representation(rir)

            # plt.subplot(2, 1, 1)
            # plt.pcolor(wetspec.numpy())
            # plt.subplot(2, 1, 2)
            # plt.pcolor(dryspec.numpy())
            # plt.savefig("dummy.png")
            # plt.close()

            # store normalization
            norm = {
                "wetspec_mean": wetspec.mean(),
                "wetspec_std": wetspec.std(),
                "dryspec_mean": dryspec.mean(),
                "dryspec_std": dryspec.std(),
                "rirspec_mean": rirspec.mean(),
                "rirspec_std": rirspec.std(),
            }

            wetspec = F.layer_norm(wetspec, normalized_shape=wetspec.shape)
            dryspec = F.layer_norm(dryspec, normalized_shape=dryspec.shape)
            rirspec = F.layer_norm(rirspec, normalized_shape=rirspec.shape)

            param = {
                "t60": torch.tensor(
                    rir_subset.iloc[rir_index]["t60"], dtype=torch.float32
                ),
                "c50": torch.tensor(
                    rir_subset.iloc[rir_index]["c50"], dtype=torch.float32
                ),
                "edt": torch.tensor(
                    rir_subset.iloc[rir_index]["edt"], dtype=torch.float32
                ),
                "mag_oct": torch.tensor(
                    rir_subset.iloc[rir_index]["mag_oct"], dtype=torch.float32
                ),
                "mag_third_oct": torch.tensor(
                    rir_subset.iloc[rir_index]["mag_third_oct"], dtype=torch.float32
                ),
            }

            out_dict = {
                "__key__": f"sample{sample_count:08d}",
                # "dry.pyd": torch.tensor(dry, dtype=torch.float32)[None, ...],
                # "wet.pyd": torch.tensor(wet, dtype=torch.float32)[None, ...],
                # "rir.pyd": torch.tensor(rir, dtype=torch.float32)[None, ...],
                # "dryspec.pyd": dryspec[None, ...],
                "wetspec.pyd": wetspec[None, ...],
                "rirspec.pyd": rirspec[None, ...],
                "norm.pyd": norm,
                "snr.pyd": snr,
                "param.pyd": param,
            }

            if write_flag:
                sink.write(out_dict)

        # close subset sink
        if write_flag:
            sink.close()
