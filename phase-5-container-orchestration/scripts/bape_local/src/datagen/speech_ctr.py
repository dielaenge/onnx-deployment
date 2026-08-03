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
    num_speech: int,
    num_rir: int,
    hard_sampling: bool,
    speech_path: str,
    out_path: str,
    rir_path: str,
    speech_representation: Any,
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

        # split the DataFrame
        rir_subsets = [
            rir_data.iloc[:train_end],
            rir_data.iloc[train_end:valid_end],
            rir_data.iloc[valid_end:],
        ]

    speech_list = get_file_list(speech_path)
    random.shuffle(speech_list)
    speech_subsets = split_list(speech_list, ratios)

    samps_per_batch = int(num_speech * num_rir)
    num_batches = [num // samps_per_batch for num in num_samps]

    for speech_subset, rir_subset, num_batch, prefix in zip(
        speech_subsets, rir_subsets, num_batches, prefixes
    ):
        # retrieves anechoic source and noise segments
        speech_stream = AudioStream(file_list=speech_subset, sr=fs, duration=duration)

        # init shardwriter
        if write_flag:
            sink = ShardWriter(f"{out_path}/{prefix}-%04d.tar", maxsize=1e9)
            sink.verbose = False

        for batch_count in trange(num_batch):

            rir_idxs = np.mod(
                np.arange(num_rir) + num_rir * batch_count, len(rir_subset)
            )
            rirs = [rir_subset.iloc[idx]["rir"] for idx in rir_idxs]

            # prepare rirs
            for i in range(len(rirs)):
                rirs[i] = remove_pre_delay(rirs[i], guard=1)
                rirs[i] = rirs[i] / np.max(np.abs(rirs[i]))
                rirs[i] = fix_length(rirs[i], 2 * fs)

            batch = []
            norm = []
            for _ in range(num_speech):
                speech = speech_stream.next_segment()[0]
                for rir in rirs:
                    snr = random.uniform(snr_range[0], snr_range[1])
                    if not hard_sampling:
                        speech = speech_stream.next_segment()[0]
                    wet = reverberate(speech, rir, int(duration * fs))
                    wet = add_awgn_with_vad(signal=wet, snr_db=snr)
                    wetspec = speech_representation(wet)
                    norm.append(
                        {
                            "wetspec_mean": wetspec.mean(),
                            "wetspec_std": wetspec.std(),
                        }
                    )
                    wetspec -= wetspec.mean()
                    wetspec /= wetspec.std()
                    batch.append(wetspec)

            signal = torch.stack(batch)

            out_dict = {
                "__key__": f"sample{batch_count:08d}",
                "signal.pyd": signal.unsqueeze(1),
                "label.pyd": torch.LongTensor(rir_idxs).tile(num_speech),
                "norm.pyd": norm,
                "snr.pyd": snr,
            }

            if write_flag:
                sink.write(out_dict)

        # close subset sink
        if write_flag:
            sink.close()
